"""Moteur vidéo — OpenRouter (Veo/Wan…) ou image cloud + motion Ken Burns."""

from __future__ import annotations

from pathlib import Path

from alfahou.models.image.engine import ImageEngine
from alfahou.models.media import cloud as media_cloud
from alfahou.models.text.engine import TextEngine


class VideoEngine:
    def __init__(self, image_engine: ImageEngine | None = None, text_engine: TextEngine | None = None):
        self.text_engine = text_engine or TextEngine()
        self.image_engine = image_engine or ImageEngine(self.text_engine)
        self.last_provider: str | None = None

    def available(self) -> bool:
        return True

    def generate(self, prompt: str, frames: int | None = None, fps: int | None = None) -> Path:
        path, provider = media_cloud.generate_video(prompt)
        self.last_provider = provider
        return path
