from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.image.diffusion import ConditionalUNet, GaussianDiffusion
from alfahou.models.text.engine import TextEngine

IMAGE_WEIGHTS = settings.weights_dir / "image_diffusion.pt"


class ImageEngine:
    def __init__(self, text_engine: TextEngine | None = None) -> None:
        self.text_engine = text_engine or TextEngine()
        self.diffusion: GaussianDiffusion | None = None
        self._load()

    def available(self) -> bool:
        return self.diffusion is not None

    def _load(self) -> None:
        if not IMAGE_WEIGHTS.exists():
            return
        ckpt = torch.load(IMAGE_WEIGHTS, map_location="cpu", weights_only=False)
        cfg = ckpt["config"]
        unet = ConditionalUNet(
            in_ch=cfg["channels"],
            base=cfg["base"],
            cond_dim=cfg["cond_dim"],
        )
        diffusion = GaussianDiffusion(unet, timesteps=cfg["timesteps"])
        diffusion.load_state_dict(ckpt["model"])
        diffusion.to(DEVICE)
        diffusion.eval()
        self.diffusion = diffusion

    def generate(self, prompt: str, steps: int | None = None) -> Path:
        if not self.available():
            raise RuntimeError("Modèle image non entraîné. Lance scripts/bootstrap.py")
        assert self.diffusion is not None
        steps = steps if steps is not None else settings.image_infer_steps
        cond = self.text_engine.embed(prompt).unsqueeze(0).to(DEVICE)
        cond = cond / (cond.norm(dim=-1, keepdim=True) + 1e-6)
        size = settings.image_size
        with torch.inference_mode():
            sample = self.diffusion.sample(
                cond,
                shape=(1, settings.image_channels, size, size),
                steps=steps,
            )
        img = ((sample[0].cpu().permute(1, 2, 0).numpy() + 1) * 127.5).clip(0, 255).astype(np.uint8)
        out = settings.outputs_dir / f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        Image.fromarray(img).save(out)
        return out


def save_image_checkpoint(diffusion: GaussianDiffusion, path: Path = IMAGE_WEIGHTS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": diffusion.state_dict(),
            "config": {
                "channels": settings.image_channels,
                "base": settings.unet_base,
                "cond_dim": settings.text_cond_dim,
                "timesteps": settings.diffusion_steps,
                "image_size": settings.image_size,
            },
        },
        path,
    )
