"""LLM cloud moderne — Groq GPT-OSS / Compound, OpenRouter, HF, Ollama."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from alfahou.core.config import settings

# Modèles 2026 (Llama 3.3 70B est déprécié chez Groq → shutdown 16/08/2026)
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_FAST_MODEL = "openai/gpt-oss-20b"
GROQ_COMPOUND = "groq/compound"
OPENROUTER_DEFAULT = "openai/gpt-oss-120b"
HF_DEFAULT = "Qwen/Qwen3-32B"

SYSTEM_PROMPT = """Tu es AlfAhou, l’IA multimédia d’Alfred Ahoussinou.
Tu réponds comme un excellent assistant moderne : naturel, direct, utile, à jour.
Tu as un accès LIVE au web (outil browser_search) et à un interpréteur de code.
Nous sommes en 2026. Interdit de dire que tes connaissances s’arrêtent en 2023 ou 2024.
Si on te demande jusqu’où vont tes connaissances, la date du jour, l’actualité, des versions logicielles, des prix, la météo, un résultat sportif, ou tout fait après mi-2024 : utilise browser_search avant de répondre.
Ne laisse jamais une réponse « mes connaissances s’arrêtent en 2024 » — cherche, puis réponds avec la date réelle.
Tu parles français ou anglais selon l’utilisateur.
Tu aides sur tout sujet : conversation, explications, rédaction, code, idées, plans.
Tu peux aussi proposer de créer une image, une vidéo ou un PDF (modalité choisie dans l’UI).
Ne dis pas que tu es ChatGPT, Gemini ou Claude. Tu es AlfAhou.
Sois concis quand la question est courte ; développe quand on te le demande.
N’invente pas de dates ni d’événements : si tu n’es pas sûr, cherche ou dis-le clairement.
Ne laisse pas de marqueurs de citation techniques du type 【…】 dans ta réponse."""


def _needs_live_web(text: str) -> bool:
    t = (text or "").lower()
    keys = (
        "connaissance",
        "cutoff",
        "cut-off",
        "jusqu",
        "aujourd",
        "date du jour",
        "quelle année",
        "quelle annee",
        "actualité",
        "actualite",
        "actu ",
        "news",
        "2025",
        "2026",
        "récent",
        "recent",
        "cette semaine",
        "ce mois",
        "météo",
        "meteo",
        "prix de",
        "cours de",
        "qui a gagné",
        "qui a gagne",
        "dernière version",
        "derniere version",
        "maintenant",
        "en ce moment",
        "à jour",
        "a jour",
        "live",
        "current",
        "today",
        "latest",
    )
    return any(k in t for k in keys)


def _pick_api_key() -> str:
    return (
        (settings.llm_api_key or "").strip()
        or os.environ.get("ALFAHOU_LLM_API_KEY", "").strip()
        or os.environ.get("GROQ_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
        or os.environ.get("HF_TOKEN", "").strip()
        or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
    )


def _clean_answer(text: str) -> str:
    """Retire les marqueurs de citation internes (browser_search Groq)."""
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


class CloudLLM:
    """Client chat completions (Groq GPT-OSS/Compound, OpenRouter, HF, Ollama)."""

    def __init__(self) -> None:
        self.provider = (settings.llm_provider or "auto").lower().strip()
        self.api_key = _pick_api_key()
        self.model = (settings.llm_model or "").strip()
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.timeout = settings.llm_timeout
        self._resolved: tuple[str, str, str] | None = None
        self.last_error: str | None = None

    def _resolve(self) -> tuple[str, str, str] | None:
        if self._resolved is not None:
            return self._resolved if self._resolved[0] else None

        key = self.api_key
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        hf_key = (
            os.environ.get("HF_TOKEN", "").strip()
            or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
            or (key if key.startswith("hf_") else "")
        )
        if key.startswith("gsk_"):
            groq_key = groq_key or key
        if key.startswith("sk-or-"):
            or_key = or_key or key
        if key.startswith("hf_"):
            hf_key = hf_key or key
        if key and not groq_key and not or_key and not hf_key:
            if self.provider == "groq":
                groq_key = key
            elif self.provider in {"openrouter", "or"}:
                or_key = key
            else:
                hf_key = key

        if self.provider == "ollama":
            base = self.base_url if self.base_url and "11434" in self.base_url else "http://127.0.0.1:11434/v1"
            model = self.model or "qwen2.5:7b"
            self._resolved = ("ollama", base, model)
            return self._resolved

        if self.provider in {"openrouter", "or"} and or_key:
            self.api_key = or_key
            model = self.model or OPENROUTER_DEFAULT
            self._resolved = ("openrouter", "https://openrouter.ai/api/v1", model)
            return self._resolved

        # Groq : modèles 2026 + outils (recherche web)
        if self.provider in {"groq", "auto", "compound"} and groq_key:
            self.api_key = groq_key
            if self.provider == "compound":
                model = GROQ_COMPOUND
            elif self.model:
                model = self.model
                # Migrer automatiquement les anciens IDs dépréciés
                if model in {
                    "llama-3.3-70b-versatile",
                    "llama-3.1-8b-instant",
                    "llama3-70b-8192",
                    "llama3-8b-8192",
                    "meta-llama/llama-4-scout-17b-16e-instruct",
                    "qwen/qwen3-32b",
                }:
                    model = GROQ_DEFAULT_MODEL
            else:
                model = GROQ_DEFAULT_MODEL
            if self.provider == "auto" and not self.model:
                model = GROQ_DEFAULT_MODEL
            self._resolved = ("groq", "https://api.groq.com/openai/v1", model)
            return self._resolved

        if self.provider in {"hf", "huggingface", "auto"} and hf_key:
            self.api_key = hf_key
            base = (
                self.base_url
                if self.base_url and ("huggingface" in self.base_url or "hf.co" in self.base_url)
                else "https://router.huggingface.co/v1"
            )
            model = self.model or HF_DEFAULT
            self._resolved = ("hf", base, model)
            return self._resolved

        # OpenRouter en secours si présent
        if self.provider == "auto" and or_key:
            self.api_key = or_key
            self._resolved = ("openrouter", "https://openrouter.ai/api/v1", self.model or OPENROUTER_DEFAULT)
            return self._resolved

        if self.provider == "groq" and not groq_key:
            self._resolved = ("", "", "")
            return None

        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.4)
            self._resolved = ("ollama", "http://127.0.0.1:11434/v1", self.model or "qwen2.5:7b")
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
            return {"enabled": False, "provider": None, "model": None, "last_error": self.last_error}
        provider, base, model = resolved
        return {
            "enabled": True,
            "provider": provider,
            "model": model,
            "base_url": base,
            "tools": self._tools_for(provider, model) is not None,
            "last_error": self.last_error,
        }

    def _tools_for(self, provider: str, model: str) -> list[dict[str, str]] | None:
        """Outils serveur Groq (recherche web + code) — infos à jour."""
        if provider != "groq":
            return None
        mid = model.lower()
        if mid.startswith("groq/compound"):
            return None  # Compound orchestre ses outils tout seul
        if mid in {
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-safeguard-20b",
        }:
            return [{"type": "browser_search"}, {"type": "code_interpreter"}]
        return None

    def _mode_hint(self, mode: str, lang: str) -> str:
        today = date.today().isoformat()
        stamp = (
            f"Date du jour : {today}. Année en cours : {date.today().year}. "
            "Tu as browser_search : utilise-le pour tout fait temporel ou postérieur à 2024. "
            "Ne mentionne jamais un cutoff 2023/2024."
        )
        if mode == "creative":
            base = "Mode créatif : sois inventif, images mentales, ton vivant." if lang == "fr" else "Creative mode: inventive and vivid."
        elif mode == "precise":
            base = "Mode précis : réponses factuelles, structurées, sans fioritures." if lang == "fr" else "Precise mode: factual and tight."
        elif mode == "teacher":
            base = "Mode prof : explique clairement, étapes, encourage." if lang == "fr" else "Teacher mode: clear steps and encouragement."
        else:
            base = "Mode équilibré : clair, utile, conversationnel." if lang == "fr" else "Balanced mode: clear and conversational."
        return f"{base} {stamp}"

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

        max_tok = settings.llm_max_tokens
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.7 if mode != "precise" else 0.3,
        }
        # GPT-OSS / Compound préfèrent max_completion_tokens
        if provider == "groq":
            payload["max_completion_tokens"] = max_tok
        else:
            payload["max_tokens"] = max_tok

        tools = self._tools_for(provider, model)
        if tools:
            payload["tools"] = tools
            # Force la recherche pour les questions « cutoff / actu / date »
            if _needs_live_web(user_message):
                payload["tool_choice"] = "required"
                payload["tools"] = [{"type": "browser_search"}]

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AlfAhou/1.1 (+https://github.com/alfredgibeau-ahoussinou/alfahou)",
            "Accept": "application/json",
        }
        if provider == "groq":
            headers["Groq-Model-Version"] = "latest"
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://alfahou.netlify.app"
            headers["X-Title"] = "AlfAhou"
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
            body = e.read().decode("utf-8", errors="replace")[:500]
            self.last_error = f"HTTP {e.code}: {body}"
            # Fallback chaîne : HF 402 → Groq ; modèle invalide → GPT-OSS
            if e.code in {402, 429} and provider == "hf" and os.environ.get("GROQ_API_KEY", "").strip():
                self._resolved = None
                self.provider = "groq"
                self.api_key = os.environ.get("GROQ_API_KEY", "").strip()
                self.model = GROQ_DEFAULT_MODEL
                return self.chat(
                    user_message=user_message,
                    history=history,
                    lang=lang,
                    mode=mode,
                    memory=memory,
                )
            if e.code in {400, 404} and provider == "groq" and model != GROQ_FAST_MODEL:
                self._resolved = ("groq", "https://api.groq.com/openai/v1", GROQ_FAST_MODEL)
                return self.chat(
                    user_message=user_message,
                    history=history,
                    lang=lang,
                    mode=mode,
                    memory=memory,
                )
            raise RuntimeError(self.last_error) from e
        except Exception as e:
            self.last_error = str(e)
            raise RuntimeError(f"LLM indisponible: {e}") from e

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            self.last_error = f"Réponse invalide: {str(data)[:300]}"
            raise RuntimeError(self.last_error) from e
        self.last_error = None
        cleaned = _clean_answer(text or "")
        return cleaned or None


_llm: CloudLLM | None = None


def get_llm() -> CloudLLM:
    global _llm
    if _llm is None:
        _llm = CloudLLM()
    return _llm
