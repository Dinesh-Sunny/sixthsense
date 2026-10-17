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

export type CameraView = "front" | "nearside";
export const VIEW_MODES: readonly Mode[] = ["bus_front", "bus_nearside"];

export const VIEW_LABEL: Record<CameraView, string> = { front: "Front camera", nearside: "Nearside camera" };
export const STAND_IN_NOTE = "Stand-in footage: a car dashcam and a bike camera, not a London bus.";

/** The bus camera view of an incident: the backend's camera_view, else derived from its mode. */
export function viewOf(i: { mode: Mode } | undefined): CameraView | null {
  if (!i) return null;
  const v = (i as { camera_view?: unknown }).camera_view;
  if (v === "front" || v === "nearside") return v;
  if (i.mode === "bus_front") return "front";
  if (i.mode === "bus_nearside") return "nearside";
  return null;
}

/**
 * Modes every inside page shows: the bus front + nearside runs; until they exist, the bus run, then the city run.
 * Undefined while metrics load.
 */
export function useDataModes(): Mode[] | undefined {
  const metrics = useQuery(metricsOptions());
  if (metrics.isPending) return undefined;
  const ran = new Set((metrics.data ?? []).filter((m) => m.candidates > 0).map((m) => m.mode));
  const views = VIEW_MODES.filter((m) => ran.has(m));
  if (views.length > 0) return views;
  return ran.has("bus") ? ["bus"] : ["city"];
}

export function inModes<T extends { mode: Mode }>(rows: T[] | undefined, modes: Mode[] | undefined): T[] {
  if (!rows) return [];
  if (!modes) return rows;
  return rows.filter((r) => modes.includes(r.mode));
}
