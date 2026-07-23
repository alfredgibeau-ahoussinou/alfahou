import { Outlet, useLocation } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import { FieldCanvas } from "./components/FieldCanvas";
import { Cursor } from "./components/Cursor";

export function AppShell() {
  const location = useLocation();

  return (
    <>
      <a
        href="/atelier#prompt"
        className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[400] focus:bg-[var(--color-ink)] focus:px-3 focus:py-2 focus:text-[var(--color-bg)]"
      >
        Aller à l’atelier
      </a>
      <FieldCanvas />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[1] bg-[radial-gradient(ellipse_75%_65%_at_58%_42%,transparent_22%,rgba(6,7,8,0.35)_72%,rgba(6,7,8,0.72)_100%),linear-gradient(180deg,rgba(6,7,8,0.15),transparent_18%,transparent_78%,rgba(6,7,8,0.7))]"
      />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-[2] animate-[grain-shift_8s_steps(8)_infinite] bg-[url('data:image/svg+xml,%3Csvg%20viewBox=%270%200%20256%20256%27%20xmlns=%27http://www.w3.org/2000/svg%27%3E%3Cfilter%20id=%27n%27%3E%3CfeTurbulence%20type=%27fractalNoise%27%20baseFrequency=%270.9%27%20numOctaves=%274%27%20stitchTiles=%27stitch%27/%3E%3C/filter%3E%3Crect%20width=%27100%25%27%20height=%27100%25%27%20filter=%27url(%23n)%27%20opacity=%270.55%27/%3E%3C/svg%3E')] bg-[length:180px] opacity-[0.14] mix-blend-overlay"
      />
      <Cursor />
      <div className="relative z-10 min-h-dvh">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </div>
    </>
  );
}
