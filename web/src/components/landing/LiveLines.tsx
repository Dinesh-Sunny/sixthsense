"use client";

import { useQueries } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useInView, prefersReducedMotion } from "@/components/landing/reveal";
import { useTween } from "@/components/landing/useTween";
import { routeOptions } from "@/lib/api/queries";
import { cn } from "@/lib/utils";

const ROUTES = ["18", "25", "73"];
const W = 320;
const H = 200;
const PAD = 14;
// Fallback shapes if the route API is unavailable (illustrative lines, no data implied).
const FALLBACK: [number, number][][] = [
  [[20, 150], [90, 120], [160, 110], [230, 70], [300, 40]],
  [[30, 40], [110, 70], [170, 100], [250, 130], [300, 170]],
  [[60, 190], [100, 140], [150, 90], [190, 50], [210, 15]],
];

type Pt = [number, number];

function project(lines: Pt[][]): Pt[][] {
  const all = lines.flat();
  const lons = all.map((p) => p[0]);
  const lats = all.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats)];
  // Rough equirectangular at London's latitude, fitted into the box.
  const kx = Math.cos((51.5 * Math.PI) / 180);
  const s = Math.min((W - 2 * PAD) / ((x1 - x0) * kx || 1), (H - 2 * PAD) / (y1 - y0 || 1));
  return lines.map((l) => l.map(([lon, lat]) => [PAD + (lon - x0) * kx * s, H - PAD - (lat - y0) * s] as Pt));
}

function pointAt(line: Pt[], f: number): Pt {
  const seg = line.slice(1).map((p, i) => Math.hypot(p[0] - line[i][0], p[1] - line[i][1]));
  let d = seg.reduce((a, b) => a + b, 0) * f;
  for (let i = 0; i < seg.length; i++) {
    if (d <= seg[i]) {
      const r = seg[i] ? d / seg[i] : 0;
      return [line[i][0] + (line[i + 1][0] - line[i][0]) * r, line[i][1] + (line[i + 1][1] - line[i][1]) * r];
    }
    d -= seg[i];
  }
  return line[line.length - 1];
}

/** Mini London: real route lines (TfL route sequences) with bus dots gliding; one needs a look, then is checked. */
export function LiveLines() {
  const [ref, inView] = useInView<HTMLDivElement>(0.4);
  const t = useTween(inView, 2400);
  const [phase, setPhase] = useState<"glide" | "look" | "checked">("glide");
  const routes = useQueries({ queries: ROUTES.map((id) => routeOptions(id)) });
  const real = routes.every((r) => r.data && r.data.directions.some((d) => d.coords.length > 1));

  const lines = useMemo<Pt[][]>(() => {
    if (!real) return FALLBACK;
    const raw = routes.map((r) => {
      const d = r.data!.directions.find((x) => x.coords.length > 1)!;
      return d.coords as Pt[];
    });
    return project(raw);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recompute when the data arrives
  }, [real, routes.map((r) => r.dataUpdatedAt).join()]);

  useEffect(() => {
    if (t < 1) return;
    if (prefersReducedMotion()) {
      setPhase("checked");
      return;
    }
    setPhase("look");
    const timer = setTimeout(() => setPhase("checked"), 1600);
    return () => clearTimeout(timer);
  }, [t]);

  const starts = [0.08, 0.15, 0.1];
  const spans = [0.55, 0.6, 0.5];
  const dots = lines.map((l, i) => pointAt(l, starts[i] + spans[i] * t));
  const watchedColour = phase === "look" ? "var(--risk-high)" : phase === "checked" ? "var(--truth)" : "var(--bus)";

  return (
    <div ref={ref} className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={real ? "Routes 18, 25 and 73 with buses moving along them" : "Three bus routes with buses moving along them"}>
        <rect width={W} height={H} rx="12" fill="var(--surface-sunk)" />
        {lines.map((l, i) => (
          <polyline
            key={i}
            points={l.map((p) => p.join(",")).join(" ")}
            fill="none"
            stroke="var(--ink)"
            strokeOpacity="0.28"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
        {real &&
          lines.map((l, i) => (
            <text key={`t${i}`} x={l[0][0] + 4} y={l[0][1] - 6} fontSize="10" fill="var(--ink-muted)" className="font-mono">
              {ROUTES[i]}
            </text>
          ))}
        {dots.map(([x, y], i) => (
          <g key={`d${i}`}>
            {i === 0 && phase === "look" && (
              <circle cx={x} cy={y} r="6" fill="var(--risk-high)" className="origin-center animate-ping [transform-box:fill-box]" opacity="0.5" />
            )}
            <circle
              cx={x}
              cy={y}
              r={i === 0 ? 5 : 4}
              fill={i === 0 ? watchedColour : "var(--bus)"}
              stroke="var(--surface)"
              strokeWidth="1.5"
              className="transition-[fill] duration-500"
            />
          </g>
        ))}
      </svg>
      <p className={cn("text-data text-ink-muted transition-opacity duration-500", phase === "glide" ? "opacity-0" : "opacity-100")}>
        {phase === "look" ? "One bus needs a look." : "Checked against the next clip."}
      </p>
    </div>
  );
}
