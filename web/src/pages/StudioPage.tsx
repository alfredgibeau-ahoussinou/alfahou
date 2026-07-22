import { useCallback, useEffect, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  assetUrl,
  createSession,
  deleteSession,
  fetchHealth,
  fetchSession,
  forgetSessionId,
  getActiveSessionId,
  listOwnedSessions,
  rememberSessionId,
  sendChat,
  type Modality,
  type Mode,
  type SessionSummary,
} from "../lib/api";

type Turn = {
  id: string;
  role: "you" | "bot";
  text: string;
  fileUrl?: string | null;
  modality?: string;
  when: string;
  welcome?: boolean;
};

function stamp(iso?: string) {
  const d = iso ? new Date(iso) : new Date();
  if (Number.isNaN(d.getTime())) {
    return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function formatDay(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function renderMarkdown(text: string) {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, _l, code) => `<pre><code>${code.trim()}</code></pre>`);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^(?:- |\* )(.+)$/gm, "<li>$1</li>");
  html = html.replace(/(?:^|\n)(\d+)\. (.+)$/gm, "<li>$2</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
}

const MODS: { value: Modality; label: string }[] = [
  { value: "auto", label: "Auto" },
  { value: "text", label: "Texte" },
  { value: "image", label: "Image" },
  { value: "video", label: "Vidéo" },
  { value: "pdf", label: "PDF" },
];

const WELCOME: Turn = {
  id: "welcome",
  role: "bot",
  text: "Bienvenue dans l’atelier. Dis-moi ce que tu veux — une idée, un texte, une image, une vidéo, un PDF.",
  when: "maintenant",
  welcome: true,
};

function turnsFromSession(messages: SessionDetailMessages): Turn[] {
  const mapped = messages
    .filter((m) => m.role === "user" || m.role === "assistant")
    .map((m) => ({
      id: crypto.randomUUID(),
      role: (m.role === "user" ? "you" : "bot") as "you" | "bot",
      text: m.content,
      fileUrl: m.file_url,
      modality: m.modality,
      when: stamp(m.created_at),
    }));
  return mapped.length ? mapped : [{ ...WELCOME, id: crypto.randomUUID() }];
}

type SessionDetailMessages = Array<{
  role: string;
  content: string;
  modality?: string;
  file_url?: string | null;
  created_at?: string;
}>;

export function StudioPage() {
  const [turns, setTurns] = useState<Turn[]>([{ ...WELCOME }]);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<Mode>("balanced");
  const [modality, setModality] = useState<Modality>("auto");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState("");
  const [suggestions, setSuggestions] = useState(["Bonjour", "Que sais-tu faire ?", "Explique l’IA"]);
  const [health, setHealth] = useState("connexion…");
  const [speak, setSpeak] = useState(() => localStorage.getItem("alfahou_speak") === "1");
  const [lastBot, setLastBot] = useState("");
  const [currentTitle, setCurrentTitle] = useState("Nouvelle conversation");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const bootRef = useRef(false);

  const refreshSessions = useCallback(async () => {
    try {
      const list = await listOwnedSessions();
      setSessions(list);
    } catch {
      /* offline / empty */
    }
  }, []);

  const loadConversation = useCallback(async (id: string): Promise<boolean> => {
    try {
      const detail = await fetchSession(id);
      rememberSessionId(id);
      setSessionId(id);
      setCurrentTitle(detail.title || "Conversation");
      setMode((detail.mode as Mode) || "balanced");
      setTurns(turnsFromSession(detail.messages || []));
      setSuggestions([]);
      setStatus("");
      setSidebarOpen(false);
      const last = [...(detail.messages || [])].reverse().find((m) => m.role === "assistant");
      setLastBot(last?.content || "");
      return true;
    } catch {
      forgetSessionId(id);
      setStatus("");
      return false;
    }
  }, []);

  const startNewConversation = useCallback(async () => {
    try {
      const s = await createSession({ mode, language: "fr" });
      rememberSessionId(s.id);
      setSessionId(s.id);
      setCurrentTitle(s.title || "Nouvelle conversation");
      setTurns([{ ...WELCOME, id: crypto.randomUUID() }]);
      setSuggestions(["Bonjour", "Que sais-tu faire ?", "Explique l’IA"]);
      setStatus("");
      setLastBot("");
      setSidebarOpen(false);
      document.body.classList.remove("busy");
      await refreshSessions();
      taRef.current?.focus();
    } catch (err) {
      // L’API chat peut créer la session au premier message.
      setSessionId(null);
      localStorage.removeItem("alfahou_session");
      setTurns([{ ...WELCOME, id: crypto.randomUUID() }]);
      setCurrentTitle("Nouvelle conversation");
      setStatus(
        err instanceof Error && err.message
          ? `Session locale prête — envoie un message (${err.message}).`
          : "Session locale prête — envoie un message pour démarrer.",
      );
    }
  }, [mode, refreshSessions]);

  useEffect(() => {
    fetchHealth()
      .then((d) => {
        const llm = d.models?.llm;
        const bit = llm?.enabled ? ` · LLM ${llm.provider || "cloud"}` : " · mode léger";
        setHealth(`${d.device} · en ligne${bit}`);
      })
      .catch(() => setHealth("hors ligne"));
  }, []);

  useEffect(() => {
    if (bootRef.current) return;
    bootRef.current = true;
    (async () => {
      await refreshSessions();
      const active = getActiveSessionId();
      if (active) {
        const ok = await loadConversation(active);
        if (ok) return;
      }
      await startNewConversation();
    })();
  }, [loadConversation, refreshSessions, startNewConversation]);

  useEffect(() => {
    document.body.classList.toggle("busy", busy || turns.some((t) => !t.welcome));
  }, [busy, turns]);

  const autoSize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 136)}px`;
  };

  const speakText = (text: string) => {
    if (!speak || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 600));
    u.lang = /[éèàùç]/i.test(text) ? "fr-FR" : "en-US";
    window.speechSynthesis.speak(u);
  };

  const onSubmit = async (e?: FormEvent, forced?: string) => {
    e?.preventDefault();
    const value = (forced ?? prompt).trim();
    if (!value || busy) return;

    let activeId = sessionId;

    setBusy(true);
    setStatus("");
    setSuggestions([]);
    setPrompt("");
    setTurns((t) => [...t.filter((x) => !x.welcome), { id: crypto.randomUUID(), role: "you", text: value, when: stamp() }]);
    setTyping(true);

    try {
      // Si pas encore de session, on en crée une ; sinon le chat en crée une au besoin.
      if (!activeId) {
        try {
          const s = await createSession({ mode, language: "fr" });
          activeId = s.id;
          rememberSessionId(s.id);
          setSessionId(s.id);
        } catch {
          activeId = null;
        }
      }

      const data = await sendChat({
        prompt: value,
        session_id: activeId,
        modality,
        mode,
      });
      rememberSessionId(data.session_id);
      setSessionId(data.session_id);
      if (data.title) setCurrentTitle(data.title);
      setTyping(false);
      setLastBot(data.text || "");
      setTurns((t) => [
        ...t,
        {
          id: crypto.randomUUID(),
          role: "bot",
          text: data.text,
          fileUrl: data.file_url,
          modality: data.modality,
          when: stamp(),
        },
      ]);
      setSuggestions(data.suggestions || []);
      speakText(data.text || "");
      await refreshSessions();
    } catch (err) {
      setTyping(false);
      const msg =
        err instanceof Error && err.name === "AbortError"
          ? "Toujours en route… réessaie."
          : err instanceof Error
            ? err.message
            : "Je n’ai pas pu répondre.";
      setTurns((t) => [...t, { id: crypto.randomUUID(), role: "bot", text: msg, when: stamp() }]);
      setStatus(msg);
    } finally {
      setBusy(false);
      requestAnimationFrame(() => {
        taRef.current?.focus();
        autoSize();
        threadRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
      });
    }
  };

  const onDelete = async (id: string, e: MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteSession(id);
      await refreshSessions();
      if (sessionId === id) await startNewConversation();
    } catch {
      setStatus("Suppression impossible.");
    }
  };

  return (
    <div className="relative z-10 flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-white/10 bg-[rgba(6,7,8,0.65)] px-[clamp(1rem,3vw,2rem)] py-3 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={() => setSidebarOpen((v) => !v)}
            className="border border-white/15 px-3 py-2 text-[0.7rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase hover:border-[var(--color-foil)] hover:text-[var(--color-ink)] lg:hidden"
            aria-expanded={sidebarOpen}
          >
            Historique
          </button>
          <Link to="/" className="font-brand text-[1.15rem] font-extrabold tracking-[-0.04em]">
            AlfAhou
          </Link>
          <p className="hidden truncate text-[0.7rem] text-[var(--color-mute)] sm:block">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 bg-[var(--color-foil)] shadow-[0_0_0_3px_rgba(212,184,150,0.15)]" />
            {health}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-0.5">
          <button
            type="button"
            onClick={startNewConversation}
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-foil)] uppercase hover:text-[var(--color-ink)]"
          >
            + Nouveau
          </button>
          <Link
            to="/manifeste"
            className="hidden px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase hover:text-[var(--color-ink)] sm:inline"
          >
            Manifeste
          </Link>
          <button
            type="button"
            onClick={() => {
              const next = !speak;
              setSpeak(next);
              localStorage.setItem("alfahou_speak", next ? "1" : "0");
              if (next && lastBot) speakText(lastBot);
              else window.speechSynthesis?.cancel();
            }}
            className={`px-3 py-2.5 text-[0.75rem] tracking-[0.12em] uppercase ${speak ? "text-[var(--color-foil)]" : "text-[var(--color-ink-dim)] hover:text-[var(--color-ink)]"}`}
          >
            Voix
          </button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[1280px] flex-1 gap-0 px-0 md:gap-6 md:px-[clamp(1rem,3vw,2rem)] md:pt-4 md:pb-6">
        {/* Sidebar conversations */}
        <aside
          className={`fixed inset-y-0 left-0 z-30 flex w-[min(20rem,88vw)] flex-col border-r border-white/10 bg-[rgba(8,10,11,0.96)] pt-[3.6rem] backdrop-blur-xl transition-transform duration-300 lg:static lg:z-0 lg:w-[17.5rem] lg:shrink-0 lg:translate-x-0 lg:border lg:border-white/10 lg:bg-[rgba(13,16,18,0.55)] lg:pt-0 lg:backdrop-blur-md ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          }`}
        >
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <p className="text-[0.68rem] tracking-[0.18em] text-[var(--color-foil)] uppercase">Conversations</p>
            <button
              type="button"
              onClick={startNewConversation}
              className="text-[0.72rem] tracking-[0.08em] text-[var(--color-ink-dim)] uppercase hover:text-[var(--color-ink)]"
            >
              + Nouveau
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {sessions.length === 0 && (
              <p className="px-3 py-6 text-[0.85rem] font-light text-[var(--color-mute)]">
                Aucune conversation pour l’instant. Envoie un message pour commencer.
              </p>
            )}
            {sessions.map((s) => {
              const active = s.id === sessionId;
              return (
                <div
                  key={s.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => loadConversation(s.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") loadConversation(s.id);
                  }}
                  className={`group mb-1 flex cursor-pointer items-start gap-2 rounded-sm border px-3 py-3 transition ${
                    active
                      ? "border-[var(--color-foil)]/50 bg-[rgba(212,184,150,0.08)]"
                      : "border-transparent hover:border-white/10 hover:bg-white/[0.03]"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[0.88rem] font-medium text-[var(--color-ink)]">{s.title}</p>
                    <p className="mt-1 truncate text-[0.72rem] text-[var(--color-mute)]">
                      {formatDay(s.updated_at)} · {s.preview || "…"}
                    </p>
                  </div>
                  <button
                    type="button"
                    aria-label="Supprimer"
                    onClick={(e) => onDelete(s.id, e)}
                    className="shrink-0 px-1 text-[0.7rem] text-[var(--color-mute)] opacity-0 transition group-hover:opacity-100 hover:text-[var(--color-danger)]"
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        </aside>

        {sidebarOpen && (
          <button
            type="button"
            aria-label="Fermer"
            className="fixed inset-0 z-20 bg-black/50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <div className="flex min-w-0 flex-1 flex-col px-[clamp(1rem,3vw,1.5rem)] pb-[calc(5.5rem+env(safe-area-inset-bottom))] lg:px-0 lg:pb-0">
          <div className="mb-3 hidden items-end justify-between gap-4 border-b border-white/10 pb-4 lg:flex">
            <div>
              <p className="text-[0.65rem] tracking-[0.16em] text-[var(--color-mute)] uppercase">Fil actif</p>
              <h2 className="font-mega mt-1 text-[1.6rem] font-semibold tracking-[-0.02em] italic">{currentTitle}</h2>
            </div>
            <div className="flex flex-col items-end gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-[0.65rem] tracking-[0.14em] text-[var(--color-mute)] uppercase">Mode</span>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as Mode)}
                  className="appearance-none border-0 border-b border-white/20 bg-transparent py-1.5 pr-6 text-[0.9rem] text-[var(--color-ink)]"
                >
                  <option value="balanced">Équilibré</option>
                  <option value="creative">Créatif</option>
                  <option value="precise">Précis</option>
                  <option value="teacher">Prof</option>
                </select>
              </label>
              <div className="flex border-b border-white/10" role="radiogroup" aria-label="Modalité">
                {MODS.map((m) => (
                  <label key={m.value} className="relative cursor-pointer">
                    <input
                      type="radio"
                      name="modality"
                      value={m.value}
                      checked={modality === m.value}
                      onChange={() => setModality(m.value)}
                      className="absolute opacity-0"
                    />
                    <span
                      className={`mb-[-1px] block px-2.5 py-2 text-[0.75rem] ${
                        modality === m.value
                          ? "border-b border-[var(--color-foil)] text-[var(--color-ink)]"
                          : "border-b border-transparent text-[var(--color-mute)]"
                      }`}
                    >
                      {m.label}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          {/* Mobile controls */}
          <div className="mb-3 flex flex-col gap-3 lg:hidden">
            <h2 className="font-mega text-[1.35rem] font-semibold italic">{currentTitle}</h2>
            <div className="flex flex-wrap items-end gap-4">
              <label className="flex flex-col gap-1">
                <span className="text-[0.65rem] tracking-[0.14em] text-[var(--color-mute)] uppercase">Mode</span>
                <select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as Mode)}
                  className="appearance-none border-0 border-b border-white/20 bg-transparent py-1.5 pr-6 text-[0.9rem]"
                >
                  <option value="balanced">Équilibré</option>
                  <option value="creative">Créatif</option>
                  <option value="precise">Précis</option>
                  <option value="teacher">Prof</option>
                </select>
              </label>
            </div>
            <div className="flex overflow-x-auto border-b border-white/10" role="radiogroup" aria-label="Modalité">
              {MODS.map((m) => (
                <label key={m.value} className="relative shrink-0 cursor-pointer">
                  <input
                    type="radio"
                    name="modality-mobile"
                    value={m.value}
                    checked={modality === m.value}
                    onChange={() => setModality(m.value)}
                    className="absolute opacity-0"
                  />
                  <span
                    className={`mb-[-1px] block px-3 py-2.5 text-[0.78rem] ${
                      modality === m.value
                        ? "border-b border-[var(--color-foil)] text-[var(--color-ink)]"
                        : "border-b border-transparent text-[var(--color-mute)]"
                    }`}
                  >
                    {m.label}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <section className="flex min-h-0 flex-1 flex-col gap-3 md:min-h-[calc(100dvh-8rem)] md:border md:border-white/10 md:bg-[rgba(13,16,18,0.45)] md:p-5 md:backdrop-blur-md">
            <div ref={threadRef} className="flex flex-1 flex-col gap-7 overflow-y-auto py-2 md:min-h-[12rem] md:py-4">
              <AnimatePresence initial={false}>
                {turns.map((t) => (
                  <motion.article
                    key={t.id}
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
                    className={`max-w-[38rem] ${t.role === "you" ? "max-w-none" : ""}`}
                  >
                    <header className="mb-2 flex justify-between gap-4">
                      <span className="text-[0.65rem] font-medium tracking-[0.16em] text-[var(--color-mute)] uppercase">
                        {t.role === "you" ? "Toi" : "AlfAhou"}
                      </span>
                      <time className="text-[0.72rem] text-[var(--color-mute)] tabular-nums">{t.when}</time>
                    </header>
                    {t.role === "you" ? (
                      <div className="font-mega border-l border-[var(--color-foil)] pl-4 text-[clamp(1.2rem,3vw,1.55rem)] leading-snug italic">
                        {t.text}
                      </div>
                    ) : (
                      <div
                        className={`text-[0.98rem] leading-relaxed font-light text-[var(--color-ink-dim)] [&_p]:mb-3 [&_p:last-child]:mb-0 [&_strong]:font-medium [&_strong]:text-[var(--color-ink)] ${
                          t.welcome
                            ? "font-mega max-w-[26ch] text-[clamp(1.15rem,2.8vw,1.45rem)] leading-snug text-[var(--color-ink)] italic"
                            : ""
                        }`}
                        dangerouslySetInnerHTML={{ __html: renderMarkdown(t.text) }}
                      />
                    )}
                    {t.fileUrl && t.role === "bot" && (
                      <div className="mt-4">
                        {(t.modality === "image" ||
                          t.fileUrl.endsWith(".png") ||
                          t.fileUrl.endsWith(".jpg")) && (
                          <img
                            src={assetUrl(t.fileUrl)}
                            alt="Image AlfAhou"
                            className="block w-full max-w-[28rem] border border-white/10 bg-black"
                          />
                        )}
                        {(t.modality === "video" || t.fileUrl.endsWith(".mp4")) && (
                          <video
                            src={assetUrl(t.fileUrl)}
                            controls
                            autoPlay
                            loop
                            className="block w-full max-w-[28rem] border border-white/10 bg-black"
                          />
                        )}
                        <p className="mt-2">
                          <a
                            href={assetUrl(t.fileUrl)}
                            download
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[0.68rem] tracking-[0.08em] text-[var(--color-foil)] uppercase"
                          >
                            Télécharger
                          </a>
                        </p>
                      </div>
                    )}
                  </motion.article>
                ))}
              </AnimatePresence>

              {typing && (
                <article className="max-w-[38rem]">
                  <header className="mb-2 flex justify-between gap-4">
                    <span className="text-[0.65rem] tracking-[0.16em] text-[var(--color-mute)] uppercase">AlfAhou</span>
                    <time className="text-[var(--color-mute)]">…</time>
                  </header>
                  <div className="flex gap-1.5 py-1">
                    <i className="block h-1 w-1 animate-pulse bg-[var(--color-foil)] opacity-40" />
                    <i className="block h-1 w-1 animate-pulse bg-[var(--color-foil)] opacity-40 [animation-delay:120ms]" />
                    <i className="block h-1 w-1 animate-pulse bg-[var(--color-foil)] opacity-40 [animation-delay:240ms]" />
                  </div>
                </article>
              )}
            </div>

            {suggestions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onSubmit(undefined, s)}
                    className="border border-white/15 bg-transparent px-3 py-2 text-[0.78rem] text-[var(--color-ink-dim)] transition hover:border-[var(--color-foil)] hover:text-[var(--color-ink)]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            <form
              onSubmit={onSubmit}
              className="fixed right-0 bottom-0 left-0 z-40 grid grid-cols-[1fr_auto] items-end gap-1.5 bg-[linear-gradient(180deg,transparent,rgba(6,7,8,0.95)_32%)] px-[clamp(1rem,3vw,1.5rem)] pt-3 pb-[calc(0.7rem+env(safe-area-inset-bottom))] md:relative md:bg-none md:px-0 md:pt-2 md:pb-0"
            >
              <div className="pointer-events-none absolute inset-x-[clamp(1rem,3vw,1.5rem)] inset-y-2 border border-white/15 bg-[rgba(13,16,18,0.82)] backdrop-blur-xl md:inset-0" />
              <textarea
                ref={taRef}
                value={prompt}
                onChange={(e) => {
                  setPrompt(e.target.value);
                  autoSize();
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    onSubmit();
                  }
                }}
                rows={1}
                required
                placeholder="Écrire dans l’atelier…"
                className="relative z-10 min-h-[2.75rem] max-h-32 w-full resize-none border-0 bg-transparent py-3.5 pl-4 text-[1rem] leading-relaxed font-light text-[var(--color-ink)] outline-none placeholder:text-[var(--color-mute)]"
              />
              <button
                type="submit"
                disabled={busy}
                className="relative z-10 m-1.5 inline-flex min-h-[2.75rem] items-center gap-2 bg-[var(--color-ink)] px-4 text-[0.68rem] font-semibold tracking-[0.12em] text-[var(--color-bg)] uppercase transition hover:bg-[var(--color-foil)] disabled:opacity-40"
              >
                <span className="hidden sm:inline">Envoyer</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden>
                  <path
                    d="M5 12h14M13 6l6 6-6 6"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </form>
            {status && <p className="relative z-10 text-[0.78rem] text-[var(--color-danger)]">{status}</p>}
          </section>
        </div>
      </div>
    </div>
  );
}
