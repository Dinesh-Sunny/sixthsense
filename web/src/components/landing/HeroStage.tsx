"use client";

import { StatusPill } from "@/components/StatusPill";
import { useInView } from "@/components/landing/reveal";
import type { Incident } from "@/lib/api/types";
import { COPY, VERDICT, cameraLine, riskLabel, riskTone } from "@/lib/copy";
import { assetUrl, cn } from "@/lib/utils";

/** Original flat illustration of a generic red double-decker (no roundel, no operator, no livery text). */
function Bus({ cone }: { cone: boolean }) {
  return (
    <svg viewBox="0 0 330 120" className="h-full w-full overflow-visible" aria-hidden>
      {/* Camera cone from the front camera toward the road ahead */}
      <polygon
        points="214,52 330,30 330,104"
        fill="var(--on-sky)"
        className={cn("transition-opacity duration-700 ease-out", cone ? "animate-[pulse_1.4s_ease-out_0.7s_1] opacity-30" : "opacity-0")}
      />
      <g>
        <rect x="6" y="6" width="206" height="98" rx="14" fill="var(--illus-bus)" />
        <rect x="6" y="56" width="206" height="5" fill="var(--illus-bus-dark)" />
        {/* upper deck windows */}
        {[16, 56, 96, 136].map((x) => (
          <rect key={`u${x}`} x={x} y="16" width="34" height="28" rx="5" fill="var(--illus-glass)" />
        ))}
        <rect x="176" y="16" width="28" height="28" rx="6" fill="var(--illus-glass)" />
        {/* lower deck windows + door */}
        {[16, 56, 96].map((x) => (
          <rect key={`l${x}`} x={x} y="66" width="34" height="22" rx="4" fill="var(--illus-glass)" />
        ))}
        <rect x="136" y="66" width="26" height="34" rx="3" fill="var(--illus-glass)" opacity="0.85" />
        <rect x="170" y="66" width="34" height="26" rx="5" fill="var(--illus-glass)" />
        {/* camera */}
        <rect x="206" y="48" width="9" height="8" rx="2" fill="var(--illus-tyre)" />
        {/* wheels */}
        {[46, 172].map((cx) => (
          <g key={cx}>
            <circle cx={cx} cy="104" r="13" fill="var(--illus-tyre)" />
            <circle cx={cx} cy="104" r="5" fill="var(--illus-glass)" />
          </g>
        ))}
      </g>
    </svg>
  );
}

/**
 * Hero stage: the bus drives along the top edge of a real street frame, its camera cone points at the
 * road and the forecast card (riskiest real moment) pops beside it. Reduced motion: final state.
 */
export function HeroStage({ top, frame }: { top: Incident | undefined; frame: { src: string; alt: string } }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.1);
  return (
    <div ref={ref} className="relative mt-16 w-full max-w-[1120px] md:mt-[76px]">
      <div
        className={cn(
          "absolute -top-[52px] left-4 z-[2] h-[64px] w-[176px] transition-[opacity,transform] duration-[700ms] ease-out md:-top-[66px] md:left-[6%] md:h-[80px] md:w-[220px]",
          inView ? "translate-x-0 opacity-100" : "-translate-x-10 opacity-0",
        )}
      >
        <Bus cone={inView} />
      </div>
      <div className="aspect-[16/9] overflow-hidden rounded-xl bg-surface-sunk shadow-float md:aspect-[16/8]">
        <img src={assetUrl(frame.src)} alt={frame.alt} className="block size-full object-cover" />
      </div>
      {top && (
        <div
          className={cn(
            "glass relative mx-auto -mt-10 flex w-[calc(100%-24px)] max-w-[380px] flex-col gap-2.5 rounded-panel bg-glass-strong p-5 shadow-float transition-[opacity,transform] duration-[600ms] ease-out md:absolute md:top-8 md:right-10 md:mt-0 md:w-[380px]",
            inView ? "translate-y-0 scale-100 opacity-100" : "translate-y-2 scale-[0.97] opacity-0",
          )}
          style={{ transitionDelay: "650ms" }}
        >
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill tone={riskTone(top.risk)}>{riskLabel(top.risk)}</StatusPill>
            <span className="text-data text-ink-muted">{cameraLine(top)}</span>
          </div>
          <div className="text-eye">{COPY.next}</div>
          <p className="font-serif text-[22px] leading-[1.2] text-balance md:text-2xl">{top.what_next}</p>
          <div className="flex items-center gap-3">
            <StatusPill tone={VERDICT[top.came_true].tone}>{VERDICT[top.came_true].label}</StatusPill>
            {top.came_true !== "unknown" && <span className="text-body-sm text-ink-muted">checked on the next clip</span>}
          </div>
        </div>
      )}
    </div>
  );
}
