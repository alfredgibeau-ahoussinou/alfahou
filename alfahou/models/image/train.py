from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.image.diffusion import ConditionalUNet, GaussianDiffusion
from alfahou.models.image.engine import save_image_checkpoint
from alfahou.models.text.engine import TextEngine, _stable_embed


def _synth_image(label: int, size: int) -> np.ndarray:
    """Dataset synthétique from scratch — formes colorées conditionnées."""
    img = np.zeros((size, size, 3), dtype=np.float32)
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = size // 2, size // 2
    palette = [
        (0.95, 0.25, 0.2),
        (0.15, 0.75, 0.55),
        (0.2, 0.45, 0.95),
        (0.95, 0.75, 0.15),
        (0.7, 0.25, 0.85),
        (0.1, 0.9, 0.85),
    ]
    color = palette[label % len(palette)]
    kind = label % 4
    if kind == 0:
        mask = (xx - cx) ** 2 + (yy - cy) ** 2 < (size * 0.28) ** 2
    elif kind == 1:
        mask = (np.abs(xx - cx) < size * 0.22) & (np.abs(yy - cy) < size * 0.22)
    elif kind == 2:
        mask = np.abs(yy - (size - 1 - xx * size / size)) < size * 0.08
        mask |= (xx - cx) ** 2 / (size * 0.35) ** 2 + (yy - cy) ** 2 / (size * 0.2) ** 2 < 1
    else:
        angle = np.arctan2(yy - cy, xx - cx)
        r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        mask = (np.cos(angle * 5) * size * 0.12 + size * 0.28) > r
    for c in range(3):
        img[..., c] = np.where(mask, color[c], 0.05 + 0.05 * (c / 3))
    # texture légère
    noise = np.random.randn(size, size, 3).astype(np.float32) * 0.03
    img = np.clip(img + noise, 0, 1)
    return img


class SynthDataset(Dataset):
    def __init__(
        self,
        n: int = 2048,
        size: int = 64,
        cond_dim: int = 192,
        text_engine: TextEngine | None = None,
    ):
        self.n = n
        self.size = size
        self.cond_dim = cond_dim
        self.text_engine = text_engine
        self.prompts = [
            "cercle rouge vif",
            "carré vert émeraude",
            "forme bleue abstraite",
            "étoile jaune dorée",
            "motif violet énergétique",
            "disque cyan lumineux",
            "sculpture géométrique",
            "aurore colorée",
        ]
        self._cache: dict[str, torch.Tensor] = {}
        if text_engine is not None:
            for p in self.prompts:
                emb = text_engine.embed(p)
                self._cache[p] = emb / (emb.norm() + 1e-6)

    def __len__(self) -> int:
        return self.n

    def __getitem__(self, i: int):
        label = i % len(self.prompts)
        prompt = self.prompts[label]
        img = _synth_image(label, self.size)
        x = torch.from_numpy(img).permute(2, 0, 1) * 2 - 1
        if prompt in self._cache:
            cond = self._cache[prompt]
        else:
            cond = _stable_embed(prompt, self.cond_dim)
        return x, cond


def train_image(
    steps: int = 600,
    batch_size: int = 16,
    lr: float = 2e-4,
    text_engine: TextEngine | None = None,
) -> GaussianDiffusion:
    ds = SynthDataset(
        n=2048,
        size=settings.image_size,
        cond_dim=settings.text_cond_dim,
        text_engine=text_engine,
    )
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=True)
    unet = ConditionalUNet(
        in_ch=settings.image_channels,
        base=settings.unet_base,
        cond_dim=settings.text_cond_dim,
    )
    diffusion = GaussianDiffusion(unet, timesteps=settings.diffusion_steps).to(DEVICE)
    opt = torch.optim.AdamW(diffusion.parameters(), lr=lr)

    diffusion.train()
    it = iter(loader)
    pbar = tqdm(range(steps), desc="AlfAhou image")
    for step in pbar:
        try:
            x, cond = next(it)
        except StopIteration:
            it = iter(loader)
            x, cond = next(it)
        x, cond = x.to(DEVICE), cond.to(DEVICE)
        loss = diffusion.p_losses(x, cond)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % 50 == 0:
            pbar.set_postfix(loss=float(loss.item()))

    diffusion.eval()
    save_image_checkpoint(diffusion)
    return diffusion
