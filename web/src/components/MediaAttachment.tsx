import { useEffect, useState } from "react";
import { assetUrl } from "../lib/api";

type Props = {
  fileUrl: string;
  modality?: string;
};

type Kind = "image" | "video" | "pdf" | "file";

function detectKind(fileUrl: string, modality?: string): Kind {
  if (modality === "image" || /\.(png|jpe?g|webp|gif)$/i.test(fileUrl)) return "image";
  if (modality === "video" || /\.mp4$/i.test(fileUrl)) return "video";
  if (modality === "pdf" || /\.pdf$/i.test(fileUrl)) return "pdf";
  return "file";
}

export function MediaAttachment({ fileUrl, modality }: Props) {
  const href = assetUrl(fileUrl);
  const kind = detectKind(fileUrl, modality);
  const [broken, setBroken] = useState(false);
  const [pdfSrc, setPdfSrc] = useState<string | null>(null);
  const [pdfError, setPdfError] = useState(false);

  useEffect(() => {
    setBroken(false);
    setPdfError(false);
    setPdfSrc(null);
    if (kind !== "pdf") return;

    let revoke: string | null = null;
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(href);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        revoke = url;
        setPdfSrc(url);
      } catch {
        if (!cancelled) setPdfError(true);
      }
    })();

    return () => {
      cancelled = true;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [href, kind]);

  return (
    <div className="mt-4">
      {kind === "image" && !broken && (
        <img
          src={href}
          alt="Image AlfAhou"
          loading="lazy"
          decoding="async"
          onError={() => setBroken(true)}
          className="block w-full max-w-[min(40rem,100%)] rounded-[var(--radius-md)] border border-white/10 bg-black object-contain"
        />
      )}

      {kind === "video" && !broken && (
        <video
          src={href}
          controls
          playsInline
          autoPlay
          muted
          preload="metadata"
          onError={() => setBroken(true)}
          className="block w-full max-w-[min(40rem,100%)] rounded-[var(--radius-md)] border border-white/10 bg-black"
        />
      )}

      {kind === "pdf" && pdfSrc && !pdfError && (
        <object
          data={pdfSrc}
          type="application/pdf"
          title="PDF AlfAhou"
          className="mt-1 h-[min(28rem,55vh)] w-full max-w-[28rem] overflow-hidden rounded-[var(--radius-md)] border border-white/10 bg-[#f7f3eb]"
        >
          <p className="p-4 text-[0.9rem] text-[var(--color-ink-dim)]">
            Aperçu indisponible dans ce navigateur.
          </p>
        </object>
      )}

      {(broken || pdfError || (kind === "pdf" && !pdfSrc && !pdfError)) && (
        <div className="max-w-[28rem] rounded-[var(--radius-md)] border border-white/10 bg-white/[0.03] px-4 py-3 text-[0.92rem] text-[var(--color-ink-dim)]">
          {kind === "pdf" && !pdfSrc && !pdfError
            ? "Chargement de l’aperçu PDF…"
            : broken || pdfError
              ? "Aperçu impossible ici — ouvre ou télécharge le fichier."
              : null}
        </div>
      )}

      <p className="mt-2 flex flex-wrap gap-3">
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[0.72rem] tracking-[0.06em] text-[var(--color-foil)] uppercase"
        >
          Ouvrir
        </a>
        <a
          href={href}
          download
          target="_blank"
          rel="noopener noreferrer"
          className="text-[0.72rem] tracking-[0.06em] text-[var(--color-foil)] uppercase"
        >
          Télécharger
        </a>
      </p>
    </div>
  );
}
