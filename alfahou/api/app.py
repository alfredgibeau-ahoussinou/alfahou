from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from alfahou.agent.brain import AlfAhouBrain
from alfahou.agent.memory import STORE
from alfahou.core.config import settings
from alfahou.core.device import DEVICE
from alfahou.orchestrator.agent import AlfAhou, Modality

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="AlfAhou",
    description="IA multimédia complète d'Alfred Ahoussinou — chat, skills, image, vidéo, PDF",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

brain: AlfAhou | None = None
chat_brain: AlfAhouBrain | None = None


def get_brain() -> AlfAhou:
    global brain
    if brain is None:
        brain = AlfAhou()
    return brain


def get_chat() -> AlfAhouBrain:
    global chat_brain
    if chat_brain is None:
        chat_brain = AlfAhouBrain()
    return chat_brain


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    modality: Modality = Modality.AUTO
    max_tokens: int = Field(220, ge=16, le=800)


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = None
    modality: Modality = Modality.AUTO
    mode: str = Field("balanced", pattern="^(balanced|creative|precise|teacher)$")
    language: str | None = Field(None, pattern="^(fr|en)$")


class ResetRequest(BaseModel):
    session_id: str


class CreateSessionRequest(BaseModel):
    title: str | None = None
    mode: str = Field("balanced", pattern="^(balanced|creative|precise|teacher)$")
    language: str = Field("fr", pattern="^(fr|en)$")


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)


class UpsertSessionRequest(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    title: str | None = None
    mode: str | None = None
    language: str | None = None


class ListSessionsRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


@app.get("/api/health")
def health():
    c = get_chat()
    return {
        "ok": True,
        "name": "AlfAhou",
        "author": "Alfred Ahoussinou",
        "device": str(DEVICE),
        "models": c.status(),
        "languages": ["fr", "en"],
    }


@app.get("/api/capabilities")
def capabilities():
    return get_chat().status()


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        result = get_chat().chat(
            req.prompt,
            session_id=req.session_id,
            modality=req.modality,
            mode=req.mode,
            language=req.language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur AlfAhou: {e}") from e

    session = STORE.get(result.session_id)
    return {
        "session_id": result.session_id,
        "modality": result.modality,
        "text": result.text,
        "file_url": result.file_url,
        "skill": result.skill,
        "suggestions": result.suggestions or [],
        "language": result.language,
        "title": session.title if session else None,
        "message": "ok",
    }


@app.post("/api/chat/reset")
def chat_reset(req: ResetRequest):
    s = STORE.reset(req.session_id)
    return {"session_id": s.id, "ok": True, "title": s.title}


@app.post("/api/chat/sessions")
def create_session(req: CreateSessionRequest):
    s = STORE.create(title=req.title, mode=req.mode, language=req.language)
    return s.to_dict()


@app.post("/api/chat/sessions/list")
def list_sessions(req: ListSessionsRequest):
    """Liste les conversations dont les ids appartiennent au client."""
    items = STORE.list_sessions(ids=req.ids)
    return {"sessions": items}


@app.get("/api/chat/sessions/{session_id}")
def get_session(session_id: str):
    s = STORE.get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return s.to_dict()


@app.put("/api/chat/sessions/{session_id}")
def upsert_session(session_id: str, req: UpsertSessionRequest):
    s = STORE.upsert_messages(
        session_id,
        req.messages,
        title=req.title,
        mode=req.mode,
        language=req.language,
    )
    return s.to_dict()


@app.patch("/api/chat/sessions/{session_id}")
def rename_session(session_id: str, req: RenameSessionRequest):
    s = STORE.rename(session_id, req.title)
    if not s:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"id": s.id, "title": s.title, "ok": True}


@app.delete("/api/chat/sessions/{session_id}")
def delete_session(session_id: str):
    ok = STORE.delete(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"ok": True, "id": session_id}


@app.post("/api/generate")
def generate(req: GenerateRequest):
    """Compat : route vers le chat (session jetable)."""
    try:
        result = get_chat().chat(req.prompt, modality=req.modality)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur AlfAhou: {e}") from e
    return {
        "modality": result.modality,
        "text": result.text,
        "file_url": result.file_url,
        "message": result.message if hasattr(result, "message") else "ok",
        "session_id": result.session_id,
        "suggestions": result.suggestions or [],
    }


app.mount("/outputs", StaticFiles(directory=str(settings.outputs_dir)), name="outputs")
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="ui")
