"""LLM open-source cloud — Hugging Face / Groq / Ollama (API compatible OpenAI)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from alfahou.core.config import settings

SYSTEM_PROMPT = """Tu es AlfAhou, l’IA multimédia d’Alfred Ahoussinou.
Tu réponds comme un excellent assistant moderne (niveau ChatGPT) : naturel, direct, utile, sans blabla marketing.
Tu parles français ou anglais selon l’utilisateur. Tu peux utiliser tout le vocabulaire courant.
Tu aides sur tout sujet : conversation, explications, rédaction, code, idées, plans.
Tu peux aussi proposer de créer une image, une vidéo ou un PDF quand c’est pertinent (l’utilisateur choisit la modalité dans l’UI).
Ne dis pas que tu es ChatGPT, Gemini ou Claude. Tu es AlfAhou.
Sois concis quand la question est courte ; développe quand on te le demande.
Pas de listes de « capacités » sauf si on te le demande explicitement."""


def _pick_api_key() -> str:
    return (
        (settings.llm_api_key or "").strip()
        or os.environ.get("ALFAHOU_LLM_API_KEY", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
        or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
        or os.environ.get("GROQ_API_KEY", "").strip()
    )


class CloudLLM:
    """Client chat completions (HF router, Groq, Ollama)."""

    def __init__(self) -> None:
        self.provider = (settings.llm_provider or "auto").lower().strip()
        self.api_key = _pick_api_key()
        self.model = (settings.llm_model or "").strip()
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.timeout = settings.llm_timeout
        self._resolved: tuple[str, str, str] | None = None

    def _resolve(self) -> tuple[str, str, str] | None:
        if self._resolved is not None:
            return self._resolved if self._resolved[0] else None

        key = self.api_key
        if self.provider == "ollama":
            base = self.base_url if self.base_url and "11434" in self.base_url else "http://127.0.0.1:11434/v1"
            model = self.model or "qwen2.5:3b"
            self._resolved = ("ollama", base, model)
            return self._resolved

        if self.provider in {"hf", "huggingface"}:
            if not key:
                self._resolved = ("", "", "")
                return None
            base = (
                self.base_url
                if self.base_url and ("huggingface" in self.base_url or "hf.co" in self.base_url)
                else "https://router.huggingface.co/v1"
            )
            model = self.model or "Qwen/Qwen2.5-7B-Instruct"
            self._resolved = ("hf", base, model)
            return self._resolved

        if self.provider == "groq":
            if not key:
                self._resolved = ("", "", "")
                return None
            base = self.base_url if self.base_url and "groq" in self.base_url else "https://api.groq.com/openai/v1"
            model = self.model or "llama-3.3-70b-versatile"
            self._resolved = ("groq", base, model)
            return self._resolved

        if key.startswith("gsk_"):
            self._resolved = (
                "groq",
                "https://api.groq.com/openai/v1",
                self.model or "llama-3.3-70b-versatile",
            )
            return self._resolved
        if key:
            self._resolved = (
                "hf",
                "https://router.huggingface.co/v1",
                self.model or "Qwen/Qwen2.5-7B-Instruct",
            )
            return self._resolved

        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.4)
            self._resolved = ("ollama", "http://127.0.0.1:11434/v1", self.model or "qwen2.5:3b")
            return self._resolved
        except Exception:
            pass

        self._resolved = ("", "", "")
        return None

    def available(self) -> bool:
        if not settings.llm_enabled:
            return False
        return self._resolve() is not None

    def status(self) -> dict[str, Any]:
        resolved = self._resolve()
        if not resolved:
            return {"enabled": False, "provider": None, "model": None}
        provider, base, model = resolved
        return {"enabled": True, "provider": provider, "model": model, "base_url": base}

    def _mode_hint(self, mode: str, lang: str) -> str:
        if mode == "creative":
            return "Mode créatif : sois inventif, images mentales, ton vivant." if lang == "fr" else "Creative mode: inventive and vivid."
        if mode == "precise":
            return "Mode précis : réponses factuelles, structurées, sans fioritures." if lang == "fr" else "Precise mode: factual and tight."
        if mode == "teacher":
            return "Mode prof : explique clairement, étapes, encourage." if lang == "fr" else "Teacher mode: clear steps and encouragement."
        return "Mode équilibré : clair, utile, conversationnel." if lang == "fr" else "Balanced mode: clear and conversational."

    def chat(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]] | None = None,
        lang: str = "fr",
        mode: str = "balanced",
        memory: dict | None = None,
    ) -> str | None:
        resolved = self._resolve()
        if not resolved:
            return None
        provider, base, model = resolved

        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.append({"role": "system", "content": self._mode_hint(mode, lang)})
        if memory and memory.get("name"):
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"L’utilisateur s’appelle {memory['name']}. Utilise son prénom avec naturel."
                        if lang == "fr"
                        else f"The user's name is {memory['name']}. Use it naturally."
                    ),
                }
            )
        if history:
            for m in history[-16:]:
                role = m.get("role")
                content = (m.get("content") or "").strip()
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content[:4000]})
        if not (history and history[-1].get("role") == "user" and history[-1].get("content") == user_message):
            messages.append({"role": "user", "content": user_message})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7 if mode != "precise" else 0.3,
            "max_tokens": settings.llm_max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if provider != "ollama" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{base}/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(f"LLM HTTP {e.code}: {body}") from e
        except Exception as e:
            raise RuntimeError(f"LLM indisponible: {e}") from e

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Réponse LLM invalide: {str(data)[:300]}") from e
        return (text or "").strip() or None


_llm: CloudLLM | None = None


def get_llm() -> CloudLLM:
    global _llm
    if _llm is None:
        _llm = CloudLLM()
    return _llm
