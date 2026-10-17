"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "@/components/landing/reveal";

/** 0 -> 1 over `ms` with ease-out once `start` is true; reduced motion jumps straight to 1. */
export function useTween(start: boolean, ms: number, delay = 0): number {
  const [t, setT] = useState(0);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (!start || reduced) return;
    let raf = 0;
    let t0 = 0;
    const timer = setTimeout(() => {
      const step = (now: number) => {
        if (!t0) t0 = now;
        const p = Math.min(1, (now - t0) / ms);
        setT(1 - Math.pow(1 - p, 3));
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    }, delay);
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(raf);
    };
  }, [start, ms, delay, reduced]);
  return reduced ? 1 : t;
}
