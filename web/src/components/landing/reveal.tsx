"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** True once the element has scrolled into view (once). Reduced motion: true straight away, final state, no motion. */
export function useInView<T extends Element>(threshold = 0.3) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return [ref, inView] as const;
}

/** Group wrapper: children using `rise` animate in when this scrolls into view. */
export function Reveal({ className, children }: { className?: string; children: React.ReactNode }) {
  const [ref, inView] = useInView<HTMLDivElement>();
  return (
    <div ref={ref} data-in={inView} className={cn("group/rv", className)}>
      {children}
    </div>
  );
}

/** Fade-up item inside <Reveal>; opacity + transform only, so no layout shift. */
export const rise =
  "opacity-0 translate-y-3 transition-[opacity,transform] duration-[600ms] ease-out group-data-[in=true]/rv:translate-y-0 group-data-[in=true]/rv:opacity-100";

/** Stagger step (ms) for the n-th item. */
export const stagger = (n: number, step = 100) => ({ transitionDelay: `${n * step}ms` });
