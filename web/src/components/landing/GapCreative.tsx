"use client";

import { ClipFrame, type StaticFrame } from "@/components/landing/ClipFrame";
import { useInView } from "@/components/landing/reveal";
import { useTween } from "@/components/landing/useTween";
import type { Incident } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Real growth from the ego check's plain note, e.g. "a pedestrian ahead grew 1.8x in 1.2 s". */
function growthOf(note: string | undefined): { factor: number; seconds: number } | null {
  const m = note?.match(/(\d+(?:\.\d+)?)\s*x\s+in\s+(\d+(?:\.\d+)?)\s*s/i);
  if (!m) return null;
  return { factor: Number(m[1]), seconds: Number(m[2]) };
}

/**
 * "Closing on us": one box ahead grows toward the bottom of a real clip frame, the way a road user looks
 * as the bus closes in. The counter shows the real growth from the incident's check; without one, no numbers.
 */
export function GapCreative({ incident, fallback }: { incident: Incident | undefined; fallback: StaticFrame }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.4);
  const t = useTween(inView, 1600, 200);
  const g = growthOf(incident?.verify_note);
  const factor = g ? 1 + (g.factor - 1) * t : null;
  const scale = 0.55 + 0.7 * t;

  return (
    <div ref={ref} className="flex flex-col gap-3">
      <div className="relative aspect-video overflow-hidden rounded-sm">
        <ClipFrame incident={incident} fallback={fallback} />
        {/* Illustration box, anchored at the bottom centre lane zone, growing as it closes in. */}
        <span
          aria-hidden
          className={cn(
            "absolute bottom-[14%] left-1/2 h-[34%] w-[16%] origin-bottom rounded-[3px] border-2 shadow-[0_0_0_1px_rgb(0_0_0/0.25)] transition-colors duration-300",
            t > 0.8 ? "border-risk-high" : "border-on-sky",
          )}
          style={{ transform: `translateX(-50%) scale(${scale})` }}
        />
        {factor !== null && (
          <span className="absolute right-2 bottom-2 rounded-full bg-scrim px-2.5 py-1 font-mono text-xs text-on-sky tabular-nums">
            grew {factor.toFixed(1)}x in {g!.seconds.toFixed(1)} s
          </span>
        )}
      </div>
      {incident?.verify_note && g && <p className="text-body-sm text-ink">{incident.verify_note}</p>}
      <p className="text-data text-ink-muted">Box drawn for illustration on a real clip frame.</p>
    </div>
  );
}
