"use client";

import type { ModeMetrics } from "@/lib/api/types";
import { useInView } from "@/components/landing/reveal";
import { cn } from "@/lib/utils";

const MAX = 12;

/** Live "N of M came true" squares that fill one by one when seen (real /api/metrics numbers). */
export function ScoreBar({ metrics }: { metrics: ModeMetrics }) {
  const [ref, inView] = useInView<HTMLSpanElement>(0.6);
  const { came_true_yes: yes, came_true_partly: partly, checked } = metrics;
  const squares = Array.from({ length: Math.min(checked, MAX) }, (_, n) =>
    n < yes ? "yes" : n < yes + partly ? "partly" : "no",
  );
  return (
    <span ref={ref} className="flex gap-[3px]" aria-hidden>
      {squares.map((s, n) => (
        <i
          key={n}
          className="relative h-[22px] w-2.5 overflow-hidden rounded-[3px] bg-surface-sunk shadow-[inset_0_0_0_1px_var(--hairline)]"
        >
          <span
            className={cn(
              "absolute inset-0 origin-bottom scale-y-0 transition-transform duration-[500ms] ease-out",
              inView && "scale-y-100",
              s === "yes" && "bg-truth",
              s === "partly" && "bg-risk-mid",
              s === "no" && "bg-hairline",
            )}
            style={{ transitionDelay: `${n * 90}ms` }}
          />
        </i>
      ))}
    </span>
  );
}
