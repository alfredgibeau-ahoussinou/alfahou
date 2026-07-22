from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from alfahou.agent.memory import STORE, Session, extract_name
from alfahou.agent.skills import run_text_skill
from alfahou.core.config import settings
from alfahou.models.image.engine import ImageEngine
from alfahou.models.pdf.engine import PDFEngine
from alfahou.models.text.bilingual import detect_lang
from alfahou.models.text.engine import TextEngine
from alfahou.models.video.engine import VideoEngine
from alfahou.orchestrator.agent import Modality


@dataclass
class ChatResult:
    session_id: str
    text: str
    modality: str = "text"
    file_url: str | None = None
    skill: str = "general"
    suggestions: list[str] | None = None
    language: str = "fr"


class AlfAhouBrain:
    """Agent conversationnel multimodal — mémoire, skills, médias."""

    def __init__(self) -> None:
        self.text = TextEngine()
        self.image = ImageEngine(self.text)
        self.video = VideoEngine(self.image, self.text)
        self.pdf = PDFEngine()

    def status(self) -> dict:
        return {
            "name": "AlfAhou",
            "author": "Alfred Ahoussinou",
            "capabilities": [
                "chat",
                "memory",
                "translate",
                "summarize",
                "rewrite",
                "explain",
                "brainstorm",
                "plan",
                "code",
                "math",
                "email",
                "story",
                "study",
                "social",
                "image",
                "video",
                "pdf",
                "voice_ready",
            ],
            "text": True,
            "image": self.image.available(),
            "video": self.video.available(),
            "pdf": True,
            "languages": ["fr", "en"],
            "modes": ["balanced", "creative", "precise", "teacher"],
        }

    def _detect_modality(self, prompt: str, modality: Modality) -> Modality:
        if modality != Modality.AUTO:
            return modality
        p = prompt.lower()
        if re.search(r"\b(vidéo|video|film|animation|clip)\b", p) or re.search(
            r"(génère|genere|generate|crée|cree|create|fais|make).{0,20}\b(vidéo|video)\b", p
        ):
            return Modality.VIDEO
        if re.search(r"\bpdf\b", p) or re.search(
            r"(génère|genere|generate|crée|cree|export).{0,20}\b(pdf|document)\b", p
        ):
            return Modality.PDF
        if re.search(r"\b(image|illustration|dessin|peinture|visuel)\b", p) or re.search(
            r"(génère|genere|generate|crée|cree|create|dessine|draw|fais).{0,24}\b(image|photo|picture)\b", p
        ) or re.search(r"\b(photo)\b(?!synth)", p):
            return Modality.IMAGE
        return Modality.TEXT

    def _suggestions(self, lang: str, skill: str) -> list[str]:
        if lang == "en":
            base = {
                "general": ["Make a plan", "Explain simply", "Brainstorm ideas"],
                "explain": ["Give an analogy", "Quiz me", "Go deeper"],
                "plan": ["Turn into checklist", "Write an email", "Summarize"],
                "image": ["Make a video from this", "Describe it", "Another variation"],
            }
        else:
            base = {
                "general": ["Fais un plan", "Explique simplement", "Brainstorm"],
                "explain": ["Donne une analogie", "Interroge-moi", "Approfondis"],
                "plan": ["Transforme en checklist", "Écris un mail", "Résume"],
                "image": ["Fais une vidéo", "Décris l’image", "Autre variation"],
            }
        return base.get(skill, base["general"])

    def _conversational_basics(self, prompt: str, lang: str, session: Session) -> str | None:
        t = prompt.lower().strip()
        name = extract_name(prompt)
        if name:
            session.memory["name"] = name
            if lang == "en":
                return f"Nice to meet you, {name}. I’m AlfAhou — what should we create together?"
            return f"Enchanté, {name}. Je suis AlfAhou — on crée quoi ensemble ?"

        if re.fullmatch(r"(bonjour|salut|bonsoir|hey|hi|hello|good\s*(morning|evening|afternoon))[!?.]*", t):
            who = session.memory.get("name")
            if lang == "en":
                return (
                    f"Hello{(' ' + who) if who else ''}! I’m AlfAhou, your multimedia AI "
                    f"(text, image, video, PDF — FR/EN). What’s on your mind?"
                )
            return (
                f"Bonjour{(' ' + who) if who else ''} ! Je suis AlfAhou, ton IA multimédia "
                f"(texte, image, vidéo, PDF — FR/EN). Qu’est-ce qu’on fait ?"
            )
        if re.search(r"\b(merci|thanks|thank you)\b", t):
            return "Avec plaisir 🙌" if lang == "fr" else "You’re welcome 🙌"
        if re.search(r"\b(qui es[- ]tu|who are you|présente[- ]toi|about you|about alfahou)\b", t):
            if lang == "en":
                return (
                    "I’m **AlfAhou** — Alfred + Ahoussinou.\n\n"
                    "I chat with memory, write/translate/summarize/plan/code, do math, "
                    "and generate images, videos, and PDFs. No third-party cloud LLM API."
                )
            return (
                "Je suis **AlfAhou** — Alfred + Ahoussinou.\n\n"
                "Je discute avec mémoire, j’écris/traduis/résume/planifie/code, je calcule, "
                "et je génère images, vidéos et PDF. Pas d’API LLM cloud tierce."
            )
        if re.search(r"\b(aide|help|que sais[- ]tu faire|what can you do|capacités|capabilities)\b", t):
            if lang == "en":
                return (
                    "I can:\n"
                    "• Chat (multi-turn, FR/EN)\n"
                    "• Write, translate, summarize, rewrite, explain\n"
                    "• Brainstorm, plan, SWOT, checklists\n"
                    "• Emails, posts, stories, poems, study sheets\n"
                    "• Code sketches & math\n"
                    "• Images, videos, PDFs\n\n"
                    "Try: “Explain quantum simply” or “Image: red circle”."
                )
            return (
                "Je peux :\n"
                "• Discuter (multi-tours, FR/EN)\n"
                "• Écrire, traduire, résumer, réécrire, expliquer\n"
                "• Brainstorm, plan, SWOT, checklists\n"
                "• Mails, posts, histoires, poèmes, fiches\n"
                "• Code & maths\n"
                "• Images, vidéos, PDF\n\n"
                "Essaie : « Explique la photosynthèse » ou « Image : cercle rouge »."
            )
        return None

    def chat(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        modality: Modality = Modality.AUTO,
        mode: str = "balanced",
        language: str | None = None,
    ) -> ChatResult:
        lang = language or detect_lang(prompt)
        session = STORE.get_or_create(session_id, mode=mode, language=lang)
        session.language = lang
        session.mode = mode if mode in {"balanced", "creative", "precise", "teacher"} else "balanced"
        session.add("user", prompt)

        kind = self._detect_modality(prompt, modality)
        suggestions: list[str]

        if kind == Modality.IMAGE:
            path = self.image.generate(prompt)
            text = "Voici l’image." if lang == "fr" else "Here’s the image."
            file_url = f"/outputs/{Path(path).name}"
            session.add("assistant", text, modality="image", file_url=file_url)
            suggestions = self._suggestions(lang, "image")
            return ChatResult(session.id, text, "image", file_url, "image", suggestions, lang)

        if kind == Modality.VIDEO:
            path = self.video.generate(prompt)
            text = "Voici la vidéo." if lang == "fr" else "Here’s the video."
            file_url = f"/outputs/{Path(path).name}"
            session.add("assistant", text, modality="video", file_url=file_url)
            suggestions = self._suggestions(lang, "image")
            return ChatResult(session.id, text, "video", file_url, "video", suggestions, lang)

        if kind == Modality.PDF:
            body = self.text.generate(prompt)
            title = prompt.strip().split("\n")[0][:80] or "Document AlfAhou"
            path = self.pdf.generate(title=title, body=body, image_path=None)
            text = body
            file_url = f"/outputs/{Path(path).name}"
            session.add("assistant", text, modality="pdf", file_url=file_url)
            suggestions = self._suggestions(lang, "plan")
            return ChatResult(session.id, text, "pdf", file_url, "pdf", suggestions, lang)

        basic = self._conversational_basics(prompt, lang, session)
        if basic:
            session.add("assistant", basic)
            return ChatResult(session.id, basic, "text", None, "chat", self._suggestions(lang, "general"), lang)

        # Contexte mémoire légère injectée
        ctx_bits = []
        if session.memory.get("name"):
            ctx_bits.append(session.memory["name"])
        text, skill = run_text_skill(prompt, lang, session.mode, session.memory)
        # Si l'utilisateur dit "approfondis" / "go deeper", s'appuyer sur le dernier sujet
        if re.search(r"\b(approfondis|go deeper|continue|plus de détails|more detail)\b", prompt.lower()):
            prev = session.last_user_topic()
            if prev and prev.lower() != prompt.lower():
                text, skill = run_text_skill(f"explique {prev}", lang, session.mode, session.memory)

        session.add("assistant", text)
        return ChatResult(session.id, text, "text", None, skill, self._suggestions(lang, skill), lang)
