from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from alfahou.agent.converse import try_chitchat
from alfahou.agent.memory import STORE, Session, extract_name
from alfahou.agent.skills import run_text_skill
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
                return f"Nice to meet you, {name}. What do you want to do?"
            return f"Enchanté, {name}. Qu’est-ce que tu veux faire ?"

        who = session.memory.get("name")
        chitchat = try_chitchat(prompt, lang, who)
        if chitchat:
            return chitchat

        if re.search(r"\b(qui es[- ]tu|who are you|présente[- ]toi|about you|about alfahou)\b", t):
            if lang == "en":
                return (
                    "I’m **AlfAhou** — Alfred + Ahoussinou.\n\n"
                    "I chat naturally, write and help with ideas, and I can also make images, videos, and PDFs. "
                    "Talk to me like a normal person — any words, any tone."
                )
            return (
                "Je suis **AlfAhou** — Alfred + Ahoussinou.\n\n"
                "Je discute naturellement, j’écris et j’aide sur tes idées, et je peux aussi faire images, vidéos et PDF. "
                "Parle-moi comme à quelqu’un — tous les mots, tous les tons."
            )
        if re.fullmatch(
            r"(aide|help|que sais[- ]tu faire|what can you do|capacités|capabilities)[!?.]*",
            t,
        ) or re.search(r"\b(que sais[- ]tu faire|what can you do|tes capacités|your capabilities)\b", t):
            if lang == "en":
                return (
                    "I can chat like this, write texts, explain things, plan, brainstorm, "
                    "sketch code, do math, and create images, videos, or PDFs.\n\n"
                    "Just say what you need in plain words."
                )
            return (
                "Je peux discuter comme ça, écrire des textes, expliquer, planifier, brainstormer, "
                "esquisser du code, calculer, et créer des images, vidéos ou PDF.\n\n"
                "Dis-moi juste ce dont tu as besoin, avec tes mots."
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
