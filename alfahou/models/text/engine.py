from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.text.bilingual import bilingual_reply, detect_lang
from alfahou.models.text.tokenizer import WordTokenizer
from alfahou.models.text.transformer import MiniGPT


def _stable_embed(text: str, dim: int) -> torch.Tensor:
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    g = torch.Generator(device="cpu")
    g.manual_seed(seed)
    v = torch.randn(dim, generator=g)
    return v / (v.norm() + 1e-6)


TEXT_WEIGHTS = settings.weights_dir / "text_minigpt.pt"
TOKENIZER_PATH = settings.weights_dir / "tokenizer.json"


class TextEngine:
    def __init__(self) -> None:
        self.tokenizer: WordTokenizer | None = None
        self.model: MiniGPT | None = None
        self._load()

    def available(self) -> bool:
        # Le moteur bilingue répond même sans poids (mais embeddings image préfèrent le modèle)
        return True

    def model_ready(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def _load(self) -> None:
        if not TEXT_WEIGHTS.exists() or not TOKENIZER_PATH.exists():
            return
        try:
            raw = TOKENIZER_PATH.read_text(encoding="utf-8")
            # Ancien tokenizer caractère → ignorer, on réentraîne
            if '"type": "word"' not in raw and "stoi" not in raw:
                return
            self.tokenizer = WordTokenizer.load(TOKENIZER_PATH)
            ckpt = torch.load(TEXT_WEIGHTS, map_location="cpu", weights_only=False)
            cfg = ckpt["config"]
            if cfg.get("tokenizer") != "word":
                self.tokenizer = None
                return
            self.model = MiniGPT(
                vocab_size=cfg["vocab_size"],
                block_size=cfg["block_size"],
                n_embd=cfg["n_embd"],
                n_head=cfg["n_head"],
                n_layer=cfg["n_layer"],
                dropout=cfg.get("dropout", 0.1),
            )
            self.model.load_state_dict(ckpt["model"])
            self.model.to(DEVICE)
            self.model.eval()
        except Exception:
            self.tokenizer = None
            self.model = None

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.7) -> str:
        # 1) Réponse bilingue cohérente (FR/EN) — priorité absolue
        reply = bilingual_reply(prompt)
        if reply:
            return reply

        # 2) Filet de sécurité : ne jamais renvoyer du charabia
        lang = detect_lang(prompt)
        if lang == "en":
            return (
                "I understood your message. Tell me clearly what you want: "
                "a short text, an image, a video, or a PDF — in English or French."
            )
        return (
            "J’ai bien reçu ton message. Dis-moi clairement ce que tu veux : "
            "un texte, une image, une vidéo ou un PDF — en français ou en anglais."
        )

    def embed(self, text: str) -> torch.Tensor:
        if not self.model_ready():
            return _stable_embed(text, settings.text_cond_dim)
        assert self.model is not None and self.tokenizer is not None
        ids = self.tokenizer.encode(text, add_special=True)
        ids = ids[: self.model.block_size]
        idx = torch.tensor([ids], dtype=torch.long, device=DEVICE)
        with torch.inference_mode():
            emb = self.model.embed_text(idx).squeeze(0).detach().cpu()
        return emb / (emb.norm() + 1e-6)


def save_checkpoint(model: MiniGPT, tokenizer: WordTokenizer, path: Path = TEXT_WEIGHTS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "config": {
                "vocab_size": tokenizer.vocab_size,
                "block_size": model.block_size,
                "n_embd": model.n_embd,
                "n_head": settings.text_n_head,
                "n_layer": settings.text_n_layer,
                "dropout": settings.text_dropout,
                "tokenizer": "word",
            },
        },
        path,
    )
    tokenizer.save(TOKENIZER_PATH)
