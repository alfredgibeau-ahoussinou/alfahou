"""Mémoire conversationnelle persistante (JSON sur disque)."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from alfahou.core.config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Message:
    role: str  # user | assistant | system
    content: str
    modality: str = "text"
    file_url: str | None = None
    created_at: str = field(default_factory=_now)


@dataclass
class Session:
    id: str
    messages: list[Message] = field(default_factory=list)
    language: str = "fr"
    mode: str = "balanced"
    memory: dict = field(default_factory=dict)
    title: str = "Nouvelle conversation"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def add(self, role: str, content: str, modality: str = "text", file_url: str | None = None) -> Message:
        msg = Message(role=role, content=content, modality=modality, file_url=file_url)
        self.messages.append(msg)
        if len(self.messages) > 80:
            self.messages = self.messages[-80:]
        self.updated_at = _now()
        if role == "user" and (self.title == "Nouvelle conversation" or not self.title.strip()):
            self.title = _title_from(content)
        return msg

    def history_text(self, last_n: int = 8) -> str:
        chunks = []
        for m in self.messages[-last_n:]:
            who = "User" if m.role == "user" else "AlfAhou"
            chunks.append(f"{who}: {m.content}")
        return "\n".join(chunks)

    def last_user_topic(self) -> str | None:
        for m in reversed(self.messages):
            if m.role == "user" and len(m.content.strip()) > 2:
                return m.content.strip()[:120]
        return None

    def preview(self) -> str:
        for m in reversed(self.messages):
            if m.content.strip():
                return m.content.strip().replace("\n", " ")[:90]
        return "Conversation vide"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "language": self.language,
            "mode": self.mode,
            "memory": self.memory,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [asdict(m) for m in self.messages],
            "preview": self.preview(),
            "message_count": len(self.messages),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        msgs = [
            Message(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                modality=m.get("modality", "text"),
                file_url=m.get("file_url"),
                created_at=m.get("created_at") or _now(),
            )
            for m in data.get("messages") or []
        ]
        return cls(
            id=data["id"],
            messages=msgs,
            language=data.get("language") or "fr",
            mode=data.get("mode") or "balanced",
            memory=data.get("memory") or {},
            title=data.get("title") or "Nouvelle conversation",
            created_at=data.get("created_at") or _now(),
            updated_at=data.get("updated_at") or _now(),
        )


def _title_from(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip())
    if len(t) <= 48:
        return t or "Nouvelle conversation"
    return t[:45].rstrip() + "…"


class MemoryStore:
    def __init__(self, root: Path | None = None) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()
        self._dir = root or (settings.data_dir / "sessions")
        self._dir.mkdir(parents=True, exist_ok=True)
        self._load_all()

    def _path(self, session_id: str) -> Path:
        safe = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)[:80]
        return self._dir / f"{safe}.json"

    def _load_all(self) -> None:
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                s = Session.from_dict(data)
                self._sessions[s.id] = s
            except Exception:
                continue

    def _persist(self, session: Session) -> None:
        path = self._path(session.id)
        path.write_text(json.dumps(session.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def get_or_create(self, session_id: str | None, mode: str = "balanced", language: str | None = None) -> Session:
        with self._lock:
            if session_id and session_id in self._sessions:
                s = self._sessions[session_id]
                if mode:
                    s.mode = mode
                if language:
                    s.language = language
                return s
            sid = session_id or str(uuid.uuid4())
            s = Session(id=sid, mode=mode or "balanced", language=language or "fr")
            self._sessions[sid] = s
            self._persist(s)
            return s

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def create(self, title: str | None = None, mode: str = "balanced", language: str = "fr") -> Session:
        with self._lock:
            s = Session(
                id=str(uuid.uuid4()),
                mode=mode,
                language=language,
                title=(title or "Nouvelle conversation").strip() or "Nouvelle conversation",
            )
            self._sessions[s.id] = s
            self._persist(s)
            return s

    def save(self, session: Session) -> None:
        with self._lock:
            session.updated_at = _now()
            self._sessions[session.id] = session
            self._persist(session)

    def upsert_messages(
        self,
        session_id: str,
        messages: list[dict],
        *,
        title: str | None = None,
        mode: str | None = None,
        language: str | None = None,
    ) -> Session:
        with self._lock:
            s = self._sessions.get(session_id) or Session(id=session_id)
            s.messages = [
                Message(
                    role=m.get("role", "user"),
                    content=m.get("content", ""),
                    modality=m.get("modality", "text"),
                    file_url=m.get("file_url"),
                    created_at=m.get("created_at") or _now(),
                )
                for m in messages
                if m.get("content")
            ][-80:]
            if title:
                s.title = title.strip()[:80]
            elif s.title == "Nouvelle conversation":
                for m in s.messages:
                    if m.role == "user":
                        s.title = _title_from(m.content)
                        break
            if mode:
                s.mode = mode
            if language:
                s.language = language
            s.updated_at = _now()
            self._sessions[s.id] = s
            self._persist(s)
            return s

    def list_sessions(self, ids: list[str] | None = None, limit: int = 50) -> list[dict]:
        with self._lock:
            sessions = list(self._sessions.values())
            if ids is not None:
                idset = set(ids)
                sessions = [s for s in sessions if s.id in idset]
            sessions.sort(key=lambda s: s.updated_at, reverse=True)
            return [
                {
                    "id": s.id,
                    "title": s.title,
                    "updated_at": s.updated_at,
                    "created_at": s.created_at,
                    "preview": s.preview(),
                    "message_count": len(s.messages),
                    "mode": s.mode,
                    "language": s.language,
                }
                for s in sessions[:limit]
            ]

    def delete(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False
            del self._sessions[session_id]
            path = self._path(session_id)
            if path.exists():
                path.unlink()
            return True

    def rename(self, session_id: str, title: str) -> Session | None:
        with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return None
            s.title = title.strip()[:80] or s.title
            s.updated_at = _now()
            self._persist(s)
            return s

    def reset(self, session_id: str) -> Session:
        with self._lock:
            s = Session(id=session_id)
            self._sessions[session_id] = s
            self._persist(s)
            return s


STORE = MemoryStore()


def extract_name(text: str) -> str | None:
    m = re.search(
        r"(?:je m'?\s*appelle|mon nom est|i am|i'm|my name is)\s+([A-Za-zÀ-ÿ][\wÀ-ÿ'-]{1,30})",
        text,
        flags=re.IGNORECASE,
    )
    return m.group(1).strip() if m else None
