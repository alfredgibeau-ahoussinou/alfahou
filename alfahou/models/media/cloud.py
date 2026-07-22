"""Génération média cloud — images / vidéos via OpenRouter + Pollinations (gratuit)."""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from alfahou.core.config import settings
from alfahou.models.text.llm_engine import _hydrate_env_from_dotenv

# Modèles image OpenRouter (du moins cher / rapide au plus premium)
OR_IMAGE_MODELS = (
    "black-forest-labs/flux.2-klein-4b",
    "sourceful/riverflow-v2.5-fast",
    "google/gemini-3.1-flash-lite-image",
    "google/gemini-3.1-flash-image",
    "openrouter/auto-beta",
)

OR_VIDEO_MODELS = (
    "google/veo-3.1-lite",
    "google/veo-3.1-fast",
    "alibaba/wan-2.6",
    "bytedance/seedance-2.0-fast",
)


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean_media_prompt(prompt: str) -> str:
    """Retire les verbes UI pour garder un prompt visuelle propre."""
    t = prompt.strip()
    t = re.sub(
        r"^(s['’]il te pla[iî]t[, ]+|please[, ]+)?(peux[- ]tu |can you )?",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"^(génère|genere|generate|crée|cree|create|fais|make|dessine|draw|montre|show|"
        r"produis|produce)\s+(moi\s+)?(une?\s+|un\s+|the\s+|a\s+|an\s+)?",
        "",
        t,
        flags=re.I,
    )
    t = re.sub(
        r"^(image|illustration|photo|picture|dessin|vidéo|video|clip|film|animation|pdf|document)\s+"
        r"(de\s+|d['’]|of\s+|about\s+|sur\s+)?",
        "",
        t,
        flags=re.I,
    )
    return t.strip(" .,:;") or prompt.strip()


def _or_headers() -> dict[str, str]:
    _hydrate_env_from_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://alfahou.netlify.app",
        "X-Title": "AlfAhou",
        "User-Agent": "AlfAhou/1.2",
    }


def _save_bytes(data: bytes, prefix: str, ext: str) -> Path:
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    path = settings.outputs_dir / f"{prefix}_{_now_stamp()}.{ext}"
    path.write_bytes(data)
    return path


def _http_json(url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: float = 120) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_bytes(url: str, headers: dict[str, str] | None = None, timeout: float = 120) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "AlfAhou/1.2"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), (resp.headers.get("content-type") or "")


def openrouter_available() -> bool:
    _hydrate_env_from_dotenv()
    return bool(os.environ.get("OPENROUTER_API_KEY", "").strip())


def generate_image_openrouter(prompt: str, *, model: str | None = None) -> Path | None:
    if not openrouter_available():
        return None
    models = [model] if model else list(OR_IMAGE_MODELS)
    last_err = None
    for mid in models:
        if not mid:
            continue
        try:
            result = _http_json(
                "https://openrouter.ai/api/v1/images",
                {
                    "model": mid,
                    "prompt": prompt,
                    "aspect_ratio": "1:1",
                },
                headers=_or_headers(),
                timeout=150,
            )
            data = result.get("data") or []
            if not data:
                continue
            item = data[0]
            if item.get("b64_json"):
                raw = base64.b64decode(item["b64_json"])
                return _save_bytes(raw, "img", "png")
            url = item.get("url") or (item.get("image_url") or {}).get("url")
            if url:
                raw, ctype = _http_bytes(url, timeout=90)
                ext = "jpg" if "jpeg" in ctype or "jpg" in ctype else "png"
                return _save_bytes(raw, "img", ext)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            last_err = f"{mid}: HTTP {e.code} {body}"
            if e.code in {401, 402, 403}:
                break  # crédits / auth → inutile de tout essayer
            continue
        except Exception as e:
            last_err = f"{mid}: {e}"
            continue
    if last_err:
        raise RuntimeError(last_err)
    return None


def generate_image_pollinations(prompt: str, *, width: int = 1024, height: int = 1024) -> Path:
    """Backend image gratuit et fiable (Pollinations)."""
    q = urllib.parse.quote(prompt[:400])
    url = (
        f"https://image.pollinations.ai/prompt/{q}"
        f"?width={width}&height={height}&nologo=true&enhance=true&model=flux"
    )
    raw, ctype = _http_bytes(url, headers={"User-Agent": "AlfAhou/1.2"}, timeout=120)
    if len(raw) < 1000:
        raise RuntimeError("Image Pollinations invalide")
    ext = "jpg" if "jpeg" in ctype or raw[:2] == b"\xff\xd8" else "png"
    return _save_bytes(raw, "img", ext)


def generate_image(prompt: str) -> tuple[Path, str]:
    """Retourne (path, provider)."""
    prompt = clean_media_prompt(prompt)
    # 1) OpenRouter si crédits
    if openrouter_available():
        try:
            path = generate_image_openrouter(prompt)
            if path:
                return path, "openrouter"
        except Exception:
            pass
    # 2) Pollinations gratuit
    path = generate_image_pollinations(prompt)
    return path, "pollinations"


def generate_video_openrouter(prompt: str, *, duration: int = 4) -> Path | None:
    if not openrouter_available():
        return None
    headers = _or_headers()
    last_err = None
    for mid in OR_VIDEO_MODELS:
        try:
            result = _http_json(
                "https://openrouter.ai/api/v1/videos",
                {
                    "model": mid,
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                },
                headers=headers,
                timeout=60,
            )
            job_id = result.get("id")
            polling = result.get("polling_url") or (f"https://openrouter.ai/api/v1/videos/{job_id}" if job_id else None)
            if not polling:
                continue
            # Poll max ~3 min
            for _ in range(24):
                time.sleep(8)
                req = urllib.request.Request(polling, headers=headers, method="GET")
                with urllib.request.urlopen(req, timeout=60) as resp:
                    status = json.loads(resp.read().decode("utf-8"))
                st = status.get("status")
                if st == "completed":
                    urls = status.get("unsigned_urls") or []
                    if not urls:
                        content = f"https://openrouter.ai/api/v1/videos/{job_id}/content?index=0"
                        raw, _ = _http_bytes(content, headers=headers, timeout=120)
                    else:
                        raw, _ = _http_bytes(urls[0], headers=headers, timeout=120)
                    return _save_bytes(raw, "vid", "mp4")
                if st == "failed":
                    last_err = status.get("error") or "failed"
                    break
            else:
                last_err = "timeout"
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            last_err = f"{mid}: HTTP {e.code} {body}"
            if e.code in {401, 402, 403}:
                break
            continue
        except Exception as e:
            last_err = f"{mid}: {e}"
            continue
    if last_err:
        raise RuntimeError(last_err)
    return None


def animate_still_to_video(image_path: Path, *, frames: int = 24, fps: int = 10) -> Path:
    """Ken Burns léger à partir d’une image cloud (fallback vidéo sans crédits)."""
    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    out_w, out_h = 768, 432
    big = img.resize((960, 540), Image.Resampling.LANCZOS)
    sw, sh = big.size
    max_x = max(0, sw - out_w)
    max_y = max(0, sh - out_h)
    seq = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        x = int(max_x * t)
        y = int(max_y * (0.2 + 0.6 * abs(0.5 - t) * 2))
        frame = big.crop((x, y, x + out_w, y + out_h))
        arr = np.array(frame)
        pulse = 0.97 + 0.03 * np.sin(2 * np.pi * t)
        arr = np.clip(arr.astype(np.float32) * pulse, 0, 255).astype(np.uint8)
        seq.append(arr)

    out = settings.outputs_dir / f"vid_{_now_stamp()}.mp4"
    imageio.mimsave(out, seq, fps=fps)
    return out


def generate_video(prompt: str) -> tuple[Path, str]:
    prompt = clean_media_prompt(prompt)
    if openrouter_available():
        try:
            path = generate_video_openrouter(prompt)
            if path:
                return path, "openrouter"
        except Exception:
            pass
    # Fallback : image cloud + animation
    still, img_provider = generate_image(prompt)
    path = animate_still_to_video(still)
    return path, f"{img_provider}+motion"


def media_status() -> dict[str, Any]:
    return {
        "image": {
            "cloud": True,
            "providers": ["openrouter", "pollinations"],
            "openrouter": openrouter_available(),
            "pollinations": True,
        },
        "video": {
            "cloud": True,
            "providers": ["openrouter", "pollinations+motion"],
            "openrouter": openrouter_available(),
        },
        "pdf": {"local": True, "cover_image": True},
    }
