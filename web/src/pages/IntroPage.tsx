import { Link, useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { MagneticButton } from "../components/MagneticButton";
import { BrandLogo } from "../components/BrandLogo";

export function IntroPage() {
  const navigate = useNavigate();
  return (
    <div className="relative z-10 grid min-h-dvh grid-rows-[auto_1fr_auto]">
      <header className="flex items-center justify-between px-[clamp(1.1rem,4vw,2.75rem)] py-4">
        <BrandLogo heightClass="h-8 sm:h-9" />
        <nav className="flex gap-1">
          <Link
            to="/manifeste"
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase transition-colors hover:text-[var(--color-ink)]"
          >
            Manifeste
          </Link>
          <Link
            to="/atelier"
            className="px-3 py-2.5 text-[0.75rem] tracking-[0.12em] text-[var(--color-ink-dim)] uppercase transition-colors hover:text-[var(--color-ink)]"
          >
            Atelier
          </Link>
        </nav>
      </header>

      <main className="flex flex-col justify-center px-[clamp(1.1rem,4vw,2.75rem)] py-8">
        <motion.p
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mb-5 text-[0.72rem] tracking-[0.28em] text-[var(--color-ink-dim)] uppercase"
        >
          Maison multimédia
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
          className="font-mega text-foil-flow text-[clamp(4.5rem,18vw,11rem)] leading-[0.88] font-bold tracking-[-0.03em] italic"
        >
          AlfAhou
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="mt-7 max-w-[38ch] text-[clamp(1.08rem,2.4vw,1.28rem)] leading-[1.65] text-[var(--color-ink-dim)]"
        >
          Une intelligence qui écrit, illustre, filme et compose — conçue comme un objet, pas comme
          un chat.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="mt-10 flex flex-wrap items-center gap-4"
        >
          <MagneticButton onClick={() => navigate("/atelier")}>Entrer dans l’atelier</MagneticButton>
          <button
            type="button"
            onClick={() => navigate("/manifeste")}
            className="px-3 py-3 text-[0.85rem] text-[var(--color-mute)] underline decoration-white/20 underline-offset-[5px] transition-colors hover:text-[var(--color-ink)] hover:decoration-[var(--color-foil)]"
          >
            Lire le manifeste
          </button>
        </motion.div>
      </main>

      <footer className="overflow-hidden border-t border-white/10 pb-[calc(1rem+env(safe-area-inset-bottom))]">
        <div className="overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_8%,#000_92%,transparent)]">
          <div className="flex w-max animate-[ticker_28s_linear_infinite] gap-5 py-4 text-[0.72rem] tracking-[0.2em] text-[var(--color-mute)] uppercase">
            {Array.from({ length: 2 }).map((_, i) => (
              <span key={i} className="flex gap-5">
                <span>Texte</span>
                <span>·</span>
                <span>Image</span>
                <span>·</span>
                <span>Vidéo</span>
                <span>·</span>
                <span>PDF</span>
                <span>·</span>
                <span>FR</span>
                <span>·</span>
                <span>EN</span>
                <span>·</span>
              </span>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}
