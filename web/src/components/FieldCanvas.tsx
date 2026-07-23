import { useEffect, useRef } from "react";

export function FieldCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const wide = window.matchMedia("(min-width: 1024px)").matches;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let raf = 0;
    const t0 = performance.now();
    const mouse = { x: 0.5, y: 0.45, tx: 0.5, ty: 0.45 };
    const N = reduced ? 28 : wide ? 110 : 72;
    const pts = Array.from({ length: N }, (_, i) => ({
      a: (i / N) * Math.PI * 2,
      r: 0.12 + Math.random() * 0.55,
      s: 0.15 + Math.random() * 0.55,
      p: Math.random() * Math.PI * 2,
    }));

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (now: number) => {
      const t = (now - t0) / 1000;
      mouse.x += (mouse.tx - mouse.x) * 0.06;
      mouse.y += (mouse.ty - mouse.y) * 0.06;
      ctx.clearRect(0, 0, w, h);

      // Sur grand écran, le champ respire à droite pour laisser le hero à gauche.
      const cx = wide ? 0.64 : 0.5;
      const cy = wide ? 0.46 : 0.45;
      const spreadX = wide ? 0.48 : 0.55;
      const spreadY = wide ? 0.4 : 0.42;

      const g = ctx.createRadialGradient(
        w * mouse.x,
        h * mouse.y,
        0,
        w * cx,
        h * cy,
        Math.max(w, h) * (wide ? 0.68 : 0.75),
      );
      g.addColorStop(0, "rgba(212,184,150,0.2)");
      g.addColorStop(0.32, "rgba(100,120,110,0.11)");
      g.addColorStop(1, "rgba(6,7,8,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      ctx.lineWidth = wide ? 1.15 : 1;
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const ang = p.a + t * p.s * 0.22;
        const rad = p.r + Math.sin(t * 0.4 + p.p) * 0.04;
        const x = w * (cx + Math.cos(ang) * rad * spreadX + (mouse.x - 0.5) * 0.08);
        const y = h * (0.48 + Math.sin(ang * 1.15) * rad * spreadY + (mouse.y - 0.5) * 0.08);
        const x2 = w * (cx + Math.cos(ang + 0.35) * rad * (spreadX * 0.9));
        const y2 = h * (0.48 + Math.sin(ang + 0.35) * rad * (spreadY * 0.9));

        ctx.strokeStyle = i % 3 === 0 ? "rgba(212,184,150,0.28)" : "rgba(244,240,232,0.1)";
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.quadraticCurveTo((x + x2) / 2 + Math.sin(t + i) * 18, (y + y2) / 2, x2, y2);
        ctx.stroke();

        ctx.fillStyle = i % 5 === 0 ? "rgba(212,184,150,0.65)" : "rgba(244,240,232,0.24)";
        ctx.beginPath();
        ctx.arc(x, y, i % 5 === 0 ? (wide ? 1.9 : 1.6) : wide ? 1.1 : 0.9, 0, Math.PI * 2);
        ctx.fill();
      }

      if (!reduced) raf = requestAnimationFrame(draw);
    };

    const onMove = (e: PointerEvent) => {
      mouse.tx = e.clientX / Math.max(w, 1);
      mouse.ty = e.clientY / Math.max(h, 1);
    };
    const onVis = () => {
      if (document.hidden) cancelAnimationFrame(raf);
      else if (!reduced) raf = requestAnimationFrame(draw);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVis);
    resize();
    if (reduced) draw(performance.now());
    else raf = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="pointer-events-none fixed inset-0 z-0 h-full w-full"
      aria-hidden
    />
  );
}
