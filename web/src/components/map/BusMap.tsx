"use client";

import "mapbox-gl/dist/mapbox-gl.css";
import type { GeoJSONSource, Map as MapboxMap, MapMouseEvent, Marker } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";
import type { RouteDetail, Vehicle } from "@/lib/api/types";
import { BUS_STATE, type BusState } from "@/lib/copy";

export type Scene = "2d" | "3d" | "drone";
export type Theme = "light" | "dark" | "satellite" | "night";
export interface Layers {
  traffic: boolean;
  /** Off by default: only the buses that need attention are drawn. */
  all: boolean;
}

/** A bus that needs attention, drawn as a numbered marker (1 = look first). */
export interface AttentionBus {
  id: string;
  n: number;
  lon: number;
  lat: number;
  state: BusState;
}

const LONDON: [number, number] = [-0.1276, 51.5072];
const STYLE_STANDARD = "mapbox://styles/mapbox/standard";
const STYLE_SATELLITE = "mapbox://styles/mapbox/standard-satellite";
const PRESET: Record<Theme, "day" | "dusk" | "night"> = { light: "day", dark: "dusk", night: "night", satellite: "day" };
const SCENE: Record<Scene, { pitch: number; bearing: number }> = {
  "2d": { pitch: 0, bearing: 0 },
  "3d": { pitch: 50, bearing: -12 },
  drone: { pitch: 72, bearing: -35 },
};

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function styleUrl(theme: Theme) {
  return theme === "satellite" ? STYLE_SATELLITE : STYLE_STANDARD;
}

// Mapbox Standard basemap config (docs.mapbox.com/map-styles/standard/api): theme default|faded|monochrome|custom,
// lightPreset dawn|day|dusk|night, showPointOfInterestLabels / showTransitLabels / showPlaceLabels booleans.
function basemapConfig(theme: Theme): Record<string, string | boolean> {
  const labels = { showPointOfInterestLabels: false, showTransitLabels: false, showPlaceLabels: true };
  if (theme === "satellite") return { lightPreset: PRESET[theme], ...labels };
  return { lightPreset: PRESET[theme], theme: theme === "light" ? "faded" : "monochrome", ...labels };
}

function applyBasemap(map: MapboxMap, theme: Theme) {
  for (const [key, value] of Object.entries(basemapConfig(theme))) {
    try {
      map.setConfigProperty("basemap", key, value);
    } catch {
      // A style without this key (e.g. satellite variants) just keeps its default.
    }
  }
}

// Bus dot size by zoom (z9 -> z12 -> z15); paired buses are 2px larger, the selected bus larger still.
const BASE_R = { 9: 1.6, 12: 3, 15: 6 } as const;
function radius(extra: number, selectedExtra: number): unknown[] {
  return [
    "interpolate", ["linear"], ["zoom"],
    9, ["case", ["get", "sel"], BASE_R[9] + selectedExtra, BASE_R[9] + extra],
    12, ["case", ["get", "sel"], BASE_R[12] + selectedExtra, BASE_R[12] + extra],
    15, ["case", ["get", "sel"], BASE_R[15] + selectedExtra, BASE_R[15] + extra],
  ];
}
const STROKE_W = ["interpolate", ["linear"], ["zoom"], 9, 0.5, 15, 1.5];

/** Adds our sources and layers; runs again after every style swap (satellite <-> standard). */
function addLayers(map: MapboxMap) {
  const empty = { type: "FeatureCollection" as const, features: [] };
  map.addSource("traffic", { type: "vector", url: "mapbox://mapbox.mapbox-traffic-v1" });
  map.addLayer({
    id: "traffic",
    type: "line",
    source: "traffic",
    "source-layer": "traffic",
    layout: { visibility: "none" },
    paint: {
      "line-width": 2,
      "line-color": [
        "match",
        ["get", "congestion"],
        "low", cssVar("--risk-low"),
        "moderate", cssVar("--risk-mid"),
        "heavy", cssVar("--risk-high"),
        "severe", cssVar("--risk-high"),
        cssVar("--slate"),
      ],
    },
  });
  map.addSource("routes", { type: "geojson", data: empty });
  map.addLayer({
    id: "routes",
    type: "line",
    source: "routes",
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": cssVar("--ink"), "line-width": 3, "line-opacity": 0.7 },
  });
  map.addSource("buses", { type: "geojson", data: empty });
  // Context buses ("Show all buses" or the chosen route): small and faint.
  map.addLayer({
    id: "buses",
    type: "circle",
    source: "buses",
    paint: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox expression arrays
      "circle-radius": radius(0, 3) as any,
      "circle-color": cssVar("--bus"),
      "circle-opacity": ["case", ["get", "sel"], 0.95, 0.4],
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      "circle-stroke-width": STROKE_W as any,
      "circle-stroke-color": cssVar("--surface"),
      "circle-stroke-opacity": 0.6,
    },
  });
}

export function BusMap({
  token,
  vehicles,
  attention,
  selectedId,
  followId,
  routes,
  scene,
  theme,
  layers,
  onSelect,
  onError,
}: {
  token: string;
  vehicles: Vehicle[];
  attention: AttentionBus[];
  selectedId: string | null;
  followId: string | null;
  routes: RouteDetail[];
  scene: Scene;
  theme: Theme;
  layers: Layers;
  onSelect: (id: string) => void;
  onError: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapboxMap | null>(null);
  const styleRef = useRef<string>(styleUrl(theme));
  const onSelectRef = useRef(onSelect);
  const onErrorRef = useRef(onError);
  const themeRef = useRef(theme);
  const followIdRef = useRef(followId);
  // Bumped on every style load so data effects re-apply to the fresh style.
  const [styleVersion, setStyleVersion] = useState(0);
  const markers = useRef(new Map<string, { m: Marker; el: HTMLButtonElement }>());
  const [mapboxReady, setMapboxReady] = useState<typeof import("mapbox-gl").default | null>(null);
  const routesRef = useRef(routes);

  useEffect(() => {
    onSelectRef.current = onSelect;
    onErrorRef.current = onError;
    themeRef.current = theme;
    followIdRef.current = followId;
    routesRef.current = routes;
  });

  // Create the map once, client-side only (keeps window out of the static prerender).
  useEffect(() => {
    let cancelled = false;
    let map: MapboxMap | null = null;
    void import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled || !box.current) return;
      mapboxgl.accessToken = token;
      setMapboxReady(() => mapboxgl);
      map = new mapboxgl.Map({
        container: box.current,
        style: styleRef.current,
        config: { basemap: basemapConfig(theme) },
        center: LONDON,
        zoom: 10.6,
        ...SCENE[scene],
      });
      mapRef.current = map;
      map.on("style.load", () => {
        if (!map) return;
        addLayers(map);
        applyBasemap(map, themeRef.current);
        setStyleVersion((v) => v + 1);
      });
      for (const layer of ["buses"]) {
        map.on("click", layer, (e: MapMouseEvent) => {
          const id = e.features?.[0]?.properties?.id;
          if (typeof id === "string") onSelectRef.current(id);
        });
        map.on("mouseenter", layer, () => map && (map.getCanvas().style.cursor = "pointer"));
        map.on("mouseleave", layer, () => map && (map.getCanvas().style.cursor = ""));
      }
      map.on("error", (e) => {
        // Auth failures mean the token is wrong; other errors (one tile) are survivable.
        const status = (e.error as { status?: number } | undefined)?.status;
        if (status === 401 || status === 403) onErrorRef.current();
      });
    });
    const placed = markers.current;
    return () => {
      cancelled = true;
      placed.forEach((e) => e.m.remove());
      placed.clear();
      map?.remove();
      mapRef.current = null;
    };
    // Map is created once per token; theme/scene changes are applied below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Theme: swap style only between standard and satellite; light presets are a config change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const url = styleUrl(theme);
    if (url !== styleRef.current) {
      styleRef.current = url;
      map.setStyle(url);
    } else if (map.isStyleLoaded()) {
      applyBasemap(map, theme);
    }
  }, [theme, styleVersion]);

  useEffect(() => {
    mapRef.current?.easeTo({ ...SCENE[scene], duration: 800 });
  }, [scene]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleVersion || !map.getLayer("traffic")) return;
    map.setLayoutProperty("traffic", "visibility", layers.traffic ? "visible" : "none");
  }, [layers, styleVersion]);

  useEffect(() => {
    const src = mapRef.current?.getSource("buses") as GeoJSONSource | undefined;
    if (!src) return;
    src.setData({
      type: "FeatureCollection",
      features: vehicles.map((v) => {
        return {
          type: "Feature",
          geometry: { type: "Point", coordinates: [v.lon, v.lat] },
          properties: { id: v.id, sel: v.id === selectedId },
        };
      }),
    });
  }, [vehicles, selectedId, styleVersion]);

  // Numbered HTML markers for the buses that need attention (few, crisp, no glyph dependency).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapboxReady) return;
    const seen = new Set<string>();
    for (const a of attention) {
      seen.add(a.id);
      let entry = markers.current.get(a.id);
      if (!entry) {
        const el = document.createElement("button");
        el.type = "button";
        el.className =
          "grid size-6 place-items-center rounded-full border-2 border-white font-mono text-[11px] font-semibold text-white shadow-float transition-transform duration-150 hover:scale-110 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          onSelectRef.current(a.id);
        });
        entry = { m: new mapboxReady.Marker({ element: el }).setLngLat([a.lon, a.lat]).addTo(map), el };
        markers.current.set(a.id, entry);
      }
      entry.m.setLngLat([a.lon, a.lat]);
      entry.el.textContent = String(a.n);
      entry.el.setAttribute("aria-label", `Bus ${a.n} of ${attention.length}: ${a.id}, ${BUS_STATE[a.state].label}`);
      entry.el.style.background = cssVar(BUS_STATE[a.state].cssVar);
      entry.el.style.zIndex = String(1000 - a.n);
      entry.el.style.transform = "";
      entry.el.dataset.sel = String(a.id === selectedId);
      entry.el.style.boxShadow = a.id === selectedId ? `0 0 0 3px ${cssVar("--ink")}` : "";
    }
    for (const [id, entry] of markers.current) {
      if (!seen.has(id)) {
        entry.m.remove();
        markers.current.delete(id);
      }
    }
  }, [attention, selectedId, mapboxReady]);

  // On load, frame the attention buses once (unless a bus or route deep link already framed the map).
  const framed = useRef(false);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || framed.current || attention.length === 0) return;
    framed.current = true;
    if (followIdRef.current || selectedId || routesRef.current.length > 0) return;
    const lons = attention.map((a) => a.lon);
    const lats = attention.map((a) => a.lat);
    map.fitBounds(
      [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ],
      {
        padding: window.innerWidth >= 768 ? { top: 100, bottom: 90, left: 330, right: 380 } : 32,
        maxZoom: 13,
        duration: 900,
      },
    );
  }, [attention, selectedId, mapboxReady]);

  // Both directions of every chosen route, under the buses.
  const routeKey = routes.map((r) => `${r.id}:${r.directions.map((d) => d.coords.length).join("/")}`).join(",");
  const fittedKey = useRef("");
  useEffect(() => {
    const map = mapRef.current;
    const src = map?.getSource("routes") as GeoJSONSource | undefined;
    if (!map || !src) return;
    const lines = routesRef.current.flatMap((r) =>
      r.directions
        .filter((d) => d.coords.length > 1)
        .map((d) => ({
          type: "Feature" as const,
          geometry: { type: "LineString" as const, coordinates: d.coords },
          properties: { id: r.id, dir: d.dir },
        })),
    );
    src.setData({ type: "FeatureCollection", features: lines });
    if (lines.length === 0 || fittedKey.current === routeKey || followIdRef.current) return;
    fittedKey.current = routeKey;
    const all = lines.flatMap((l) => l.geometry.coordinates);
    const lons = all.map((c) => c[0]);
    const lats = all.map((c) => c[1]);
    map.fitBounds(
      [
        [Math.min(...lons), Math.min(...lats)],
        [Math.max(...lons), Math.max(...lats)],
      ],
      {
        // Desktop panels cover the left 320px and right 360px of the map.
        padding: window.innerWidth >= 768 ? { top: 90, bottom: 80, left: 340, right: 380 } : 24,
        maxZoom: 14,
        duration: 900,
      },
    );
  }, [routeKey, styleVersion]);

  // Follow (or jump to) the bus each time the fleet updates.
  const targetId = followId ?? selectedId;
  const target = vehicles.find((v) => v.id === targetId) ?? attention.find((a) => a.id === targetId);
  const tLon = target?.lon;
  const tLat = target?.lat;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || tLon === undefined || tLat === undefined) return;
    map.easeTo({ center: [tLon, tLat], zoom: Math.max(map.getZoom(), followId ? 15 : 13), duration: 900 });
  }, [tLon, tLat, followId]);

  // mapbox-gl.css sets .mapboxgl-map{position:relative}, which beats `absolute`, so size an outer box and fill it.
  return (
    <div className="absolute inset-0">
      <div ref={box} className="h-full w-full" aria-label="Live map of London buses" role="region" />
    </div>
  );
}
