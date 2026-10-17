"""London buses from TfL Open Data: route list, stop coordinates, live arrivals -> estimated positions.

A bus's position is its NEXT stop (TfL arrivals carry no GPS); bearing points to the following stop
when the same vehicle has a prediction for it. Unkeyed TfL allows ~50 req/min, so every call goes
through one pacer and a full sweep of ~700 routes may take longer than fleet_poll_s.
"""

import asyncio
import hashlib
import json
import logging
import math
import re
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .clients.http import HttpClient
from .contracts import (
    FleetSnapshot,
    Pairing,
    RouteDetail,
    RouteDirection,
    RouteStop,
    RouteSummary,
    Vehicle,
)
from .modes import PAIRING_MODE_GROUPS
from .settings import Settings
from .store import IncidentStore

log = logging.getLogger("sixthsense.tfl")

ARRIVALS_BATCH = 20  # line ids per /Line/{ids}/Arrivals call
REQ_PER_MIN_NO_KEY = 40  # stay under TfL's ~50/min anonymous limit
REQ_PER_MIN_KEY = 400
STOP_PAGES_MAX = 60
STOPS_CACHE_FILE = "tfl_stops.json"
STOPS_CACHE_MAX_AGE_S = 7 * 24 * 3600
PAIRING_TTL_S = 30 * 60
RETRY_AFTER_ERROR_S = 15.0
ROUTE_ID_RE = re.compile(r"^[a-z0-9-]{1,12}$")
DIRECTIONS = ("inbound", "outbound")

StopCoords = dict[str, tuple[float, float, str]]  # naptanId -> (lon, lat, name)
SnapshotFn = Callable[[FleetSnapshot], Awaitable[None]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def bearing_deg(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Initial compass bearing from point 1 to point 2, 0-360."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return round((math.degrees(math.atan2(x, y)) + 360) % 360, 1)


def valid_route_id(route_id: str) -> bool:
    return bool(ROUTE_ID_RE.match(route_id))


def vehicles_from_arrivals(predictions: list[dict[str, Any]], stops: StopCoords, ts: str) -> list[Vehicle]:
    """Earliest prediction per vehicleId = its next stop; the next distinct stop gives the bearing."""
    by_vehicle: dict[str, list[dict[str, Any]]] = {}
    for p in predictions:
        vid = str(p.get("vehicleId") or "").strip()
        if vid and p.get("naptanId") and p.get("lineId"):
            by_vehicle.setdefault(vid, []).append(p)
    out: list[Vehicle] = []
    for vid, preds in by_vehicle.items():
        preds.sort(key=lambda p: int(p.get("timeToStation") or 0))
        nxt = preds[0]
        coords = stops.get(nxt["naptanId"])
        if coords is None:
            continue  # stop not in the cache yet; skip rather than invent a position
        lon, lat, stop_name = coords
        bearing = None
        following = next((p for p in preds[1:] if p["naptanId"] != nxt["naptanId"]), None)
        if following and (fc := stops.get(following["naptanId"])):
            bearing = bearing_deg(lon, lat, fc[0], fc[1])
        out.append(
            Vehicle(
                id=vid,
                route=str(nxt["lineId"]),
                dir="inbound" if nxt.get("direction") == "inbound" else "outbound",
                towards=str(nxt.get("towards") or nxt.get("destinationName") or ""),
                next_stop=str(nxt["naptanId"]),
                next_stop_name=str(nxt.get("stationName") or stop_name),
                eta_s=max(0, int(nxt.get("timeToStation") or 0)),
                lon=lon,
                lat=lat,
                bearing=bearing,
                ts=ts,
            )
        )
    return out


class _Pacer:
    """Spaces requests evenly so a sweep never trips TfL's rate limit."""

    def __init__(self, per_min: int) -> None:
        self.interval = 60.0 / per_min
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            delay = self._next - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._next = time.monotonic() + self.interval


class Fleet:
    def __init__(self, settings: Settings, http: HttpClient, store: IncidentStore) -> None:
        self.settings = settings
        self.http = http
        self.store = store
        has_key = bool(settings.tfl_app_key.get_secret_value())
        self._pacer = _Pacer(REQ_PER_MIN_KEY if has_key else REQ_PER_MIN_NO_KEY)
        self.routes: list[RouteSummary] = []
        self.stops: StopCoords = {}
        self.snapshot = FleetSnapshot(ts=_now_iso())
        self._by_route: dict[str, list[Vehicle]] = {}
        self._route_cache: dict[str, RouteDetail] = {}
        # incident_id -> (vehicle_id, expires, stop_name, towards); stop/towards frozen at pairing time
        self._pairs: dict[str, tuple[str, float, str, str]] = {}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        await self._pacer.wait()
        r = await self.http.get(path, params=params)
        r.raise_for_status()
        return r.json()

    # ---------- startup data ----------
    async def load_routes(self) -> None:
        data = await self._get("/Line/Mode/bus")
        self.routes = sorted(
            (RouteSummary(id=str(x["id"]), name=str(x.get("name") or x["id"])) for x in data if x.get("id")),
            key=lambda r: (len(r.id), r.id),
        )

    def _cache_path(self) -> Path:
        return self.settings.data_dir / STOPS_CACHE_FILE

    async def load_stops(self) -> None:
        path = self._cache_path()
        try:
            if time.time() - path.stat().st_mtime < STOPS_CACHE_MAX_AGE_S:
                raw = json.loads(path.read_text())
                self.stops = {k: (v[0], v[1], v[2]) for k, v in raw.items()}
                log.info("tfl: %d stops from cache", len(self.stops))
                return
        except (OSError, ValueError, IndexError):
            pass
        stops: StopCoords = {}
        for page in range(1, STOP_PAGES_MAX + 1):
            data = await self._get("/StopPoint/Mode/bus", {"page": page})
            points = data.get("stopPoints") or []
            for sp in points:
                sid, lat, lon = sp.get("naptanId") or sp.get("id"), sp.get("lat"), sp.get("lon")
                if sid and lat is not None and lon is not None:
                    stops[str(sid)] = (float(lon), float(lat), str(sp.get("commonName") or ""))
            total, size = int(data.get("total") or 0), int(data.get("pageSize") or len(points) or 1)
            if not points or page * size >= total:
                break
        self.stops = stops
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({k: list(v) for k, v in stops.items()}))
        except OSError as e:
            log.warning("tfl: stop cache not written (%s)", type(e).__name__)
        log.info("tfl: %d stops loaded", len(stops))

    # ---------- polling ----------
    async def poll_once(self) -> FleetSnapshot:
        ids = [r.id for r in self.routes]
        latencies: list[float] = []
        ts = _now_iso()
        for i in range(0, len(ids), ARRIVALS_BATCH):
            batch = ids[i : i + ARRIVALS_BATCH]
            t0 = time.perf_counter()
            try:
                preds = await self._get(f"/Line/{','.join(batch)}/Arrivals")
            except (httpx.HTTPError, ValueError) as e:
                # Keep the last known buses for these routes; one bad batch never empties the map.
                log.warning("tfl: arrivals batch failed (%s)", type(e).__name__)
                continue
            latencies.append((time.perf_counter() - t0) * 1000)
            vehicles = vehicles_from_arrivals(preds if isinstance(preds, list) else [], self.stops, ts)
            for rid in batch:
                self._by_route[rid] = []
            for v in vehicles:
                self._by_route.setdefault(v.route, []).append(v)
        seen: dict[str, Vehicle] = {}
        for vs in self._by_route.values():
            for v in vs:
                if v.id not in seen or v.eta_s < seen[v.id].eta_s:
                    seen[v.id] = v
        self.snapshot = FleetSnapshot(
            ts=_now_iso(),
            vehicles=sorted(seen.values(), key=lambda v: (v.route, v.id)),
            routes=len({v.route for v in seen.values()}),
            latency_ms=round(sum(latencies) / len(latencies)) if latencies else 0,
        )
        return self.snapshot

    async def run(self, on_snapshot: SnapshotFn) -> None:
        """Lifespan task: never raises except on cancellation."""
        while True:
            started = time.monotonic()
            try:
                if not self.routes:
                    await self.load_routes()
                if not self.stops:
                    await self.load_stops()
                snap = await self.poll_once()
                await on_snapshot(snap)
                wait = max(0.0, self.settings.fleet_poll_s - (time.monotonic() - started))
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001 - the poller must outlive any upstream failure
                log.warning("tfl: poll failed (%s)", type(e).__name__)
                wait = RETRY_AFTER_ERROR_S
            await asyncio.sleep(wait)

    # ---------- on demand ----------
    async def route_detail(self, route_id: str) -> RouteDetail | None:
        if route_id in self._route_cache:
            return self._route_cache[route_id]
        directions: list[RouteDirection] = []
        for d in DIRECTIONS:
            try:
                data = await self._get(f"/Line/{route_id}/Route/Sequence/{d}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    continue
                raise
            directions.append(_direction(d, data))
        if not directions:
            return None
        detail = RouteDetail(id=route_id, directions=directions)
        self._route_cache[route_id] = detail
        return detail

    async def pairings(self) -> list[Pairing]:
        """Stand-in: pair real incidents with live buses, stable for 30 min.

        Prefers the latest bus_front + bus_nearside runs, then bus, then city.
        """
        incidents: list = []
        for group in PAIRING_MODE_GROUPS:
            incidents = [i for m in group for i in await self.store.list_incidents(m) if not i.fixture]
            if incidents:
                break
        live = {v.id: v for v in self.snapshot.vehicles}
        if not live:
            return []
        now = time.monotonic()
        ids = sorted(live)
        used: set[str] = set()
        out: list[Pairing] = []
        for inc in incidents:
            vid, expires, stop_name, towards = self._pairs.get(inc.id, ("", 0.0, "", ""))
            if vid not in live or expires < now or vid in used:
                start = int(hashlib.sha1(inc.id.encode()).hexdigest(), 16) % len(ids)
                ring = ids[start:] + ids[:start]  # deterministic start, skip buses already paired
                vid = next((x for x in ring if x not in used), "")
                if not vid:
                    break
                stop_name, towards = live[vid].next_stop_name, live[vid].towards
                self._pairs[inc.id] = (vid, now + PAIRING_TTL_S, stop_name, towards)
            used.add(vid)
            out.append(
                Pairing(
                    incident_id=inc.id,
                    vehicle_id=vid,
                    route=live[vid].route,
                    risk=inc.risk,
                    came_true=inc.came_true,
                    mode=inc.mode,
                    stop_name=stop_name,
                    towards=towards,
                )
            )
        return sorted(out, key=lambda p: -p.risk)


def _direction(d: str, data: dict[str, Any]) -> RouteDirection:
    coords: list[list[float]] = []
    for ls in data.get("lineStrings") or []:
        try:
            parsed = json.loads(ls) if isinstance(ls, str) else ls
        except ValueError:
            continue
        # lineStrings are JSON text of [[[lon, lat], ...]] (one or more parts)
        for part in parsed:
            coords.extend([[float(p[0]), float(p[1])] for p in part if len(p) >= 2])
    stops: list[RouteStop] = []
    seqs = data.get("stopPointSequences") or []
    if seqs:
        for sp in seqs[0].get("stopPoint") or []:
            if sp.get("lat") is not None and sp.get("lon") is not None:
                stops.append(
                    RouteStop(id=str(sp.get("id") or ""), name=str(sp.get("name") or ""),
                              lon=float(sp["lon"]), lat=float(sp["lat"]))
                )
    return RouteDirection(dir="inbound" if d == "inbound" else "outbound", coords=coords, stops=stops)
