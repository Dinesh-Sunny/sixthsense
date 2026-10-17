"use client";

import { useInView } from "@/components/landing/reveal";
import { cn } from "@/lib/utils";

// Illustrations for the audience cards: labels from the hazard set and pill names only, no numbers or stats.
const ROWS = [
  { hazard: "Cyclist on the nearside", pill: "Came true", tone: "text-truth" },
  { hazard: "Pedestrian stepping out", pill: "To review", tone: "text-slate" },
  { hazard: "Vehicle cutting in", pill: "Came true", tone: "text-truth" },
];

/** Bus safety teams: a small stack of report rows sliding in. */
export function ReportStack() {
  const [ref, inView] = useInView<HTMLUListElement>(0.4);
  return (
    <ul ref={ref} className="mt-2 flex h-[108px] flex-col justify-center gap-1.5" aria-hidden>
      {ROWS.map((r, n) => (
        <li
          key={r.hazard}
          className={cn(
            "flex items-center gap-2 rounded-md border border-hairline bg-surface px-2.5 py-1.5 transition-[opacity,transform] duration-[550ms] ease-out",
            inView ? "translate-x-0 opacity-100" : "translate-x-3 opacity-0",
          )}
          style={{ transitionDelay: `${n * 110}ms` }}
        >
          <span className="truncate rounded-full bg-surface-sunk px-2 py-0.5 text-[11px] font-medium text-ink">{r.hazard}</span>
          <span className="flex-1" />
          <span className={cn("inline-flex items-center gap-1 rounded-full border border-current px-2 py-0.5 text-[11px] font-medium", r.tone)}>
            <span className="size-1.5 rounded-full bg-current" />
            {r.pill}
          </span>
        </li>
      ))}
    </ul>
  );
}

const BUSES = [
  { n: 1, x: 62, y: 38, tint: "var(--risk-high)" },
  { n: 2, x: 30, y: 64, tint: "var(--risk-mid)" },
  { n: 3, x: 80, y: 70, tint: "var(--truth)" },
];

/** Control rooms: a muted map tile; numbered buses appear in order and #1 pulses once. */
export function MapTile() {
  const [ref, inView] = useInView<HTMLDivElement>(0.4);
  return (
    <div ref={ref} className="relative mt-2 h-[108px] overflow-hidden rounded-md bg-surface-sunk" aria-hidden>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 size-full">
        <path d="M0 30 L100 46 M0 72 L100 58 M24 0 L36 100 M70 0 L58 100" stroke="var(--surface)" strokeWidth="3" fill="none" />
        <path d="M8 90 Q40 40 92 22" stroke="var(--ink)" strokeOpacity="0.25" strokeWidth="1.2" fill="none" />
      </svg>
      {BUSES.map((b, i) => (
        <span
          key={b.n}
          className={cn(
            "absolute -translate-x-1/2 -translate-y-1/2 transition-[opacity,scale] duration-500 ease-out",
            inView ? "scale-100 opacity-100" : "scale-75 opacity-0",
          )}
          style={{ left: `${b.x}%`, top: `${b.y}%`, transitionDelay: `${i * 180}ms` }}
        >
          {b.n === 1 && inView && (
            <span
              className="absolute inset-0 animate-[ping_1.2s_ease-out_0.7s_1_forwards] rounded-full opacity-50"
              style={{ background: b.tint }}
            />
          )}
          <span
            className="relative grid size-6 place-items-center rounded-full border-[1.5px] border-surface font-mono text-[11px] font-semibold text-on-sky shadow-float"
            style={{ background: b.tint }}
          >
            {b.n}
          </span>
        </span>
      ))}
    </div>
  );
}
