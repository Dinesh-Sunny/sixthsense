"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { cn } from "@/lib/utils";

const REDUCE = "(prefers-reduced-motion: reduce)";

function subscribeReduce(cb: () => void) {
  const mq = window.matchMedia(REDUCE);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

/** Live prefers-reduced-motion (false during the static prerender). */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReduce,
    () => window.matchMedia(REDUCE).matches,
    () => false,
  );
}

/** True once the element has scrolled into view (once). Reduced motion: true straight away, final state, no motion. */
export function useInView<T extends Element>(threshold = 0.3) {
  const ref = useRef<T>(null);
  const [seen, setSeen] = useState(false);
  const reduced = useReducedMotion();
  useEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setSeen(true);
          io.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold, reduced]);
  // Reduced motion: final state at once (the global CSS rule also removes transition time).
  return [ref, seen || reduced] as const;
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
