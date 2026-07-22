from __future__ import annotations

import hashlib
from pathlib import Path

import torch

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.text.tokenizer import CharTokenizer
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
        self.tokenizer: CharTokenizer | None = None
        self.model: MiniGPT | None = None
        self._load()

    def available(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def _load(self) -> None:
        if not TEXT_WEIGHTS.exists() or not TOKENIZER_PATH.exists():
            return
        self.tokenizer = CharTokenizer.load(TOKENIZER_PATH)
        ckpt = torch.load(TEXT_WEIGHTS, map_location="cpu", weights_only=False)
        cfg = ckpt["config"]
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

    def generate(self, prompt: str, max_tokens: int = 200, temperature: float = 0.9) -> str:
        if not self.available():
            raise RuntimeError("Modèle texte non entraîné. Lance scripts/bootstrap.py")
        assert self.model is not None and self.tokenizer is not None
        ids = self.tokenizer.encode(prompt, add_special=True)[:-1]  # keep BOS, drop EOS
        idx = torch.tensor([ids], dtype=torch.long, device=DEVICE)
        out = self.model.generate(idx, max_new_tokens=max_tokens, temperature=temperature)
        return self.tokenizer.decode(out[0].tolist())

    def embed(self, text: str) -> torch.Tensor:
        if not self.available():
            return _stable_embed(text, settings.text_cond_dim)
        assert self.model is not None and self.tokenizer is not None
        ids = self.tokenizer.encode(text, add_special=True)
        ids = ids[: self.model.block_size]
        idx = torch.tensor([ids], dtype=torch.long, device=DEVICE)
        emb = self.model.embed_text(idx).squeeze(0).detach().cpu()
        return emb / (emb.norm() + 1e-6)


def save_checkpoint(model: MiniGPT, tokenizer: CharTokenizer, path: Path = TEXT_WEIGHTS) -> None:
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
            },
        },
        path,
    )
    tokenizer.save(TOKENIZER_PATH)
