import { queryOptions } from "@tanstack/react-query";
import { getJson, getReady, postJson } from "./client";
import type { Alert, AskIn, AskOut, Health, Incident, Mode, ModeMetrics, RunIn, RunStatus, Weather } from "./types";

const RUN_POLL_MS = 2_000;
const WEATHER_MS = 10 * 60_000;

export const queryKeys = {
  incidents: (mode: Mode) => ["incidents", mode] as const,
  incidentsAll: ["incidents"] as const,
  incident: (id: string) => ["incident", id] as const,
  metrics: ["metrics"] as const,
  run: ["run"] as const,
  alerts: ["alerts"] as const,
  weather: ["weather"] as const,
  ready: ["ready"] as const,
};

export const incidentsOptions = (mode: Mode) =>
  queryOptions({
    queryKey: queryKeys.incidents(mode),
    queryFn: ({ signal }) => getJson<Incident[]>("/incidents", { mode }, signal),
  });

export const incidentOptions = (id: string) =>
  queryOptions({
    queryKey: queryKeys.incident(id),
    queryFn: ({ signal }) => getJson<Incident>(`/incidents/${encodeURIComponent(id)}`, undefined, signal),
    enabled: id.length > 0,
  });

export const metricsOptions = () =>
  queryOptions({
    queryKey: queryKeys.metrics,
    queryFn: ({ signal }) => getJson<ModeMetrics[]>("/metrics", undefined, signal),
  });

export const runOptions = () =>
  queryOptions({
    queryKey: queryKeys.run,
    queryFn: ({ signal }) => getJson<RunStatus>("/runs/current", undefined, signal),
    refetchInterval: (q) => (q.state.data?.state === "running" ? RUN_POLL_MS : false),
    staleTime: 0,
  });

export const alertsOptions = () =>
  queryOptions({
    queryKey: queryKeys.alerts,
    queryFn: ({ signal }) => getJson<Alert[]>("/alerts", undefined, signal),
  });

export const weatherOptions = () =>
  queryOptions({
    queryKey: queryKeys.weather,
    queryFn: ({ signal }) => getJson<Weather>("/weather", undefined, signal),
    staleTime: WEATHER_MS,
    refetchInterval: WEATHER_MS,
    retry: 1,
  });

export const readyOptions = () =>
  queryOptions({
    queryKey: queryKeys.ready,
    queryFn: ({ signal }) => getReady<Health>(signal),
    staleTime: 60_000,
    retry: false,
  });

export const startRun = (body: RunIn) => postJson<RunStatus>("/runs", body);
export const askFootage = (body: AskIn) => postJson<AskOut>("/ask", body);
export const sendAlert = (incidentId: string) => postJson<Alert>("/alerts", { incident_id: incidentId });
