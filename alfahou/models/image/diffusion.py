from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        half = self.dim // 2
        freqs = torch.exp(-math.log(10000) * torch.arange(half, device=t.device) / half)
        args = t.float().unsqueeze(1) * freqs.unsqueeze(0)
        return torch.cat([args.sin(), args.cos()], dim=-1)


class ResBlock(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, time_dim: int, cond_dim: int):
        super().__init__()
        self.norm1 = nn.GroupNorm(8, in_ch)
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, padding=1)
        self.norm2 = nn.GroupNorm(8, out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1)
        self.time_proj = nn.Linear(time_dim, out_ch)
        self.cond_proj = nn.Linear(cond_dim, out_ch)
        self.skip = nn.Conv2d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        h = self.conv1(F.silu(self.norm1(x)))
        h = h + self.time_proj(F.silu(t_emb))[:, :, None, None]
        h = h + self.cond_proj(cond)[:, :, None, None]
        h = self.conv2(F.silu(self.norm2(h)))
        return h + self.skip(x)


class ConditionalUNet(nn.Module):
    """UNet conditionné par embedding texte — générateur d'images AlfAhou."""

    def __init__(self, in_ch: int = 3, base: int = 64, cond_dim: int = 192, time_dim: int = 256):
        super().__init__()
        self.time_mlp = nn.Sequential(
            SinusoidalPosEmb(time_dim),
            nn.Linear(time_dim, time_dim),
            nn.SiLU(),
            nn.Linear(time_dim, time_dim),
        )
        self.in_conv = nn.Conv2d(in_ch, base, 3, padding=1)
        self.down1 = ResBlock(base, base, time_dim, cond_dim)
        self.down2 = ResBlock(base, base * 2, time_dim, cond_dim)
        self.pool = nn.AvgPool2d(2)
        self.mid = ResBlock(base * 2, base * 2, time_dim, cond_dim)
        self.up1 = ResBlock(base * 4, base, time_dim, cond_dim)
        self.up2 = ResBlock(base * 2, base, time_dim, cond_dim)
        self.out = nn.Sequential(nn.GroupNorm(8, base), nn.SiLU(), nn.Conv2d(base, in_ch, 3, padding=1))

    def forward(self, x: torch.Tensor, t: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        t_emb = self.time_mlp(t)
        x0 = self.in_conv(x)
        d1 = self.down1(x0, t_emb, cond)
        d2 = self.down2(self.pool(d1), t_emb, cond)
        m = self.mid(self.pool(d2), t_emb, cond)
        u1 = F.interpolate(m, scale_factor=2, mode="nearest")
        u1 = self.up1(torch.cat([u1, d2], dim=1), t_emb, cond)
        u2 = F.interpolate(u1, scale_factor=2, mode="nearest")
        u2 = self.up2(torch.cat([u2, d1], dim=1), t_emb, cond)
        return self.out(u2)


class GaussianDiffusion(nn.Module):
    def __init__(self, model: ConditionalUNet, timesteps: int = 200):
        super().__init__()
        self.model = model
        self.timesteps = timesteps
        betas = torch.linspace(1e-4, 0.02, timesteps)
        alphas = 1.0 - betas
        alpha_bar = torch.cumprod(alphas, dim=0)
        self.register_buffer("betas", betas)
        self.register_buffer("alphas", alphas)
        self.register_buffer("alpha_bar", alpha_bar)
        self.register_buffer("sqrt_alpha_bar", torch.sqrt(alpha_bar))
        self.register_buffer("sqrt_one_minus_alpha_bar", torch.sqrt(1.0 - alpha_bar))

    def q_sample(self, x0: torch.Tensor, t: torch.Tensor, noise: torch.Tensor | None = None):
        if noise is None:
            noise = torch.randn_like(x0)
        sa = self.sqrt_alpha_bar[t].view(-1, 1, 1, 1)
        so = self.sqrt_one_minus_alpha_bar[t].view(-1, 1, 1, 1)
        return sa * x0 + so * noise, noise

    def p_losses(self, x0: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        b = x0.size(0)
        t = torch.randint(0, self.timesteps, (b,), device=x0.device)
        x_noisy, noise = self.q_sample(x0, t)
        pred = self.model(x_noisy, t, cond)
        return F.mse_loss(pred, noise)

    @torch.no_grad()
    def sample(self, cond: torch.Tensor, shape: tuple[int, ...], steps: int | None = None) -> torch.Tensor:
        steps = steps or self.timesteps
        device = cond.device
        x = torch.randn(shape, device=device)
        # sous-échantillonner les timesteps pour génération rapide
        order = torch.linspace(self.timesteps - 1, 0, steps, device=device).long()
        for i, t_val in enumerate(order):
            t = torch.full((shape[0],), int(t_val.item()), device=device, dtype=torch.long)
            pred_noise = self.model(x, t, cond)
            beta = self.betas[t].view(-1, 1, 1, 1)
            alpha = self.alphas[t].view(-1, 1, 1, 1)
            alpha_bar = self.alpha_bar[t].view(-1, 1, 1, 1)
            x = (1 / torch.sqrt(alpha)) * (x - beta / torch.sqrt(1 - alpha_bar) * pred_noise)
            if i < len(order) - 1:
                x = x + torch.sqrt(beta) * torch.randn_like(x)
        return x.clamp(-1, 1)
