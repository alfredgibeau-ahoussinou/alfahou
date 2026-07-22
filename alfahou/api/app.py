from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.orchestrator.agent import AlfAhou, Modality

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="AlfAhou", description="IA multimédia d'Alfred Ahoussinou — from scratch")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
brain = AlfAhou()


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    modality: Modality = Modality.AUTO
    max_tokens: int = Field(220, ge=16, le=800)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "name": "AlfAhou",
        "author": "Alfred Ahoussinou",
        "device": str(DEVICE),
        "models": brain.status(),
    }


@app.post("/api/generate")
def generate(req: GenerateRequest):
    try:
        result = brain.generate(req.prompt, modality=req.modality, max_tokens=req.max_tokens)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur AlfAhou: {e}") from e

    file_url = None
    if result.file_path:
        name = Path(result.file_path).name
        file_url = f"/outputs/{name}"
    return {
        "modality": result.modality.value,
        "text": result.text,
        "file_url": file_url,
        "message": result.message,
    }


app.mount("/outputs", StaticFiles(directory=str(settings.outputs_dir)), name="outputs")
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
