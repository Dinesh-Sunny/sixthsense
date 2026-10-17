// Mirror of backend/src/sixthsense/contracts.py. Field names must match exactly
// (no generator: openapi-typescript failed the library gate, see decisions).

export type Mode = "road" | "city" | "street";
export const MODES: readonly Mode[] = ["road", "city", "street"] as const;

export type CameTrue = "yes" | "partly" | "no" | "unknown";

export interface GapPoint {
  /** seconds from clip start */
  t: number;
  /** gap in car lengths */
  cl: number;
}

export interface Incident {
  id: string;
  mode: Mode;
  camera_id: string | null;
  source: string | null;
  original_video: string | null;
  start_s: number;
  end_s: number;
  query: string | null;
  similarity: number | null;
  description: string;
  verified: boolean;
  verify_score: number;
  verify_note: string;
  verify_by: string;
  type: string;
  what_happens: string;
  what_next: string;
  why: string;
  fix: string;
  risk: number;
  came_true: CameTrue;
  came_true_evidence: string;
  next_source: string | null;
  judged_by: string | null;
  /** true = Sample data, never live */
  fixture: boolean;
  gap_series: GapPoint[];
  run_id: string | null;
  trace_url: string | null;
}

export interface ModeMetrics {
  mode: Mode;
  run_id: string | null;
  candidates: number;
  ruled_out: number;
  verified: number;
  checked: number;
  came_true_yes: number;
  came_true_partly: number;
  /** yes / checked; shown as "N of M came true" */
  accuracy: number | null;
  generated_at: string;
  eval_url: string | null;
}

export type StepName = "find" | "rule_out" | "predict" | "check";
export type StepState = "pending" | "running" | "done" | "error";

export interface StepProgress {
  done: number;
  total: number;
  state: StepState;
}

export type RunState = "idle" | "running" | "done" | "error";

export type RunSteps = Record<StepName, StepProgress>;

export interface RunStatus {
  run_id: string | null;
  mode: Mode | null;
  limit: number;
  state: RunState;
  steps: RunSteps;
  started_at: string | null;
  finished_at: string | null;
  /** exception class only */
  error: string | null;
  runs_enabled: boolean;
  /** ISO time a new run may start */
  cooldown_until: string | null;
}

export interface RunIn {
  mode: Mode;
  limit: number;
}

export interface AskIn {
  question: string;
  original_video?: string | null;
}

/** Backend passes VSS evidence dicts through as-is; these are the keys the UI reads. */
export interface AskEvidence {
  [key: string]: unknown;
  text?: string;
  source?: string | null;
  camera_id?: string | null;
  start_s?: number | null;
  end_s?: number | null;
  incident_id?: string | null;
}

export interface AskOut {
  answer: string;
  evidence: AskEvidence[];
}

export interface AlertIn {
  incident_id: string;
}

export interface Alert {
  id: string;
  incident_id: string;
  camera_id: string | null;
  type: string;
  what_next: string;
  risk: number;
  start_s: number;
  sent_at: string;
  /** true when the Discord webhook accepted it */
  delivered: boolean;
}

export type Wx = "clear" | "cloudy" | "rain" | "night";

export interface Weather {
  city: string;
  temp_c: number | null;
  label: string;
  wx: Wx;
  source: "open-meteo" | "clock";
}

export type StoreState = "vast" | "json" | "degraded";

/** GET /healthz, GET /readyz (outside /api). */
export interface Health {
  ok: boolean;
  store: StoreState | null;
  vss: boolean | null;
}

// ---- v2: London buses (plan sixthsense-v2-buses.md) ----

export type Direction = "inbound" | "outbound";

export interface Vehicle {
  /** TfL vehicleId (a registration) */
  id: string;
  route: string;
  dir: Direction;
  towards: string;
  /** naptanId */
  next_stop: string;
  next_stop_name: string;
  eta_s: number;
  lon: number;
  lat: number;
  bearing: number | null;
  ts: string;
}

export interface FleetSnapshot {
  ts: string;
  vehicles: Vehicle[];
  routes: number;
  latency_ms: number;
  source: "tfl";
}

export interface RouteSummary {
  id: string;
  name: string;
}

export interface RouteStop {
  id: string;
  name: string;
  lon: number;
  lat: number;
}

export interface RouteDirection {
  dir: Direction;
  coords: [number, number][];
  stops: RouteStop[];
}

export interface RouteDetail {
  id: string;
  directions: RouteDirection[];
}

/** Stand-in pairing of a real incident (latest run per mode) to a live bus. */
export interface Pairing {
  incident_id: string;
  vehicle_id: string;
  route: string;
  risk: number;
  came_true: CameTrue;
  mode: Mode;
}

export interface MapConfig {
  mapbox_token: string | null;
}
