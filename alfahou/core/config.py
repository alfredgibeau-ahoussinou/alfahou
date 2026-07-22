from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "AlfAhou"
    host: str = "127.0.0.1"
    port: int = 8787
    root: Path = ROOT
    weights_dir: Path = ROOT / "weights"
    outputs_dir: Path = ROOT / "outputs"
    data_dir: Path = ROOT / "data"
    corpus_path: Path = ROOT / "data" / "corpus" / "seed_bilingual.txt"

    text_block_size: int = 64
    text_n_embd: int = 192
    text_n_head: int = 6
    text_n_layer: int = 4
    text_dropout: float = 0.1

    image_size: int = 64
    image_channels: int = 3
    diffusion_steps: int = 200
    image_infer_steps: int = 12
    unet_base: int = 64
    text_cond_dim: int = 192

    video_frames: int = 72
    video_fps: int = 24
    pdf_with_image: bool = False

    # LLM multi-route (Groq + OpenRouter + HF…)
    llm_enabled: bool = True
    llm_provider: str = "auto"  # auto | groq | compound | openrouter | hf | ollama
    llm_api_key: str = ""
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_model: str = "openai/gpt-oss-20b"
    llm_max_tokens: int = 2048
    llm_timeout: float = 120.0

    model_config = {
        "env_prefix": "ALFAHOU_",
        "env_file": str(ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
settings.weights_dir.mkdir(parents=True, exist_ok=True)
settings.outputs_dir.mkdir(parents=True, exist_ok=True)
(settings.data_dir / "corpus").mkdir(parents=True, exist_ok=True)
(settings.data_dir / "raw").mkdir(parents=True, exist_ok=True)
