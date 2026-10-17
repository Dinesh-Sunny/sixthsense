"use client";

import { GapChart } from "@/components/GapChart";
import { useInView } from "@/components/landing/reveal";
import { useTween } from "@/components/landing/useTween";
import type { GapPoint } from "@/lib/api/types";
import { gapSummary } from "@/lib/copy";
import { assetUrl, cn } from "@/lib/utils";

/**
 * Two boxes on a real frame close in while the gap counter ticks down. The counter and chart use the
 * real gap series of the riskiest live moment; without one, only the frame and boxes show (no numbers).
 */
export function GapCreative({ series, frame }: { series: GapPoint[] | undefined; frame: { src: string; alt: string } }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.4);
  const t = useTween(inView, 1600, 200);
  const g = gapSummary(series);
  const value = g ? g.from + (g.to - g.from) * t : null;

  return (
    <div ref={ref} className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-sm">
        <img src={assetUrl(frame.src)} alt={frame.alt} className="block aspect-video w-full object-cover" />
        {/* Illustration boxes: they move together as the counter falls. */}
        <span
          aria-hidden
          className="absolute top-[42%] left-[18%] h-[26%] w-[16%] rounded-[3px] border-2 border-on-sky shadow-[0_0_0_1px_rgb(0_0_0/0.25)]"
          style={{ transform: `translateX(${t * 70}%)` }}
        />
        <span
          aria-hidden
          className={cn(
            "absolute top-[46%] right-[18%] h-[24%] w-[18%] rounded-[3px] border-2 shadow-[0_0_0_1px_rgb(0_0_0/0.25)] transition-colors duration-300",
            t > 0.85 ? "border-risk-high" : "border-on-sky",
          )}
          style={{ transform: `translateX(${-t * 70}%)` }}
        />
        {value !== null && (
          <span className="absolute bottom-2 left-2 rounded-full bg-scrim px-2.5 py-1 font-mono text-xs text-on-sky tabular-nums">
            gap {value.toFixed(1)} cl
          </span>
        )}
      </div>
      {g && series && (
        <div
          className={cn(
            "[&_polyline]:transition-[stroke-dashoffset] [&_polyline]:duration-[1400ms] [&_polyline]:ease-out [&_polyline]:[stroke-dasharray:1400]",
            inView ? "[&_polyline]:[stroke-dashoffset:0]" : "[&_polyline]:[stroke-dashoffset:1400]",
          )}
        >
          <GapChart series={series} />
        </div>
      )}
      <p className="text-data text-ink-muted">Boxes drawn for illustration on a real frame.</p>
    </div>
  );
}
