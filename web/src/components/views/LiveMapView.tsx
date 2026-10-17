"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import type { Route } from "next";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppNav } from "@/components/AppNav";
import { AskFootage } from "@/components/map/AskFootage";
import { BusDrawer } from "@/components/map/BusDrawer";
import { BusMap, type Layers, type Scene, type Theme } from "@/components/map/BusMap";
import { MapControls } from "@/components/map/MapControls";
import { MAP_COPY } from "@/components/map/mapCopy";
import { StatusPill } from "@/components/StatusPill";
import { WeatherPill } from "@/components/WeatherPill";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { useFleet } from "@/lib/api/fleet";
import {
  allIncidentsOptions,
  mapConfigOptions,
  pairingsOptions,
  routeOptions,
  routesOptions,
  weatherOptions,
} from "@/lib/api/queries";
import { BUS_COPY, busState, pairingPill, riskLabel, riskTone, type BusState } from "@/lib/copy";
import { cn } from "@/lib/utils";

const panel = "glass-map rounded-panel shadow-float";
const NUMBER = new Intl.NumberFormat("en-GB");

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

export function LiveMapView() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const { snapshot, link } = useFleet();
  const mapConfig = useQuery(mapConfigOptions());
  const routesList = useQuery(routesOptions());
  const pairings = useQuery(pairingsOptions());
  const incidents = useQuery(allIncidentsOptions());
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
  const [leftOpen, setLeftOpen] = useState(true);
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
  // After a pod restart the fleet starts empty and pairings come back empty; refetch once buses appear.
  const hadBuses = useRef(false);
  const refetchPairings = pairings.refetch;
  useEffect(() => {
    const has = vehicles.length > 0;
    if (has && !hadBuses.current) void refetchPairings();
    hadBuses.current = has;
  }, [vehicles.length, refetchPairings]);

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
        : vehicles.filter((v) => chosenRoutes.includes(v.route) || v.id === selectedId || pairByBus.has(v.id)),
    [vehicles, chosenRoutes, selectedId, pairByBus],
  );
  const routeDetails = useQueries({ queries: chosenRoutes.map((id) => routeOptions(id)) })
    .map((q) => q.data)
    .filter((d) => d !== undefined);
  const needsLook = useMemo(() => [...(pairings.data ?? [])].sort((a, b) => b.risk - a.risk), [pairings.data]);

  const addRoute = (raw: string) => {
    const typed = raw.trim();
    if (!typed) return;
    const known = routesList.data?.find((r) => r.id.toUpperCase() === typed.toUpperCase());
    const rid = known?.id ?? typed;
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
  const statusLine = snapshot.data
    ? `${MAP_COPY.liveLink[link]} · ${NUMBER.format(snapshot.data.vehicles.length)} buses · ${NUMBER.format(snapshot.data.routes)} routes · ${snapshot.data.latency_ms} ms`
    : MAP_COPY.liveLink.connecting;

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
          <div className="hidden items-center gap-2 md:flex">
            <AskFootage />
            <MapControls
              scene={scene}
              theme={theme}
              layers={layers}
              onScene={setScene}
              onTheme={setUserTheme}
              onLayers={setLayers}
            />
          </div>
        }
      />

      {/* Left panel: routes, follow, one status line */}
      <aside
        className={cn(panel, "z-10 m-4 flex flex-col gap-3 p-4 md:absolute md:top-[76px] md:left-4 md:m-0 md:w-[280px]")}
        aria-label={MAP_COPY.routesTitle}
      >
        <div className="flex items-center gap-2">
          <h2 className="text-eye">{MAP_COPY.routesTitle}</h2>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => setLeftOpen((o) => !o)}
            aria-expanded={leftOpen}
            aria-controls="routes-body"
            className="rounded-full px-2 text-data text-slate hover:text-ink focus-visible:ring-[3px] focus-visible:ring-ring/50"
          >
            {leftOpen ? MAP_COPY.hide : MAP_COPY.show}
          </button>
        </div>
        {leftOpen && (
          <div id="routes-body" className="flex flex-col gap-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                addRoute(query);
              }}
            >
              <label htmlFor="route-search" className="sr-only">
                {BUS_COPY.routeSearch}
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
                    className="inline-flex h-7 items-center gap-1.5 rounded-full bg-pill px-3 text-xs font-medium text-on-ink transition-opacity duration-150 hover:opacity-80"
                    aria-label={`Remove route ${r}`}
                  >
                    {r} <span aria-hidden>×</span>
                  </button>
                ))}
              </div>
            )}
            {bus && (
              <Button
                size="sm"
                variant={followId ? "default" : "outline"}
                onClick={() => setFollowId((f) => (f ? null : selectedId))}
                aria-pressed={Boolean(followId)}
              >
                {followId ? `${BUS_COPY.following} ${followId}` : `${BUS_COPY.follow} ${bus.id}`}
              </Button>
            )}
          </div>
        )}
        <p className="text-data text-ink-muted" aria-live="polite">
          <span
            aria-hidden
            className={cn("mr-1.5 inline-block size-1.5 rounded-full align-middle", link === "live" ? "bg-truth" : "bg-slate")}
          />
          {statusLine}
        </p>
        {snapshot.isError && <p className="text-body-sm text-risk-high">We can&apos;t reach the bus feed right now. We&apos;ll keep trying.</p>}
      </aside>

      {/* Right panel: the list, or the selected bus (back arrow returns to the list) */}
      <aside
        className={cn(
          panel,
          "z-10 mx-4 mb-4 flex max-h-[80dvh] flex-col overflow-hidden md:absolute md:top-[76px] md:right-4 md:m-0 md:max-h-[calc(100dvh-160px)] md:w-[340px]",
        )}
        aria-label={selectedId ? "Selected bus" : BUS_COPY.needsLook}
      >
        {selectedId ? (
          <BusDrawer
            key={selectedId}
            busId={selectedId}
            bus={bus}
            pairing={pairing}
            incident={pairing ? incidentById.get(pairing.incident_id) : undefined}
            following={followId === selectedId}
            onFollow={() => setFollowId((f) => (f === selectedId ? null : selectedId))}
            onShowRoute={() => bus && setChosenRoutes((rs) => (rs.includes(bus.route) ? rs : [...rs, bus.route]))}
            onBack={() => {
              setSelectedId(null);
              setFollowId(null);
            }}
          />
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-4 [&>*]:shrink-0">
            <h2 className="text-[13px] leading-none font-medium tracking-[0.06em] text-ink-muted uppercase">
              {BUS_COPY.needsLook} <span className="font-mono">{needsLook.length}</span>
            </h2>
            {needsLook.length === 0 ? (
              <p className="text-body-sm text-ink-muted">{BUS_COPY.needsLookNone}</p>
            ) : (
              <ul className="-mx-2 flex flex-col">
                {needsLook.map((p, n) => {
                  const inc = incidentById.get(p.incident_id);
                  const live = vehicles.some((v) => v.id === p.vehicle_id);
                  const pill = pairingPill(p);
                  return (
                    <li key={`${p.vehicle_id}-${p.incident_id}`} className={cn(n > 0 && "border-t border-hairline")}>
                      <button
                        type="button"
                        onClick={() => selectBus(p.vehicle_id)}
                        className="flex w-full flex-col gap-1.5 rounded-md px-2 py-3 text-left transition-colors duration-150 hover:bg-surface-sunk focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
                      >
                        <span className="flex flex-wrap items-center gap-2">
                          <StatusPill tone={riskTone(p.risk)}>{riskLabel(p.risk)}</StatusPill>
                          <StatusPill tone={pill.tone}>{pill.label}</StatusPill>
                        </span>
                        <span className="flex items-baseline gap-2">
                          <span className="text-body-sm font-medium">Route {p.route}</span>
                          <span className="truncate text-data text-ink-muted">{p.vehicle_id}</span>
                        </span>
                        {inc && <span className="line-clamp-2 text-body-sm text-ink-muted">{inc.what_next}</span>}
                        {!live && <span className="text-data text-ink-muted">Not on the road right now</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </aside>

      {/* Phone: ask + map controls under the panels */}
      <div className="mx-4 mb-4 flex flex-wrap gap-2 md:hidden">
        <AskFootage />
        <MapControls scene={scene} theme={theme} layers={layers} onScene={setScene} onTheme={setUserTheme} onLayers={setLayers} />
      </div>

      {/* Bottom bar */}
      <div className="glass-map z-10 mx-4 mb-4 flex flex-wrap items-center gap-3 rounded-full px-4 py-2 shadow-float md:absolute md:bottom-4 md:left-4 md:m-0">
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
