"use client";

import "mapbox-gl/dist/mapbox-gl.css";
import type { GeoJSONSource, Map as MapboxMap, MapMouseEvent } from "mapbox-gl";
import { useEffect, useRef, useState } from "react";
import type { RouteDetail, Vehicle } from "@/lib/api/types";
import { BUS_STATE, type BusState } from "@/lib/copy";

export type Scene = "2d" | "3d" | "drone";
export type Theme = "light" | "dark" | "satellite" | "night";
export interface Layers {
  traffic: boolean;
  cameras: boolean;
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
    paint: { "line-color": cssVar("--ink"), "line-width": 3, "line-opacity": 0.75 },
  });
  map.addSource("buses", { type: "geojson", data: empty });
  map.addLayer({
    id: "cameras",
    type: "circle",
    source: "buses",
    filter: ["==", ["get", "paired"], true],
    paint: {
      "circle-radius": 11,
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-width": 2,
      "circle-stroke-color": ["get", "color"],
    },
  });
  map.addLayer({
    id: "buses",
    type: "circle",
    source: "buses",
    paint: {
      "circle-radius": ["case", ["get", "sel"], 9, ["get", "paired"], 6, 4],
      "circle-color": ["get", "color"],
      "circle-stroke-width": ["case", ["get", "sel"], 3, 1],
      "circle-stroke-color": cssVar("--surface"),
    },
  });
}

export function BusMap({
  token,
  vehicles,
  states,
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
  states: Map<string, BusState>;
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
  // Bumped on every style load so data effects re-apply to the fresh style.
  const [styleVersion, setStyleVersion] = useState(0);

  useEffect(() => {
    onSelectRef.current = onSelect;
    onErrorRef.current = onError;
  });

  // Create the map once, client-side only (keeps window out of the static prerender).
  useEffect(() => {
    let cancelled = false;
    let map: MapboxMap | null = null;
    void import("mapbox-gl").then(({ default: mapboxgl }) => {
      if (cancelled || !box.current) return;
      mapboxgl.accessToken = token;
      map = new mapboxgl.Map({
        container: box.current,
        style: styleRef.current,
        config: { basemap: { lightPreset: PRESET[theme] } },
        center: LONDON,
        zoom: 10.6,
        ...SCENE[scene],
      });
      mapRef.current = map;
      map.on("style.load", () => {
        if (!map) return;
        addLayers(map);
        setStyleVersion((v) => v + 1);
      });
      map.on("click", "buses", (e: MapMouseEvent) => {
        const id = e.features?.[0]?.properties?.id;
        if (typeof id === "string") onSelectRef.current(id);
      });
      map.on("mouseenter", "buses", () => map && (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "buses", () => map && (map.getCanvas().style.cursor = ""));
      map.on("error", (e) => {
        // Auth failures mean the token is wrong; other errors (one tile) are survivable.
        const status = (e.error as { status?: number } | undefined)?.status;
        if (status === 401 || status === 403) onErrorRef.current();
      });
    });
    return () => {
      cancelled = true;
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
      map.setStyle(url, { config: { basemap: { lightPreset: PRESET[theme] } } });
    } else if (map.isStyleLoaded()) {
      map.setConfigProperty("basemap", "lightPreset", PRESET[theme]);
    }
  }, [theme, styleVersion]);

  useEffect(() => {
    mapRef.current?.easeTo({ ...SCENE[scene], duration: 800 });
  }, [scene]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !styleVersion || !map.getLayer("traffic")) return;
    map.setLayoutProperty("traffic", "visibility", layers.traffic ? "visible" : "none");
    map.setLayoutProperty("cameras", "visibility", layers.cameras ? "visible" : "none");
  }, [layers, styleVersion]);

  useEffect(() => {
    const src = mapRef.current?.getSource("buses") as GeoJSONSource | undefined;
    if (!src) return;
    const colour = Object.fromEntries(
      (Object.keys(BUS_STATE) as BusState[]).map((k) => [k, cssVar(BUS_STATE[k].cssVar)]),
    ) as Record<BusState, string>;
    src.setData({
      type: "FeatureCollection",
      features: vehicles.map((v) => {
        const state = states.get(v.id) ?? "road";
        return {
          type: "Feature",
          geometry: { type: "Point", coordinates: [v.lon, v.lat] },
          properties: { id: v.id, color: colour[state], paired: state !== "road", sel: v.id === selectedId },
        };
      }),
    });
  }, [vehicles, states, selectedId, styleVersion]);

  useEffect(() => {
    const src = mapRef.current?.getSource("routes") as GeoJSONSource | undefined;
    if (!src) return;
    src.setData({
      type: "FeatureCollection",
      features: routes.flatMap((r) =>
        r.directions
          .filter((d) => d.coords.length > 1)
          .map((d) => ({ type: "Feature" as const, geometry: { type: "LineString" as const, coordinates: d.coords }, properties: { id: r.id } })),
      ),
    });
  }, [routes, styleVersion]);

  // Follow (or jump to) the bus each time the fleet updates.
  const target = vehicles.find((v) => v.id === (followId ?? selectedId));
  const tLon = target?.lon;
  const tLat = target?.lat;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || tLon === undefined || tLat === undefined) return;
    map.easeTo({ center: [tLon, tLat], zoom: Math.max(map.getZoom(), followId ? 15 : 13), duration: 900 });
  }, [tLon, tLat, followId]);

  return <div ref={box} className="absolute inset-0" aria-label="Live map of London buses" role="region" />;
}
