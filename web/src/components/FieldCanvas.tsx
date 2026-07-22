import { useEffect, useRef } from "react";

export function FieldCanvas() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w = 0;
    let h = 0;
    let dpr = 1;
    let raf = 0;
    const t0 = performance.now();
    const mouse = { x: 0.5, y: 0.45, tx: 0.5, ty: 0.45 };
    const N = reduced ? 28 : 72;
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

      const g = ctx.createRadialGradient(
        w * mouse.x,
        h * mouse.y,
        0,
        w * 0.5,
        h * 0.45,
        Math.max(w, h) * 0.75,
      );
      g.addColorStop(0, "rgba(212,184,150,0.14)");
      g.addColorStop(0.35, "rgba(100,120,110,0.08)");
      g.addColorStop(1, "rgba(6,7,8,0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      ctx.lineWidth = 1;
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const ang = p.a + t * p.s * 0.22;
        const rad = p.r + Math.sin(t * 0.4 + p.p) * 0.04;
        const x = w * (0.5 + Math.cos(ang) * rad * 0.55 + (mouse.x - 0.5) * 0.08);
        const y = h * (0.48 + Math.sin(ang * 1.15) * rad * 0.42 + (mouse.y - 0.5) * 0.08);
        const x2 = w * (0.5 + Math.cos(ang + 0.35) * rad * 0.5);
        const y2 = h * (0.48 + Math.sin(ang + 0.35) * rad * 0.38);

        ctx.strokeStyle = i % 3 === 0 ? "rgba(212,184,150,0.22)" : "rgba(244,240,232,0.08)";
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.quadraticCurveTo((x + x2) / 2 + Math.sin(t + i) * 18, (y + y2) / 2, x2, y2);
        ctx.stroke();

        ctx.fillStyle = i % 5 === 0 ? "rgba(212,184,150,0.55)" : "rgba(244,240,232,0.2)";
        ctx.beginPath();
        ctx.arc(x, y, i % 5 === 0 ? 1.6 : 0.9, 0, Math.PI * 2);
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
