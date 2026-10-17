// How an incident is named on screen: hazard type + London place, with one short secondary line.
// Every screen uses these so the long forecast sentence never repeats as a headline.
import { useQuery } from "@tanstack/react-query";
import { metricsOptions } from "@/lib/api/queries";
import type { Incident, Mode, Pairing } from "@/lib/api/types";

const FALLBACK_HAZARD = "Close call";

export function hazardOf(i: Pick<Incident, "type"> | undefined): string {
  const t = i?.type?.trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : FALLBACK_HAZARD;
}

/** "Route 254 near Stamford Hill Broadway" when the pairing knows the stop. */
export function placeOf(p: Pairing | undefined): string | null {
  if (!p) return null;
  return p.stop_name ? `Route ${p.route} near ${p.stop_name}` : `Route ${p.route}`;
}

export function incidentTitle(i: Incident | undefined, p?: Pairing): string {
  const place = placeOf(p);
  return place ? `${hazardOf(i)} · ${place}` : hazardOf(i);
}

/** One short line under a title: the fix (default) or what happened, with the other as fallback. */
export function shortLine(i: Incident | undefined, prefer: "fix" | "happened" = "fix"): string {
  const happened = i?.came_true_evidence || i?.what_happens || "";
  return prefer === "fix" ? i?.fix || happened : happened || i?.fix || "";
}

/**
 * Inside pages show the bus safety run; until it has run, they fall back to the city run.
 * Returns undefined while metrics load.
 */
export function useDataMode(): Mode | undefined {
  const metrics = useQuery(metricsOptions());
  if (metrics.isPending) return undefined;
  return metrics.data?.some((m) => m.mode === "bus" && m.candidates > 0) ? "bus" : "city";
}

export function inMode<T extends { mode: Mode }>(rows: T[] | undefined, mode: Mode | undefined): T[] {
  if (!rows) return [];
  if (!mode) return rows;
  return rows.filter((r) => r.mode === mode);
}
