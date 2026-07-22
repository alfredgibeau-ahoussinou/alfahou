from __future__ import annotations

from datetime import datetime
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
import torch
from PIL import Image

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.models.image.engine import ImageEngine
from alfahou.models.text.engine import TextEngine


class VideoEngine:
    """Vidéo = diffusion image + champ de mouvement neuronal (from scratch)."""

    def __init__(self, image_engine: ImageEngine | None = None, text_engine: TextEngine | None = None):
        self.text_engine = text_engine or TextEngine()
        self.image_engine = image_engine or ImageEngine(self.text_engine)
        # petit MLP qui prédit un flux optique latent à partir de t + cond
        self.motion = torch.nn.Sequential(
            torch.nn.Linear(settings.text_cond_dim + 1, 128),
            torch.nn.SiLU(),
            torch.nn.Linear(128, 64),
            torch.nn.SiLU(),
            torch.nn.Linear(64, 2),
            torch.nn.Tanh(),
        ).to(DEVICE)
        # init légère déterministe
        with torch.no_grad():
            for p in self.motion.parameters():
                if p.dim() > 1:
                    torch.nn.init.xavier_uniform_(p, gain=0.3)

    def available(self) -> bool:
        return self.image_engine.available()

    def generate(self, prompt: str, frames: int | None = None, fps: int | None = None) -> Path:
        if not self.available():
            raise RuntimeError("Modèle image requis pour la vidéo. Lance scripts/bootstrap.py")
        frames = frames or settings.video_frames
        fps = fps or settings.video_fps

        # image de base
        base_path = self.image_engine.generate(prompt, steps=30)
        base = np.array(Image.open(base_path).convert("RGB")).astype(np.float32) / 255.0
        h, w, _ = base.shape
        cond = self.text_engine.embed(prompt).to(DEVICE)
        cond = cond / (cond.norm() + 1e-6)

        seq = []
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        for i in range(frames):
            t = torch.tensor([i / max(frames - 1, 1)], device=DEVICE)
            inp = torch.cat([cond, t], dim=0).unsqueeze(0)
            with torch.no_grad():
                flow = self.motion(inp).squeeze(0).cpu().numpy()  # dx, dy in [-1,1]
            amp = 8.0
            dx = flow[0] * amp * np.sin(2 * np.pi * (i / frames) + xx / w)
            dy = flow[1] * amp * np.cos(2 * np.pi * (i / frames) + yy / h)
            # warp simple
            map_x = np.clip(xx + dx, 0, w - 1).astype(np.float32)
            map_y = np.clip(yy + dy, 0, h - 1).astype(np.float32)
            # bilinear via PIL resize trick: sample with integer nearest for speed
            xi = map_x.astype(np.int32)
            yi = map_y.astype(np.int32)
            frame = base[yi, xi]
            # pulsation couleur
            pulse = 0.92 + 0.08 * np.sin(2 * np.pi * i / frames)
            frame = np.clip(frame * pulse, 0, 1)
            seq.append((frame * 255).astype(np.uint8))

        out = settings.outputs_dir / f"vid_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        imageio.mimsave(out, seq, fps=fps)
        return out
