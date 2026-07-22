from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from alfahou.models.image.engine import ImageEngine
from alfahou.models.pdf.engine import PDFEngine
from alfahou.models.text.engine import TextEngine
from alfahou.models.video.engine import VideoEngine


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    PDF = "pdf"
    AUTO = "auto"


@dataclass
class GenerationResult:
    modality: Modality
    text: str | None = None
    file_path: str | None = None
    message: str = "ok"


class AlfAhou:
    """Orchestrateur multimodal — route les intentions vers les moteurs locaux."""

    def __init__(self) -> None:
        self.text = TextEngine()
        self.image = ImageEngine(self.text)
        self.video = VideoEngine(self.image, self.text)
        self.pdf = PDFEngine()

    def status(self) -> dict:
        return {
            "name": "AlfAhou",
            "author": "Alfred Ahoussinou",
            "text": True,
            "text_model": self.text.model_ready(),
            "image": self.image.available(),
            "video": self.video.available(),
            "pdf": True,
            "languages": ["fr", "en"],
        }

    def _detect(self, prompt: str, modality: Modality) -> Modality:
        if modality != Modality.AUTO:
            return modality
        p = prompt.lower()
        if any(k in p for k in ("vidéo", "video", "film", "animation", "clip")):
            return Modality.VIDEO
        if any(k in p for k in ("pdf", "document", "rapport", "livre")):
            return Modality.PDF
        if any(k in p for k in ("image", "photo", "illustration", "dessin", "peinture", "visuel")):
            return Modality.IMAGE
        return Modality.TEXT

    def generate(self, prompt: str, modality: Modality = Modality.AUTO, max_tokens: int = 220) -> GenerationResult:
        kind = self._detect(prompt, modality)

        if kind == Modality.TEXT:
            text = self.text.generate(prompt, max_tokens=max_tokens)
            return GenerationResult(modality=kind, text=text)

        if kind == Modality.IMAGE:
            path = self.image.generate(prompt)
            return GenerationResult(modality=kind, file_path=str(path), text=prompt)

        if kind == Modality.VIDEO:
            path = self.video.generate(prompt)
            return GenerationResult(modality=kind, file_path=str(path), text=prompt)

        # PDF : texte (+ image optionnelle — désactivée en prod cloud pour éviter les timeouts)
        from alfahou.core.config import settings

        body = self.text.generate(prompt, max_tokens=max_tokens) if self.text.available() else prompt
        image_path: Path | None = None
        if settings.pdf_with_image and self.image.available():
            try:
                image_path = self.image.generate(prompt, steps=min(10, settings.image_infer_steps))
            except Exception:
                image_path = None
        title = prompt.strip().split("\n")[0][:80] or "Document AlfAhou"
        path = self.pdf.generate(title=title, body=body, image_path=image_path)
        return GenerationResult(modality=kind, file_path=str(path), text=body)
