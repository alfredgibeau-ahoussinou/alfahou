import { useRef, type ReactNode, type MouseEvent } from "react";
import { motion } from "motion/react";
import clsx from "clsx";

type Props = {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  type?: "button" | "submit";
};

export function MagneticButton({ children, className, onClick, type = "button" }: Props) {
  const ref = useRef<HTMLButtonElement>(null);

  const onMove = (e: MouseEvent) => {
    const el = ref.current;
    if (!el || window.matchMedia("(pointer: coarse)").matches) return;
    const r = el.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    el.style.transform = `translate(${dx * 6}px, ${dy * 5}px)`;
  };

  const onLeave = () => {
    if (ref.current) ref.current.style.transform = "";
  };

  return (
    <motion.button
      ref={ref}
      type={type}
      data-magnetic
      onClick={onClick}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        "group relative overflow-hidden rounded-[var(--radius-md)] border border-white/15 bg-white/[0.04] px-6 py-4",
        "text-[0.8rem] font-medium tracking-[0.1em] text-[var(--color-ink)] uppercase",
        "transition-[border-color,background] duration-300 hover:border-[var(--color-foil)] hover:bg-[rgba(212,184,150,0.08)]",
        className,
      )}
    >
      <span className="relative z-10">{children}</span>
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 -translate-x-full bg-[linear-gradient(105deg,transparent_30%,rgba(244,240,232,0.12)_50%,transparent_70%)] transition-transform duration-[4500ms] group-hover:translate-x-full"
      />
    </motion.button>
  );
}
