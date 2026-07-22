#!/usr/bin/env python3
"""Entraîne les mini-modèles AlfAhou (texte puis image) — 100% local."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.image.train import train_image
from alfahou.models.text.engine import TextEngine
from alfahou.models.text.train import train_text


def main() -> None:
    print(f"AlfAhou bootstrap · device={DEVICE}")
    print(f"Corpus: {settings.corpus_path}")
    print("— Phase 1: texte (MiniGPT) —")
    train_text(steps=800, batch_size=32)
    text_engine = TextEngine()
    print("— Phase 2: image (diffusion) —")
    train_image(steps=500, batch_size=8, text_engine=text_engine)
    print("OK — poids sauvegardés dans", settings.weights_dir)
    print("Lance: uvicorn alfahou.api.app:app --reload --port 8787")


if __name__ == "__main__":
    main()
