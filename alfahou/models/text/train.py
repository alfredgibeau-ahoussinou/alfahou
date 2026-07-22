from __future__ import annotations

from pathlib import Path

import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.text.engine import save_checkpoint
from alfahou.models.text.tokenizer import WordTokenizer
from alfahou.models.text.transformer import MiniGPT


class TokenDataset(Dataset):
    def __init__(self, data: torch.Tensor, block_size: int):
        self.data = data
        self.block_size = block_size

    def __len__(self) -> int:
        return max(0, len(self.data) - self.block_size)

    def __getitem__(self, i: int):
        chunk = self.data[i : i + self.block_size + 1]
        return chunk[:-1], chunk[1:]


def train_text(
    corpus_path: Path | None = None,
    steps: int = 1200,
    batch_size: int = 32,
    lr: float = 3e-4,
) -> MiniGPT:
    corpus_path = corpus_path or settings.corpus_path
    text = corpus_path.read_text(encoding="utf-8")
    # Répéter le corpus pour plus d'expositions aux dialogues bilingues
    text = (text + "\n") * 8
    tokenizer = WordTokenizer().build_from_text(text, min_freq=1)
    ids = torch.tensor(tokenizer.encode(text, add_special=False), dtype=torch.long)
    ds = TokenDataset(ids, settings.text_block_size)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=True)

    model = MiniGPT(
        vocab_size=tokenizer.vocab_size,
        block_size=settings.text_block_size,
        n_embd=settings.text_n_embd,
        n_head=settings.text_n_head,
        n_layer=settings.text_n_layer,
        dropout=settings.text_dropout,
    ).to(DEVICE)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    model.train()
    it = iter(loader)
    pbar = tqdm(range(steps), desc="AlfAhou texte bilingue")
    for step in pbar:
        try:
            x, y = next(it)
        except StopIteration:
            it = iter(loader)
            x, y = next(it)
        x, y = x.to(DEVICE), y.to(DEVICE)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 50 == 0:
            pbar.set_postfix(loss=float(loss.item()), vocab=tokenizer.vocab_size)

    model.eval()
    save_checkpoint(model, tokenizer)
    return model
