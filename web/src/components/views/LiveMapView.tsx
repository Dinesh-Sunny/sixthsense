"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import type { Route } from "next";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { ClipPlayer } from "@/components/ClipPlayer";
import { BusMap, type Layers, type Scene, type Theme } from "@/components/map/BusMap";
import { StatusPill } from "@/components/StatusPill";
import { WeatherPill } from "@/components/WeatherPill";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { useFleet } from "@/lib/api/fleet";
import {
  alertsOptions,
  allIncidentsOptions,
  mapConfigOptions,
  pairingsOptions,
  routeOptions,
  routesOptions,
  weatherOptions,
} from "@/lib/api/queries";
import type { Incident, Pairing, Vehicle } from "@/lib/api/types";
import { BUS_COPY, BUS_STATE, VERDICT, busState, etaText, riskLabel, type BusState } from "@/lib/copy";
import { cn } from "@/lib/utils";

const SCENES: { id: Scene; label: string }[] = [
  { id: "2d", label: "2D" },
  { id: "3d", label: "3D" },
  { id: "drone", label: "Drone" },
];
const THEMES: { id: Theme; label: string }[] = [
  { id: "light", label: "Light" },
  { id: "dark", label: "Dark" },
  { id: "satellite", label: "Satellite" },
  { id: "night", label: "Night" },
];

const panel = "glass rounded-panel shadow-float";

function Segmented<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { id: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="glass flex gap-0.5 rounded-full p-1 shadow-float">
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          role="radio"
          aria-checked={value === o.id}
          onClick={() => onChange(o.id)}
          className={cn(
            "h-7 rounded-full px-3 text-xs font-medium text-ink-muted transition-colors duration-150 hover:text-ink",
            value === o.id && "bg-surface text-ink shadow-[0_0_0_1px_var(--hairline)]",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Toggle({ on, label, onClick }: { on: boolean; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={cn(
        "glass h-9 rounded-full px-3.5 text-xs font-medium shadow-float transition-colors duration-150",
        on ? "bg-pill text-on-ink" : "text-ink-muted hover:text-ink",
      )}
    >
      {label}
    </button>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-hairline bg-surface px-3 py-2.5">
      <div className="text-eye">{label}</div>
      <div className="mt-1.5 font-mono text-lg leading-none font-medium tabular-nums">{value}</div>
    </div>
  );
}

function Clock() {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    const tick = () => setNow(new Date());
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);
  if (!now) return null;
  return (
    <span className="text-data text-ink">
      {now.toLocaleTimeString("en-GB", { timeZone: "Europe/London", hour: "2-digit", minute: "2-digit", second: "2-digit" })}
    </span>
  );
}

function BusDrawer({
  bus,
  pairing,
  incident,
  nudged,
  following,
  onFollow,
  onShowRoute,
  onClose,
}: {
  bus: Vehicle | undefined;
  pairing: Pairing | undefined;
  incident: Incident | undefined;
  nudged: boolean;
  following: boolean;
  onFollow: () => void;
  onShowRoute: () => void;
  onClose: () => void;
}) {
  const state = busState(pairing);
  const checked = pairing ? pairing.came_true !== "unknown" : false;
  const done = [Boolean(pairing), nudged, Boolean(pairing), checked, checked];
  return (
    <div className="flex flex-col gap-3">
      <button type="button" onClick={onClose} className="self-start text-data text-slate hover:underline">
        ← {BUS_COPY.needsLook}
      </button>
      {!bus ? (
        <p className="text-body-sm text-ink-muted">{BUS_COPY.busGone}</p>
      ) : (
        <>
          <div className="flex items-start gap-3">
            <div>
              <div className="font-serif text-[28px] leading-none">Route {bus.route}</div>
              <div className="mt-1 text-data text-ink-muted">{bus.id}</div>
            </div>
            <div className="flex-1" />
            <StatusPill tone={BUS_STATE[state].tone}>{BUS_STATE[state].label}</StatusPill>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-body-sm">
            <dt className="text-ink-muted">{BUS_COPY.towards}</dt>
            <dd>{bus.towards || "Not given"}</dd>
            <dt className="text-ink-muted">{BUS_COPY.nextStop}</dt>
            <dd>
              {bus.next_stop_name} · <span className="font-mono">{etaText(bus.eta_s)}</span>
            </dd>
          </dl>
        </>
      )}
      {pairing && incident && (
        <>
          <div className="overflow-hidden rounded-md bg-surface">
            <ClipPlayer
              source={incident.source}
              label="Stand-in clip for this bus"
              fallbackLabel={BUS_COPY.standIn}
              overlay={<StatusPill tone="sample">{BUS_COPY.standIn}</StatusPill>}
            />
          </div>
          <div className="text-eye">Next</div>
          <p className="font-serif text-xl leading-[1.2] text-balance">{incident.what_next}</p>
          <div className="flex flex-wrap gap-2">
            <StatusPill tone={riskTone(pairing.risk)}>{riskLabel(pairing.risk)}</StatusPill>
            <StatusPill tone={VERDICT[pairing.came_true].tone}>{VERDICT[pairing.came_true].label}</StatusPill>
          </div>
          <ol className="flex flex-col gap-1.5" aria-label="What the agents did">
            {BUS_COPY.timeline.map((step, n) => (
              <li key={step} className={cn("flex items-center gap-2 text-body-sm", !done[n] && "text-ink-muted")}>
                <span
                  aria-hidden
                  className={cn("size-2 rounded-full", done[n] ? "bg-truth" : "border border-ink-muted")}
                />
                {step}
                <span className="sr-only">{done[n] ? " (done)" : " (not yet)"}</span>
              </li>
            ))}
          </ol>
        </>
      )}
      <div className="flex flex-wrap gap-2 pt-1">
        {pairing && (
          <Button asChild size="sm">
            <Link href={{ pathname: "/incident", query: { id: pairing.incident_id } }}>{BUS_COPY.openReport}</Link>
          </Button>
        )}
        {bus && (
          <>
            <Button size="sm" variant="glass" onClick={onFollow} aria-pressed={following}>
              {following ? BUS_COPY.following : BUS_COPY.follow}
            </Button>
            <Button size="sm" variant="glass" onClick={onShowRoute}>
              {BUS_COPY.showRoute}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function riskTone(risk: number) {
  return risk >= 4 ? ("hi" as const) : risk === 3 ? ("mid" as const) : ("lo" as const);
}

export function LiveMapView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const { snapshot, link } = useFleet();
  const mapConfig = useQuery(mapConfigOptions());
  const routesList = useQuery(routesOptions());
  const pairings = useQuery(pairingsOptions());
  const incidents = useQuery(allIncidentsOptions());
  const alerts = useQuery(alertsOptions());
  const weather = useQuery(weatherOptions());

  const [chosenRoutes, setChosenRoutes] = useState<string[]>(() =>
    (params.get("route") ?? "").split(",").map((r) => r.trim()).filter(Boolean),
  );
  const [selectedId, setSelectedId] = useState<string | null>(() => params.get("bus"));
  const [followId, setFollowId] = useState<string | null>(() => params.get("bus"));
  const [query, setQuery] = useState("");
  const [scene, setScene] = useState<Scene>("2d");
  const [userTheme, setUserTheme] = useState<Theme | null>(null);
  const [layers, setLayers] = useState<Layers>({ traffic: false, cameras: true });
  const [mapFailed, setMapFailed] = useState(false);
  const theme: Theme = userTheme ?? (weather.data?.wx === "night" ? "night" : "light");

  // Keep the URL shareable: ?route=18,25&bus=LJ12ABC
  useEffect(() => {
    const q = new URLSearchParams();
    if (chosenRoutes.length) q.set("route", chosenRoutes.join(","));
    if (selectedId) q.set("bus", selectedId);
    const next = q.toString();
    if (next !== params.toString()) router.replace(`${pathname}${next ? `?${next}` : ""}` as Route, { scroll: false });
  }, [chosenRoutes, selectedId, params, pathname, router]);

  const vehicles = useMemo(() => snapshot.data?.vehicles ?? [], [snapshot.data]);
  const pairByBus = useMemo(() => new Map((pairings.data ?? []).map((p) => [p.vehicle_id, p])), [pairings.data]);
  const states = useMemo(() => {
    const m = new Map<string, BusState>();
    pairByBus.forEach((p, id) => m.set(id, busState(p)));
    return m;
  }, [pairByBus]);
  const incidentById = useMemo(() => new Map((incidents.data ?? []).map((i) => [i.id, i])), [incidents.data]);
  const shown = useMemo(
    () =>
      chosenRoutes.length === 0
        ? vehicles
        : vehicles.filter((v) => chosenRoutes.includes(v.route) || v.id === selectedId),
    [vehicles, chosenRoutes, selectedId],
  );
  const routeDetails = useQueries({ queries: chosenRoutes.map((id) => routeOptions(id)) })
    .map((q) => q.data)
    .filter((d) => d !== undefined);

  const needsLook = useMemo(
    () =>
      [...(pairings.data ?? [])]
        .filter((p) => p.came_true === "unknown" || p.risk >= 4)
        .sort((a, b) => b.risk - a.risk),
    [pairings.data],
  );

  const addRoute = (raw: string) => {
    const id = raw.trim().toUpperCase();
    if (!id) return;
    const known = routesList.data?.find((r) => r.id.toUpperCase() === id);
    const rid = known?.id ?? raw.trim();
    setChosenRoutes((rs) => (rs.includes(rid) ? rs : [...rs, rid]));
    setQuery("");
  };

  const selectBus = (id: string) => {
    setSelectedId(id);
    setFollowId(null);
  };

  const bus = vehicles.find((v) => v.id === selectedId);
  const pairing = selectedId ? pairByBus.get(selectedId) : undefined;
  const token = mapConfig.data?.mapbox_token ?? null;
  const fleetValue = (v: number | undefined) => (snapshot.data && v !== undefined ? String(v) : "…");

  return (
    <div className="relative flex min-h-dvh flex-col bg-ground md:h-dvh md:overflow-hidden">
      {/* Map layer */}
      <div className="relative h-[55dvh] w-full md:absolute md:inset-0 md:h-auto">
        {token && !mapFailed ? (
          <BusMap
            token={token}
            vehicles={shown}
            states={states}
            selectedId={selectedId}
            followId={followId}
            routes={routeDetails}
            scene={scene}
            theme={theme}
            layers={layers}
            onSelect={selectBus}
            onError={() => setMapFailed(true)}
          />
        ) : (
          <div className="sky-soft grid size-full place-items-center px-6 pt-20">
            {!mapConfig.isPending && (
              <Empty className={cn(panel, "max-w-md flex-none border-solid p-7")}>
                <EmptyHeader>
                  <EmptyTitle className="font-serif text-[28px] leading-[1.15] font-normal">
                    {mapFailed ? "The map couldn't load" : BUS_COPY.noToken}
                  </EmptyTitle>
                  <EmptyDescription className="text-body-sm text-ink-muted">{BUS_COPY.noTokenBody}</EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </div>
        )}
      </div>

      <AppNav
        className="pointer-events-none absolute inset-x-0 top-0 z-10 [&>*]:pointer-events-auto"
        right={
          <div className="hidden flex-wrap items-center gap-2 lg:flex">
            <Segmented label="Scene" value={scene} options={SCENES} onChange={setScene} />
            <Toggle on={layers.traffic} label="Traffic" onClick={() => setLayers((l) => ({ ...l, traffic: !l.traffic }))} />
            <Toggle on={layers.cameras} label="Cameras" onClick={() => setLayers((l) => ({ ...l, cameras: !l.cameras }))} />
            <Segmented label="Map theme" value={theme} options={THEMES} onChange={setUserTheme} />
          </div>
        }
      />

      {/* Left panel: routes, follow, status */}
      <aside className={cn(panel, "z-10 m-4 flex flex-col gap-4 p-4 md:absolute md:top-[76px] md:left-4 md:m-0 md:w-[300px]")}>
        <form
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            addRoute(query);
          }}
        >
          <label htmlFor="route-search" className="text-eye">
            {BUS_COPY.routes}
          </label>
          <Input
            id="route-search"
            list="route-list"
            value={query}
            placeholder={BUS_COPY.routeSearch}
            onChange={(e) => setQuery(e.target.value)}
          />
          <datalist id="route-list">
            {routesList.data?.slice(0, 800).map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </datalist>
        </form>
        {chosenRoutes.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {chosenRoutes.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setChosenRoutes((rs) => rs.filter((x) => x !== r))}
                className="inline-flex h-7 items-center gap-1.5 rounded-full bg-pill px-3 text-xs font-medium text-on-ink"
                aria-label={`Remove route ${r}`}
              >
                {r} <span aria-hidden>×</span>
              </button>
            ))}
          </div>
        )}
        <Button
          size="sm"
          variant={followId ? "default" : "glass"}
          disabled={!bus}
          onClick={() => setFollowId((f) => (f ? null : selectedId))}
        >
          {followId ? `${BUS_COPY.following} ${followId}` : BUS_COPY.follow}
        </Button>
        <div className="grid grid-cols-2 gap-2">
          <Tile label="Connected" value={link === "live" ? "Live" : link === "polling" ? "Every 30s" : "…"} />
          <Tile label="Vehicles" value={fleetValue(snapshot.data?.vehicles.length)} />
          <Tile label="Routes" value={fleetValue(snapshot.data?.routes)} />
          <Tile label="Latency" value={snapshot.data ? `${snapshot.data.latency_ms} ms` : "…"} />
        </div>
        {snapshot.isError && <p className="text-body-sm text-risk-high">We can&apos;t reach the bus feed right now. We&apos;ll keep trying.</p>}
      </aside>

      {/* Right panel: needs a look, or the selected bus */}
      <aside
        className={cn(
          panel,
          "z-10 mx-4 mb-4 flex max-h-none flex-col gap-3 overflow-y-auto p-4 md:absolute md:top-[76px] md:right-4 md:bottom-16 md:m-0 md:max-h-[calc(100dvh-150px)] md:w-[340px] md:self-start",
        )}
        aria-label={selectedId ? "Selected bus" : BUS_COPY.needsLook}
      >
        {selectedId ? (
          <BusDrawer
            bus={bus}
            pairing={pairing}
            incident={pairing ? incidentById.get(pairing.incident_id) : undefined}
            nudged={Boolean(pairing && alerts.data?.some((a) => a.incident_id === pairing.incident_id))}
            following={followId === selectedId}
            onFollow={() => setFollowId((f) => (f === selectedId ? null : selectedId))}
            onShowRoute={() => bus && setChosenRoutes((rs) => (rs.includes(bus.route) ? rs : [...rs, bus.route]))}
            onClose={() => {
              setSelectedId(null);
              setFollowId(null);
            }}
          />
        ) : (
          <>
            <h2 className="text-[13px] leading-none font-medium tracking-[0.06em] text-ink-muted uppercase">
              {BUS_COPY.needsLook}
            </h2>
            {needsLook.length === 0 ? (
              <p className="text-body-sm text-ink-muted">{BUS_COPY.needsLookNone}</p>
            ) : (
              <ul className="flex flex-col">
                {needsLook.map((p, n) => {
                  const inc = incidentById.get(p.incident_id);
                  const live = vehicles.some((v) => v.id === p.vehicle_id);
                  const st = busState(p);
                  return (
                    <li key={`${p.vehicle_id}-${p.incident_id}`} className={cn(n > 0 && "border-t border-hairline")}>
                      <button
                        type="button"
                        onClick={() => selectBus(p.vehicle_id)}
                        className="flex w-full flex-col gap-1.5 py-3 text-left"
                      >
                        <span className="flex items-center gap-2">
                          <StatusPill tone={BUS_STATE[st].tone}>{riskLabel(p.risk)}</StatusPill>
                          <span className="text-body-sm font-medium">Route {p.route}</span>
                          <span className="text-data text-ink-muted">{p.vehicle_id}</span>
                        </span>
                        {inc && <span className="line-clamp-2 text-body-sm text-ink-muted">{inc.what_next}</span>}
                        {!live && <span className="text-data text-ink-muted">Not on the road right now</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </>
        )}
      </aside>

      {/* Mobile controls (desktop has them in the top bar) */}
      <div className="mx-4 mb-4 flex flex-wrap gap-2 lg:hidden">
        <Segmented label="Scene" value={scene} options={SCENES} onChange={setScene} />
        <Segmented label="Map theme" value={theme} options={THEMES} onChange={setUserTheme} />
        <Toggle on={layers.traffic} label="Traffic" onClick={() => setLayers((l) => ({ ...l, traffic: !l.traffic }))} />
        <Toggle on={layers.cameras} label="Cameras" onClick={() => setLayers((l) => ({ ...l, cameras: !l.cameras }))} />
      </div>

      {/* Bottom bar */}
      <div className="glass z-10 mx-4 mb-4 flex flex-wrap items-center gap-3 rounded-full px-4 py-2 shadow-float md:absolute md:bottom-4 md:left-4 md:m-0">
        <Clock />
        <WeatherPill />
        <a
          href="https://tfl.gov.uk/info-for/open-data-users/"
          target="_blank"
          rel="noreferrer"
          className="text-data text-ink-muted underline-offset-2 hover:underline"
        >
          {BUS_COPY.poweredBy}
        </a>
      </div>
    </div>
  );
}
