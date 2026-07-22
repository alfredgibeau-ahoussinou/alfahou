import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { useRef, type MouseEvent } from "react";
import { MagneticButton } from "../components/MagneticButton";
import { BrandLogo } from "../components/BrandLogo";

const CARDS = [
  {
    n: "01",
    title: "Présence",
    body: "Des réponses naturelles, directes, comme quelqu’un qui t’écoute vraiment.",
  },
  {
    n: "02",
    title: "Matière",
    body: "Texte, image, vidéo, PDF — un même geste créatif, plusieurs matières.",
  },
  {
    n: "03",
    title: "Signature",
    body: "Alfred + Ahoussinou. Une identité, pas un produit anonyme.",
  },
  {
    n: "04",
    title: "Exigence",
    body: "Le détail compte : le rythme, la lumière, le silence entre deux phrases.",
  },
];

function TiltCard({
  n,
  title,
  body,
  i,
}: {
  n: string;
  title: string;
  body: string;
  i: number;
}) {
  const ref = useRef<HTMLElement>(null);
  const onMove = (e: MouseEvent) => {
    const el = ref.current;
    if (!el || window.matchMedia("(pointer: coarse)").matches) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(700px) rotateY(${px * 7}deg) rotateX(${-py * 7}deg) translateY(-2px)`;
  };
  const onLeave = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  return (
    <motion.article
      ref={ref}
      data-tilt
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 + i * 0.08, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className="rounded-[var(--radius-md)] border border-white/10 bg-[rgba(13,16,18,0.55)] p-6 backdrop-blur-md transition-[border-color,background] duration-400 hover:border-[var(--color-foil)] hover:bg-[rgba(20,24,26,0.75)]"
    >
      <span className="mb-4 block text-[0.7rem] tracking-[0.18em] text-[var(--color-foil)]">{n}</span>
      <h3 className="font-brand mb-2 text-[1.35rem] font-bold tracking-[-0.03em]">{title}</h3>
      <p className="text-[1rem] leading-[1.65] text-[var(--color-ink-dim)]">{body}</p>
    </motion.article>
  );
}

export function ManifestPage() {
  const navigate = useNavigate();
  return (
    <div className="relative z-10 min-h-dvh px-[clamp(1.1rem,4vw,2.75rem)] pb-16">
      <header className="flex items-center justify-between gap-3 py-4">
        <div className="flex min-w-0 items-center gap-3">
          <BrandLogo heightClass="h-7 sm:h-8" />
          <Link
            to="/"
            className="hidden px-2 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase transition-colors hover:text-[var(--color-ink)] sm:inline"
          >
            Accueil
          </Link>
        </div>
        <MagneticButton className="!px-4 !py-3 !text-[0.7rem]" onClick={() => navigate("/atelier")}>
          Atelier
        </MagneticButton>
      </header>

      <div className="grid items-start gap-10 pt-4 md:grid-cols-[0.85fr_1.15fr] md:gap-16">
        <div className="md:sticky md:top-20">
          <motion.h2
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            className="font-mega text-[clamp(2.8rem,8vw,5rem)] leading-none font-semibold tracking-[-0.02em] italic"
          >
            Le manifeste
          </motion.h2>
          <p className="mt-5 max-w-[32ch] text-[1.08rem] leading-[1.65] text-[var(--color-ink-dim)]">
            AlfAhou n’est pas une coque d’API. C’est une maison.
          </p>
        </div>
        <div className="grid gap-4">
          {CARDS.map((c, i) => (
            <TiltCard key={c.n} {...c} i={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
