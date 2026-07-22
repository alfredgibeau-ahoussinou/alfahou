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
    "google/veo-3.1-fast",
    "google/veo-3.1-lite",
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


def cinematic_video_prompt(prompt: str) -> str:
    """Enrichit le sujet pour les modèles vidéo / le still 16:9."""
    subject = clean_media_prompt(prompt)
    return (
        f"{subject}. Cinematic 16:9 shot, natural coherent motion, stable subject, "
        "photorealistic lighting, smooth camera, no morphing, no glitches, no text overlay."
    )


def _even(n: int) -> int:
    return n if n % 2 == 0 else n + 1


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


def generate_image_openrouter(
    prompt: str,
    *,
    model: str | None = None,
    aspect_ratio: str = "1:1",
) -> Path | None:
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
                    "aspect_ratio": aspect_ratio,
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


def generate_image(prompt: str, *, aspect_ratio: str = "1:1") -> tuple[Path, str]:
    """Retourne (path, provider)."""
    prompt = clean_media_prompt(prompt)
    # 1) OpenRouter si crédits
    if openrouter_available():
        try:
            path = generate_image_openrouter(prompt, aspect_ratio=aspect_ratio)
            if path:
                return path, "openrouter"
        except Exception:
            pass
    # 2) Pollinations gratuit
    if aspect_ratio == "16:9":
        path = generate_image_pollinations(prompt, width=1280, height=720)
    elif aspect_ratio == "9:16":
        path = generate_image_pollinations(prompt, width=720, height=1280)
    else:
        path = generate_image_pollinations(prompt)
    return path, "pollinations"


def generate_video_openrouter(prompt: str, *, duration: int = 5) -> Path | None:
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


def _cover_crop_16x9(img):
    """Recadre sans étirer pour un ratio 16:9 (évite les visages déformés)."""
    sw, sh = img.size
    target = 16 / 9
    src = sw / sh if sh else target
    if abs(src - target) < 0.02:
        return img
    if src > target:
        new_w = max(1, int(sh * target))
        left = (sw - new_w) // 2
        return img.crop((left, 0, left + new_w, sh))
    new_h = max(1, int(sw / target))
    top = (sh - new_h) // 2
    return img.crop((0, top, sw, top + new_h))


def animate_still_to_video(
    image_path: Path,
    *,
    frames: int | None = None,
    fps: int | None = None,
) -> Path:
    """Ken Burns sobre : cover 16:9, zoom + pan monotones, sans pulse ni bounce."""
    import imageio.v2 as imageio
    import numpy as np
    from PIL import Image

    frames = frames if frames is not None else max(48, settings.video_frames)
    fps = fps if fps is not None else max(24, settings.video_fps)

    img = _cover_crop_16x9(Image.open(image_path).convert("RGB"))
    # Multiples de 16 pour libx264 (évite le resize forcé d’imageio)
    out_w, out_h = 1280, 720
    # Marge pour un léger zoom avant (pas d’étirement)
    scale = 1.12
    big_w = _even(max(out_w + 2, int(out_w * scale)))
    big_h = _even(max(out_h + 2, int(out_h * scale)))
    # Aligner aussi sur 16 px
    big_w = big_w - (big_w % 16)
    big_h = big_h - (big_h % 16)
    big = img.resize((big_w, big_h), Image.Resampling.LANCZOS)
    max_x = max(0, big_w - out_w)
    max_y = max(0, big_h - out_h)

    seq = []
    for i in range(frames):
        t = i / max(frames - 1, 1)
        # smoothstep : accélération / freinage naturels
        e = t * t * (3.0 - 2.0 * t)
        # Zoom progressif : fenêtre de crop qui se resserre vers le centre-droit
        zoom = 1.0 + 0.1 * e
        cw = min(big_w, int(out_w / zoom))
        ch = min(big_h, int(out_h / zoom))
        cw = max(out_w // 2, cw - (cw % 2))
        ch = max(out_h // 2, ch - (ch % 2))
        x = int((max_x * 0.15) + (max(0, big_w - cw) - max_x * 0.15) * e)
        y = int(max(0, big_h - ch) * (0.4 + 0.2 * e))
        x = max(0, min(x, big_w - cw))
        y = max(0, min(y, big_h - ch))
        frame = big.crop((x, y, x + cw, y + ch)).resize((out_w, out_h), Image.Resampling.LANCZOS)
        seq.append(np.array(frame))

    out = settings.outputs_dir / f"vid_{_now_stamp()}.mp4"
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    try:
        imageio.mimsave(
            out,
            seq,
            fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
            output_params=["-profile:v", "main", "-level", "4.0", "-movflags", "+faststart"],
        )
    except TypeError:
        imageio.mimsave(out, seq, fps=fps)
    return out


def generate_video(prompt: str) -> tuple[Path, str]:
    video_prompt = cinematic_video_prompt(prompt)
    if openrouter_available():
        try:
            path = generate_video_openrouter(video_prompt)
            if path:
                return path, "openrouter"
        except Exception:
            pass
    # Fallback : still 16:9 + Ken Burns sobre (pas d’étirement 1:1→16:9)
    still, img_provider = generate_image(video_prompt, aspect_ratio="16:9")
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
