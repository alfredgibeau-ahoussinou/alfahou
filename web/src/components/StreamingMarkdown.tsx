import { useEffect, useRef, useState } from "react";

type Props = {
  text: string;
  className?: string;
  /** Effet frappe type ChatGPT */
  animate?: boolean;
  onDone?: () => void;
  onProgress?: () => void;
};

/**
 * Affiche le markdown progressivement (rafales de caractères),
 * avec curseur clignotant pendant l’animation.
 */
export function StreamingMarkdown({ text, className, animate = false, onDone, onProgress }: Props) {
  const [shown, setShown] = useState(animate ? "" : text);
  const [streaming, setStreaming] = useState(!!animate);
  const onDoneRef = useRef(onDone);
  const onProgressRef = useRef(onProgress);
  onDoneRef.current = onDone;
  onProgressRef.current = onProgress;

  useEffect(() => {
    if (!animate) {
      setShown(text);
      setStreaming(false);
      return;
    }

    setShown("");
    setStreaming(true);
    let i = 0;
    let raf = 0;
    let last = performance.now();
    let finished = false;
    const len = text.length;
    const cps = len > 900 ? 140 : len > 400 ? 95 : len > 160 ? 70 : 48;

    const finish = () => {
      if (finished) return;
      finished = true;
      setShown(text);
      setStreaming(false);
      onDoneRef.current?.();
    };

    const step = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      i = Math.min(len, i + cps * dt);
      const next = Math.floor(i);
      setShown(text.slice(0, next));
      onProgressRef.current?.();
      if (next < len) {
        raf = requestAnimationFrame(step);
      } else {
        finish();
      }
    };

    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
    };
  }, [text, animate]);

  const skip = () => {
    if (!streaming) return;
    setShown(text);
    setStreaming(false);
    onDoneRef.current?.();
  };

  return (
    <div
      className={className}
      onClick={skip}
      onKeyDown={(e) => {
        if (streaming && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          skip();
        }
      }}
      role={streaming ? "button" : undefined}
      tabIndex={streaming ? 0 : undefined}
      title={streaming ? "Cliquer pour afficher tout" : undefined}
    >
      <span dangerouslySetInnerHTML={{ __html: renderLiteMarkdown(shown) }} />
      {streaming && <span className="stream-caret" aria-hidden />}
    </div>
  );
}

/** Markdown léger sûr pour le flux partiel. */
function renderLiteMarkdown(text: string) {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, _l, code) => `<pre><code>${code.trim()}</code></pre>`);
  html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^(?:- |\* )(.+)$/gm, "<li>$1</li>");
  html = html.replace(/(?:^|\n)(\d+)\. (.+)$/gm, "<li>$2</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
}
