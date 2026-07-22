import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  assetUrl,
  fetchHealth,
  resetChat,
  sendChat,
  type Modality,
  type Mode,
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

function stamp() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
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

export function StudioPage() {
  const [turns, setTurns] = useState<Turn[]>([
    {
      id: "welcome",
      role: "bot",
      text: "Bienvenue dans l’atelier. Dis-moi ce que tu veux — une idée, un texte, une image, une vidéo, un PDF.",
      when: "maintenant",
      welcome: true,
    },
  ]);
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<Mode>("balanced");
  const [modality, setModality] = useState<Modality>("auto");
  const [sessionId, setSessionId] = useState<string | null>(
    () => localStorage.getItem("alfahou_session"),
  );
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState("");
  const [suggestions, setSuggestions] = useState(["Bonjour", "Que sais-tu faire ?", "Explique l’IA"]);
  const [health, setHealth] = useState("connexion…");
  const [speak, setSpeak] = useState(() => localStorage.getItem("alfahou_speak") === "1");
  const [lastBot, setLastBot] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);

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
    document.body.classList.toggle("busy", busy || turns.length > 1);
  }, [busy, turns.length]);

  useEffect(() => {
    taRef.current?.focus();
  }, []);

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

    setBusy(true);
    setStatus("");
    setSuggestions([]);
    setPrompt("");
    setTurns((t) => [
      ...t,
      { id: crypto.randomUUID(), role: "you", text: value, when: stamp() },
    ]);
    setTyping(true);

    try {
      const data = await sendChat({
        prompt: value,
        session_id: sessionId,
        modality,
        mode,
      });
      setSessionId(data.session_id);
      localStorage.setItem("alfahou_session", data.session_id);
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
    } catch (err) {
      setTyping(false);
      const msg =
        err instanceof Error && err.name === "AbortError"
          ? "Toujours en route… réessaie."
          : err instanceof Error
            ? err.message
            : "Je n’ai pas pu répondre.";
      setTurns((t) => [
        ...t,
        { id: crypto.randomUUID(), role: "bot", text: msg, when: stamp() },
      ]);
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

  const onReset = async () => {
    if (sessionId) {
      try {
        await resetChat(sessionId);
      } catch {
        /* ignore */
      }
    }
    setSessionId(null);
    localStorage.removeItem("alfahou_session");
    setTurns([
      {
        id: crypto.randomUUID(),
        role: "bot",
        text: "Nouveau fil. Dis-moi ce que tu veux créer ou comprendre.",
        when: stamp(),
        welcome: true,
      },
    ]);
    setSuggestions(["Bonjour", "Que sais-tu faire ?", "Fais un plan"]);
    setStatus("");
    document.body.classList.remove("busy");
  };

  return (
    <div className="relative z-10 flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 flex items-center justify-between gap-4 border-b border-white/10 bg-[rgba(6,7,8,0.65)] px-[clamp(1.1rem,4vw,2.75rem)] py-3 backdrop-blur-md">
        <div className="flex min-w-0 items-center gap-4">
          <Link to="/" className="font-brand text-[1.15rem] font-extrabold tracking-[-0.04em]">
            AlfAhou
          </Link>
          <p className="truncate text-[0.7rem] text-[var(--color-mute)]">
            <span className="mr-1.5 inline-block h-1.5 w-1.5 bg-[var(--color-foil)] shadow-[0_0_0_3px_rgba(212,184,150,0.15)]" />
            {health}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-0.5">
          <Link
            to="/manifeste"
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase hover:text-[var(--color-ink)]"
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
          <button
            type="button"
            onClick={onReset}
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase hover:text-[var(--color-ink)]"
          >
            Nouveau
          </button>
          <a
            href="https://github.com/alfredgibeau-ahoussinou/alfahou"
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase hover:text-[var(--color-ink)]"
          >
            Code
          </a>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-[1180px] flex-1 grid-cols-1 gap-0 px-[clamp(1.1rem,4vw,2.75rem)] pb-[calc(5.5rem+env(safe-area-inset-bottom))] md:grid-cols-[minmax(260px,0.9fr)_minmax(0,1.35fr)] md:gap-[clamp(1.75rem,4vw,3.5rem)] md:pt-5 md:pb-7">
        <aside className="py-6 md:sticky md:top-[4.2rem] md:self-start md:py-6">
          <p className="rail-eyebrow mb-3 text-[0.68rem] tracking-[0.22em] text-[var(--color-foil)] uppercase">
            Atelier
          </p>
          <h2 className="font-mega rail-title text-[clamp(2.4rem,8vw,3.6rem)] leading-[0.95] font-semibold tracking-[-0.02em] italic">
            Créer
            <br />
            avec AlfAhou
          </h2>
          <p className="rail-copy mt-4 mb-6 max-w-[28ch] text-[0.95rem] leading-relaxed font-light text-[var(--color-ink-dim)]">
            Parle librement. Choisis une matière si tu veux — ou laisse Auto décider.
          </p>

          <label className="mb-5 flex max-w-[12rem] flex-col gap-1.5">
            <span className="text-[0.65rem] tracking-[0.14em] text-[var(--color-mute)] uppercase">
              Mode
            </span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value as Mode)}
              className="appearance-none border-0 border-b border-white/20 bg-transparent py-2 pr-6 text-[0.95rem] text-[var(--color-ink)]"
            >
              <option value="balanced">Équilibré</option>
              <option value="creative">Créatif</option>
              <option value="precise">Précis</option>
              <option value="teacher">Prof</option>
            </select>
          </label>

          <div className="flex flex-wrap border-b border-white/10" role="radiogroup" aria-label="Modalité">
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
                  className={`mb-[-1px] block px-3 py-2.5 text-[0.78rem] ${
                    modality === m.value
                      ? "border-b border-[var(--color-foil)] text-[var(--color-ink)]"
                      : "border-b border-transparent text-[var(--color-mute)] hover:text-[var(--color-ink)]"
                  }`}
                >
                  {m.label}
                </span>
              </label>
            ))}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col gap-3 md:grid md:min-h-[calc(100dvh-5rem)] md:grid-rows-[1fr_auto_auto] md:border md:border-white/10 md:bg-[rgba(13,16,18,0.55)] md:p-5 md:backdrop-blur-md">
          <div ref={threadRef} className="flex flex-1 flex-col gap-7 overflow-y-auto py-2 md:min-h-[12rem] md:py-5">
            <AnimatePresence initial={false}>
              {turns.map((t) => (
                <motion.article
                  key={t.id}
                  initial={{ opacity: 0, y: 16, clipPath: "inset(0 0 100% 0)" }}
                  animate={{ opacity: 1, y: 0, clipPath: "inset(0 0 0 0)" }}
                  transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
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
                  <span className="text-[0.65rem] tracking-[0.16em] text-[var(--color-mute)] uppercase">
                    AlfAhou
                  </span>
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
            className="fixed right-0 bottom-0 left-0 z-40 grid grid-cols-[1fr_auto] items-end gap-1.5 bg-[linear-gradient(180deg,transparent,rgba(6,7,8,0.95)_32%)] px-[clamp(1.1rem,4vw,2.75rem)] pt-3 pb-[calc(0.7rem+env(safe-area-inset-bottom))] md:relative md:bg-none md:px-0 md:pt-2 md:pb-0"
          >
            <div className="pointer-events-none absolute inset-x-[clamp(1.1rem,4vw,2.75rem)] inset-y-2 border border-white/15 bg-[rgba(13,16,18,0.82)] backdrop-blur-xl md:inset-0" />
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
  );
}
