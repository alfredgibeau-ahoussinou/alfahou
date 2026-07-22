"""LLM multi-route — style « plusieurs APIs » (Groq + OpenRouter + HF + Ollama).

Comme Cursor côté idée : un routeur essaie plusieurs fournisseurs / modèles
et bascule automatiquement si l’un est saturé (429) ou en erreur.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from alfahou.core.config import settings

GROQ_DEFAULT_MODEL = "openai/gpt-oss-20b"  # plus de marge quota que 120B
GROQ_STRONG_MODEL = "openai/gpt-oss-120b"
GROQ_COMPOUND = "groq/compound"
OPENROUTER_DEFAULT = "openai/gpt-oss-20b"
# Secours OpenRouter (un seul compte = plein de modèles, façon agrégateur)
OPENROUTER_FALLBACKS = (
    "google/gemini-2.5-flash",
    "deepseek/deepseek-chat-v3-0324",
    "meta-llama/llama-4-maverick:free",
    "qwen/qwen3-32b",
)
HF_DEFAULT = "Qwen/Qwen3-32B"

SYSTEM_PROMPT = """Tu es AlfAhou, l’IA multimédia d’Alfred Ahoussinou.
Tu réponds comme un excellent assistant moderne : naturel, direct, utile, à jour.
Tu as un accès LIVE au web quand l’outil browser_search est disponible.
Nous sommes en 2026. Interdit de dire que tes connaissances s’arrêtent en 2023 ou 2024.
Si on te demande jusqu’où vont tes connaissances, la date du jour, l’actualité, des versions logicielles, des prix, la météo, un résultat sportif, ou tout fait après mi-2024 : utilise browser_search avant de répondre si disponible ; sinon sois transparent.
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


def _clean_answer(text: str) -> str:
    text = re.sub(r"【[^】]*】", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def _keys() -> dict[str, str]:
    generic = (
        (settings.llm_api_key or "").strip()
        or os.environ.get("ALFAHOU_LLM_API_KEY", "").strip()
    )
    groq = os.environ.get("GROQ_API_KEY", "").strip()
    openrouter = os.environ.get("OPENROUTER_API_KEY", "").strip()
    hf = (
        os.environ.get("HF_TOKEN", "").strip()
        or os.environ.get("HUGGINGFACE_HUB_TOKEN", "").strip()
    )
    if generic.startswith("gsk_"):
        groq = groq or generic
    elif generic.startswith("sk-or-"):
        openrouter = openrouter or generic
    elif generic.startswith("hf_"):
        hf = hf or generic
    return {"groq": groq, "openrouter": openrouter, "hf": hf, "generic": generic}


Route = tuple[str, str, str, str]  # provider, base, model, api_key


class CloudLLM:
    """Routeur multi-fournisseurs : bascule auto si un cloud est saturé."""

    def __init__(self) -> None:
        self.provider = (settings.llm_provider or "auto").lower().strip()
        self.model = (settings.llm_model or "").strip()
        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.timeout = settings.llm_timeout
        self.last_error: str | None = None
        self.active: Route | None = None
        self._routes_cache: list[Route] | None = None

    def _build_routes(self) -> list[Route]:
        if self._routes_cache is not None:
            return self._routes_cache

        k = _keys()
        pref = self.provider
        model_pref = self.model
        routes: list[Route] = []

        def add(provider: str, base: str, model: str, key: str) -> None:
            if not model:
                return
            # dédup
            for p, b, m, _ in routes:
                if p == provider and m == model and b == base:
                    return
            routes.append((provider, base, model, key))

        # Mode forcé
        if pref == "ollama":
            base = self.base_url if self.base_url and "11434" in self.base_url else "http://127.0.0.1:11434/v1"
            add("ollama", base, model_pref or "qwen2.5:7b", "")
            self._routes_cache = routes
            return routes

        if pref in {"openrouter", "or"} and k["openrouter"]:
            add("openrouter", "https://openrouter.ai/api/v1", model_pref or OPENROUTER_DEFAULT, k["openrouter"])
            for m in OPENROUTER_FALLBACKS:
                add("openrouter", "https://openrouter.ai/api/v1", m, k["openrouter"])
            self._routes_cache = routes
            return routes

        if pref == "compound" and k["groq"]:
            add("groq", "https://api.groq.com/openai/v1", GROQ_COMPOUND, k["groq"])
            self._routes_cache = routes
            return routes

        if pref in {"hf", "huggingface"} and k["hf"]:
            base = (
                self.base_url
                if self.base_url and ("huggingface" in self.base_url or "hf.co" in self.base_url)
                else "https://router.huggingface.co/v1"
            )
            add("hf", base, model_pref or HF_DEFAULT, k["hf"])
            self._routes_cache = routes
            return routes

        if pref == "groq" and k["groq"]:
            m = model_pref or GROQ_DEFAULT_MODEL
            if m in {"llama-3.3-70b-versatile", "llama-3.1-8b-instant"}:
                m = GROQ_DEFAULT_MODEL
            add("groq", "https://api.groq.com/openai/v1", m, k["groq"])
            if m != GROQ_DEFAULT_MODEL:
                add("groq", "https://api.groq.com/openai/v1", GROQ_DEFAULT_MODEL, k["groq"])
            if m != GROQ_STRONG_MODEL:
                add("groq", "https://api.groq.com/openai/v1", GROQ_STRONG_MODEL, k["groq"])
            # puis OpenRouter / HF si présents
            if k["openrouter"]:
                add("openrouter", "https://openrouter.ai/api/v1", OPENROUTER_DEFAULT, k["openrouter"])
                for fm in OPENROUTER_FALLBACKS:
                    add("openrouter", "https://openrouter.ai/api/v1", fm, k["openrouter"])
            if k["hf"]:
                add("hf", "https://router.huggingface.co/v1", HF_DEFAULT, k["hf"])
            self._routes_cache = routes
            return routes

        # auto : chaîne complète façon Cursor (plusieurs backends)
        if k["groq"]:
            preferred = model_pref if model_pref and "llama-3" not in model_pref else GROQ_DEFAULT_MODEL
            if preferred in {"llama-3.3-70b-versatile", "llama-3.1-8b-instant"}:
                preferred = GROQ_DEFAULT_MODEL
            add("groq", "https://api.groq.com/openai/v1", preferred, k["groq"])
            if preferred != GROQ_DEFAULT_MODEL:
                add("groq", "https://api.groq.com/openai/v1", GROQ_DEFAULT_MODEL, k["groq"])
            add("groq", "https://api.groq.com/openai/v1", GROQ_STRONG_MODEL, k["groq"])
        if k["openrouter"]:
            add("openrouter", "https://openrouter.ai/api/v1", model_pref or OPENROUTER_DEFAULT, k["openrouter"])
            for fm in OPENROUTER_FALLBACKS:
                add("openrouter", "https://openrouter.ai/api/v1", fm, k["openrouter"])
        if k["hf"]:
            add("hf", "https://router.huggingface.co/v1", HF_DEFAULT, k["hf"])

        try:
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=0.3)
            add("ollama", "http://127.0.0.1:11434/v1", "qwen2.5:7b", "")
        except Exception:
            pass

        self._routes_cache = routes
        return routes

    def available(self) -> bool:
        if not settings.llm_enabled:
            return False
        return bool(self._build_routes())

    def status(self) -> dict[str, Any]:
        routes = self._build_routes()
        active = self.active or (routes[0] if routes else None)
        if not active:
            return {
                "enabled": False,
                "provider": None,
                "model": None,
                "routes": 0,
                "last_error": self.last_error,
            }
        provider, base, model, _ = active
        return {
            "enabled": True,
            "provider": provider,
            "model": model,
            "base_url": base,
            "tools": self._tools_for(provider, model) is not None,
            "routes": len(routes),
            "route_chain": [f"{p}:{m}" for p, _, m, _ in routes[:8]],
            "last_error": self.last_error,
        }

    def _tools_for(self, provider: str, model: str) -> list[dict[str, str]] | None:
        if provider != "groq":
            return None
        mid = model.lower()
        if mid.startswith("groq/compound"):
            return None
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

    def _messages(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]] | None,
        lang: str,
        mode: str,
        memory: dict | None,
    ) -> list[dict[str, str]]:
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
        return messages

    def _call_route(
        self,
        route: Route,
        messages: list[dict[str, str]],
        user_message: str,
        mode: str,
    ) -> str:
        provider, base, model, api_key = route
        max_tok = settings.llm_max_tokens
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.7 if mode != "precise" else 0.3,
        }
        if provider == "groq":
            payload["max_completion_tokens"] = max_tok
        else:
            payload["max_tokens"] = max_tok

        tools = self._tools_for(provider, model)
        if tools:
            payload["tools"] = tools
            if _needs_live_web(user_message):
                payload["tool_choice"] = "required"
                payload["tools"] = [{"type": "browser_search"}]

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AlfAhou/1.2 (+https://github.com/alfredgibeau-ahoussinou/alfahou)",
            "Accept": "application/json",
        }
        if provider == "groq":
            headers["Groq-Model-Version"] = "latest"
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://alfahou.netlify.app"
            headers["X-Title"] = "AlfAhou"
        if provider != "ollama" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(
            f"{base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        text = msg.get("content")
        if not text and isinstance(msg.get("reasoning"), str):
            text = msg.get("reasoning")
        cleaned = _clean_answer(text or "")
        if not cleaned:
            raise RuntimeError("Réponse vide")
        return cleaned

    def chat(
        self,
        *,
        user_message: str,
        history: list[dict[str, str]] | None = None,
        lang: str = "fr",
        mode: str = "balanced",
        memory: dict | None = None,
    ) -> str | None:
        routes = self._build_routes()
        if not routes:
            return None

        messages = self._messages(
            user_message=user_message,
            history=history,
            lang=lang,
            mode=mode,
            memory=memory,
        )
        errors: list[str] = []

        for idx, route in enumerate(routes):
            provider, _base, model, _key = route
            try:
                text = self._call_route(route, messages, user_message, mode)
                self.active = route
                self.last_error = None
                return text
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:350]
                err = f"{provider}/{model} → HTTP {e.code}: {body}"
                errors.append(err)
                self.last_error = err
                # 429 / 402 / 5xx → essayer la route suivante
                if e.code in {400, 404, 402, 429, 500, 502, 503} and idx + 1 < len(routes):
                    if e.code == 429:
                        time.sleep(0.8)
                    continue
                if idx + 1 < len(routes):
                    continue
                raise RuntimeError(self.last_error) from e
            except Exception as e:
                err = f"{provider}/{model} → {e}"
                errors.append(err)
                self.last_error = err
                if idx + 1 < len(routes):
                    continue
                raise RuntimeError(f"LLM indisponible: {e}") from e

        self.last_error = " | ".join(errors[-3:]) if errors else "aucune route"
        raise RuntimeError(self.last_error)


_llm: CloudLLM | None = None


def get_llm() -> CloudLLM:
    global _llm
    if _llm is None:
        _llm = CloudLLM()
    return _llm
