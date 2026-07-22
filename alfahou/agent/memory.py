from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock


@dataclass
class Message:
    role: str  # user | assistant | system
    content: str
    modality: str = "text"
    file_url: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Session:
    id: str
    messages: list[Message] = field(default_factory=list)
    language: str = "fr"
    mode: str = "balanced"  # balanced | creative | precise | teacher
    memory: dict = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add(self, role: str, content: str, modality: str = "text", file_url: str | None = None) -> Message:
        msg = Message(role=role, content=content, modality=modality, file_url=file_url)
        self.messages.append(msg)
        # garder une fenêtre raisonnable
        if len(self.messages) > 40:
            self.messages = self.messages[-40:]
        self.updated_at = datetime.now(timezone.utc).isoformat()
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


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

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
            return s

    def reset(self, session_id: str) -> Session:
        with self._lock:
            s = Session(id=session_id)
            self._sessions[session_id] = s
            return s


STORE = MemoryStore()


def extract_name(text: str) -> str | None:
    m = re.search(
        r"(?:je m'?\s*appelle|mon nom est|i am|i'm|my name is)\s+([A-Za-zÀ-ÿ][\wÀ-ÿ'-]{1,30})",
        text,
        flags=re.IGNORECASE,
    )
    return m.group(1).strip() if m else None
