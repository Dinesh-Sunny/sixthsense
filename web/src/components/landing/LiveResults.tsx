"use client";

import { ScoreBar } from "@/components/landing/ScoreBar";
import { Reveal, rise, stagger, useInView } from "@/components/landing/reveal";
import type { Incident, ModeMetrics } from "@/lib/api/types";
import { MODE_INFO } from "@/lib/copy";
import { hazardOf } from "@/lib/incident";
import { cn } from "@/lib/utils";

const MAX_BOXES = 30;
const card = "lift flex flex-col gap-3 rounded-xl bg-surface p-7 shadow-float";

/** One box per clip watched; the ruled-out ones get crossed and fade (scaled when there are many). */
function RuledOutBoxes({ candidates, ruledOut }: { candidates: number; ruledOut: number }) {
  const [ref, inView] = useInView<HTMLDivElement>(0.5);
  const per = Math.max(1, Math.ceil(candidates / MAX_BOXES));
  const total = Math.ceil(candidates / per);
  const crossed = Math.round(ruledOut / per);
  return (
    <div className="flex flex-col gap-2">
      <div ref={ref} className="flex flex-wrap gap-1" aria-hidden>
        {Array.from({ length: total }, (_, n) => {
          const out = n < crossed;
          return (
            <span
              key={n}
              className={cn(
                "relative size-4 rounded-[3px] border border-ink-muted transition-opacity duration-500 ease-out",
                out && inView ? "opacity-30" : "opacity-100",
              )}
              style={{ transitionDelay: `${n * 60}ms` }}
            >
              {out && (
                <svg viewBox="0 0 16 16" className="absolute inset-0 size-full">
                  <path
                    d="M3 3l10 10M13 3L3 13"
                    stroke="var(--risk-high)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    pathLength={1}
                    strokeDasharray="1"
                    style={{
                      strokeDashoffset: inView ? 0 : 1,
                      transition: "stroke-dashoffset 400ms ease-out",
                      transitionDelay: `${n * 60}ms`,
                    }}
                  />
                </svg>
              )}
            </span>
          );
        })}
      </div>
      {per > 1 && <span className="text-data text-ink-muted">One box ≈ {per} clips</span>}
    </div>
  );
}

function HazardChips({ incidents }: { incidents: Incident[] }) {
  const counts = new Map<string, number>();
  for (const i of incidents) counts.set(hazardOf(i), (counts.get(hazardOf(i)) ?? 0) + 1);
  const chips = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  if (chips.length === 0) return <p className="text-body-sm text-ink-muted">No hazards in this run yet.</p>;
  return (
    <Reveal>
      <ul className="flex flex-wrap gap-1.5">
        {chips.map(([hazard, n], k) => (
          <li
            key={hazard}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border border-hairline bg-surface-sunk px-2.5 py-1 text-xs font-medium text-ink",
              "scale-90 opacity-0 transition-[opacity,transform] duration-[450ms] ease-out group-data-[in=true]/rv:scale-100 group-data-[in=true]/rv:opacity-100",
            )}
            style={stagger(k, 90)}
          >
            {hazard}
            <span className="font-mono text-ink-muted">{n}</span>
          </li>
        ))}
      </ul>
    </Reveal>
  );
}

/** Three live cards from the latest bus run (city until the bus run exists): score, ruled out, hazards. */
export function LiveResults({ metrics, incidents, actions }: { metrics: ModeMetrics; incidents: Incident[]; actions?: React.ReactNode }) {
  const runName = metrics.mode === "bus" ? MODE_INFO.bus.name : `${MODE_INFO[metrics.mode].name} run`;
  return (
    <section className="mx-auto max-w-[1200px] px-4 py-12 md:px-10 md:py-16 lg:px-[80px]" aria-labelledby="results-h">
      <Reveal className="mb-8">
        <h2 id="results-h" className={cn("font-serif text-[36px] leading-[1.08] md:text-[44px]", rise)}>
          Live results
        </h2>
        <p className={cn("mt-2 text-body-sm text-ink-muted", rise)} style={stagger(1)}>
          {metrics.mode === "bus"
            ? "From the latest bus safety run, read live from the app."
            : `From the latest ${runName.toLowerCase()} (the bus safety run hasn't run yet), read live from the app.`}
        </p>
      </Reveal>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className={card}>
          <div className="text-eye">{runName}</div>
          <div className="font-serif text-[30px] leading-none">
            {metrics.checked > 0 ? `${metrics.came_true_yes} of ${metrics.checked}` : "Not checked yet"}
          </div>
          <p className="text-body-sm text-ink-muted">forecasts came true when we checked the next clip</p>
          {metrics.checked > 0 && <ScoreBar metrics={metrics} />}
        </div>
        <div className={card}>
          <div className="text-eye">False alarms ruled out</div>
          <div className="font-serif text-[30px] leading-none">{metrics.ruled_out}</div>
          <p className="text-body-sm text-ink-muted">
            before anyone saw them, out of {metrics.candidates} clips watched
          </p>
          <RuledOutBoxes candidates={metrics.candidates} ruledOut={metrics.ruled_out} />
        </div>
        <div className={card}>
          <div className="text-eye">Hazards found</div>
          <div className="font-serif text-[30px] leading-none">{new Set(incidents.map((i) => hazardOf(i))).size}</div>
          <p className="text-body-sm text-ink-muted">kinds of close call in this run</p>
          <HazardChips incidents={incidents} />
        </div>
      </div>
      {actions && <div className="mt-8 flex flex-wrap items-center gap-3">{actions}</div>}
    </section>
  );
}
