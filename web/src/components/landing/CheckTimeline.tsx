"use client";

import { useInView } from "@/components/landing/reveal";
import { cn } from "@/lib/utils";

// Illustration of how one moment moves through the agent; it shows steps, not numbers.
const STEPS = ["Spotted", "Driver nudged", "Checked the next clip", "Came true", "Report filed"];

export function CheckTimeline() {
  const [ref, inView] = useInView<HTMLOListElement>(0.5);
  return (
    <ol ref={ref} className="relative flex flex-col gap-3" aria-label="How one moment moves through SixthSense">
      <span aria-hidden className="absolute top-2 bottom-2 left-[7px] w-px bg-hairline" />
      <span
        aria-hidden
        className={cn(
          "absolute top-2 left-[7px] w-px origin-top bg-truth transition-transform duration-[700ms] ease-out",
          inView ? "scale-y-100" : "scale-y-0",
        )}
        style={{ bottom: "0.5rem", transitionDuration: `${STEPS.length * 110 + 300}ms` }}
      />
      {STEPS.map((s, n) => (
        <li
          key={s}
          className={cn(
            "relative flex items-center gap-3 text-body-sm transition-[opacity,transform] duration-[500ms] ease-out",
            inView ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-40",
          )}
          style={{ transitionDelay: `${n * 110}ms` }}
        >
          <span
            aria-hidden
            className={cn(
              "relative z-[1] grid size-[15px] place-items-center rounded-full border transition-colors duration-[400ms] ease-out",
              inView ? "border-truth bg-truth" : "border-ink-muted bg-surface",
            )}
            style={{ transitionDelay: `${n * 110 + 150}ms` }}
          >
            <svg viewBox="0 0 10 10" className="size-2">
              <path d="M2 5.2l2 2 4-4.4" fill="none" stroke="var(--surface)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          {s}
        </li>
      ))}
    </ol>
  );
}
