from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from alfahou.agent.converse import try_chitchat
from alfahou.agent.memory import STORE, Session, extract_name
from alfahou.agent.skills import run_text_skill
from alfahou.models.image.engine import ImageEngine
from alfahou.models.pdf.engine import PDFEngine
from alfahou.models.media import cloud as media_cloud
from alfahou.models.media.cloud import clean_media_prompt
from alfahou.models.text.bilingual import detect_lang
from alfahou.models.text.engine import TextEngine
from alfahou.models.text.llm_engine import get_llm
from alfahou.models.video.engine import VideoEngine
from alfahou.orchestrator.agent import Modality


def _persist(session: Session) -> None:
    STORE.save(session)


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
    """Agent conversationnel multimodal — LLM cloud + skills + médias cloud."""

    def __init__(self) -> None:
        self.text = TextEngine()
        self.image = ImageEngine(self.text)
        self.video = VideoEngine(self.image, self.text)
        self.pdf = PDFEngine()
        self.llm = get_llm()

    def status(self) -> dict:
        llm = self.llm.status()
        media = media_cloud.media_status()
        return {
            "name": "AlfAhou",
            "author": "Alfred Ahoussinou",
            "capabilities": [
                "chat",
                "llm_cloud",
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
            "llm": llm,
            "image": True,
            "video": True,
            "pdf": True,
            "media": media,
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
                "llm": ["Go deeper", "Make it shorter", "Give an example"],
            }
        else:
            base = {
                "general": ["Fais un plan", "Explique simplement", "Brainstorm"],
                "explain": ["Donne une analogie", "Interroge-moi", "Approfondis"],
                "plan": ["Transforme en checklist", "Écris un mail", "Résume"],
                "image": ["Fais une vidéo", "Décris l’image", "Autre variation"],
                "llm": ["Approfondis", "Plus court", "Donne un exemple"],
            }
        return base.get(skill, base["general"])

    def _exact_local_skill(self, prompt: str) -> bool:
        """Math / heure : rester local pour l’exactitude."""
        t = prompt.lower()
        return bool(
            re.search(r"\b(calcule|calculate|combien fait|sqrt)\b", t)
            or re.search(r"\d+\s*[\+\-\*/]\s*\d+", t)
            or re.search(r"\b(quelle heure|what time|date d'?aujourd|today'?s date)\b", t)
        )

    def _history_dicts(self, session: Session) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for m in session.messages:
            if m.role in {"user", "assistant"} and m.content.strip():
                out.append({"role": m.role, "content": m.content})
        return out

    def _llm_reply(self, prompt: str, lang: str, session: Session) -> str | None:
        if not self.llm.available():
            return None
        try:
            return self.llm.chat(
                user_message=prompt,
                history=self._history_dicts(session),
                lang=lang,
                mode=session.mode,
                memory=session.memory,
            )
        except Exception:
            # Conservé dans llm.last_error pour /api/health
            return None

    def _conversational_basics(self, prompt: str, lang: str, session: Session) -> str | None:
        """Fallback léger si pas de LLM — identité + chitchat."""
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
                    "I chat with a modern cloud LLM (GPT-OSS + live web search), and I can also make images, videos, and PDFs."
                )
            return (
                "Je suis **AlfAhou** — Alfred + Ahoussinou.\n\n"
                "Je discute via un LLM cloud récent (GPT-OSS + recherche web), et je peux aussi faire images, vidéos et PDF."
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

        name = extract_name(prompt)
        if name:
            session.memory["name"] = name

        session.add("user", prompt)

        kind = self._detect_modality(prompt, modality)

        if kind == Modality.IMAGE:
            try:
                path = self.image.generate(prompt)
            except Exception as e:
                msg = f"Impossible de générer l’image pour le moment : {e}" if lang == "fr" else f"Couldn’t generate the image: {e}"
                session.add("assistant", msg)
                _persist(session)
                return ChatResult(session.id, msg, "text", None, "image_error", self._suggestions(lang, "image"), lang)
            provider = getattr(self.image, "last_provider", None) or "cloud"
            text = (
                f"Voici l’image (via {provider})."
                if lang == "fr"
                else f"Here’s the image (via {provider})."
            )
            file_url = f"/outputs/{Path(path).name}"
            session.add("assistant", text, modality="image", file_url=file_url)
            _persist(session)
            return ChatResult(session.id, text, "image", file_url, "image", self._suggestions(lang, "image"), lang)

        if kind == Modality.VIDEO:
            try:
                path = self.video.generate(prompt)
            except Exception as e:
                msg = f"Impossible de générer la vidéo pour le moment : {e}" if lang == "fr" else f"Couldn’t generate the video: {e}"
                session.add("assistant", msg)
                _persist(session)
                return ChatResult(session.id, msg, "text", None, "video_error", self._suggestions(lang, "image"), lang)
            provider = getattr(self.video, "last_provider", None) or "cloud"
            if provider.endswith("+motion"):
                text = (
                    "Voici une animation fluide à partir d’une image 16:9 "
                    f"(via {provider}). Pour une vraie vidéo générative, les crédits "
                    "OpenRouter vidéo sont nécessaires."
                    if lang == "fr"
                    else f"Here’s a smooth 16:9 image animation (via {provider}). "
                    "True generative video needs OpenRouter video credits."
                )
            else:
                text = (
                    f"Voici la vidéo (via {provider})."
                    if lang == "fr"
                    else f"Here’s the video (via {provider})."
                )
            file_url = f"/outputs/{Path(path).name}"
            session.add("assistant", text, modality="video", file_url=file_url)
            _persist(session)
            return ChatResult(session.id, text, "video", file_url, "video", self._suggestions(lang, "image"), lang)

        if kind == Modality.PDF:
            topic = clean_media_prompt(prompt)
            pdf_prompt = (
                f"Rédige un document clair et utile sur : {topic}\n"
                "Structure avec un titre court, des sous-titres ## et des puces si besoin. "
                "Ton professionnel, français, 250–450 mots."
                if lang == "fr"
                else f"Write a clear useful document about: {topic}\n"
                "Use a short title, ## headings and bullets if useful. Professional tone, 250–450 words."
            )
            body = self._llm_reply(pdf_prompt, lang, session) or self.text.generate(prompt)
            title = topic[:80] or ("Document AlfAhou" if lang == "fr" else "AlfAhou document")
            # Première ligne markdown # titre
            m = re.match(r"^#\s+(.+)$", body.strip(), re.M)
            if m:
                title = m.group(1).strip()[:80]
            cover = None
            try:
                cover = self.image.generate(f"elegant editorial cover illustration for: {title}, no text")
            except Exception:
                cover = None
            path = self.pdf.generate(title=title, body=body, image_path=cover)
            file_url = f"/outputs/{Path(path).name}"
            summary = (
                f"PDF prêt : « {title} ». Tu peux le télécharger ci-dessous."
                if lang == "fr"
                else f"PDF ready: “{title}”. Download it below."
            )
            session.add("assistant", summary, modality="pdf", file_url=file_url)
            _persist(session)
            return ChatResult(session.id, summary, "pdf", file_url, "pdf", self._suggestions(lang, "plan"), lang)

        # Maths / heure : moteur local exact
        if self._exact_local_skill(prompt):
            text, skill = run_text_skill(prompt, lang, session.mode, session.memory)
            session.add("assistant", text)
            _persist(session)
            return ChatResult(session.id, text, "text", None, skill, self._suggestions(lang, skill), lang)

        # Chemin principal : LLM cloud moderne (GPT-OSS + outils)
        llm_text = self._llm_reply(prompt, lang, session)
        if llm_text:
            session.add("assistant", llm_text)
            _persist(session)
            return ChatResult(session.id, llm_text, "text", None, "llm", self._suggestions(lang, "llm"), lang)

        # Si le LLM est configuré mais en erreur (quota, etc.), ne pas mentir via le fallback local
        if self.llm.available() and self.llm.last_error:
            err = (
                "Je suis un peu saturé côté cloud pour le moment — réessaie dans quelques secondes. "
                "Mes réponses à jour passent par la recherche web en direct."
                if lang == "fr"
                else "The cloud model is briefly saturated — try again in a few seconds. Live answers use web search."
            )
            session.add("assistant", err)
            _persist(session)
            return ChatResult(session.id, err, "text", None, "llm_busy", self._suggestions(lang, "general"), lang)

        # Fallback sans clé / hors ligne
        basic = self._conversational_basics(prompt, lang, session)
        if basic:
            session.add("assistant", basic)
            _persist(session)
            return ChatResult(session.id, basic, "text", None, "chat", self._suggestions(lang, "general"), lang)

        text, skill = run_text_skill(prompt, lang, session.mode, session.memory)
        if re.search(r"\b(approfondis|go deeper|continue|plus de détails|more detail)\b", prompt.lower()):
            prev = session.last_user_topic()
            if prev and prev.lower() != prompt.lower():
                text, skill = run_text_skill(f"explique {prev}", lang, session.mode, session.memory)
        session.add("assistant", text)
        _persist(session)
        return ChatResult(session.id, text, "text", None, skill, self._suggestions(lang, skill), lang)
