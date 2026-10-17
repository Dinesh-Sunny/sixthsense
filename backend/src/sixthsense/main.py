"""FastAPI app: lifespan-owned clients, /api routes, health, static web export mounted last.

Run: `uvicorn --factory sixthsense.main:create_app`. Behind Ingress `/app(/|$)(.*)` the prefix is
stripped before it reaches us, so routes are root-relative.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

import httpx
import socketio
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from . import tracing
from .clients.http import HttpClient, gpu_client, public_client, tfl_client, vss_client
from .clients.models import ModelClients, UpstreamError
from .clients.vss import VSSClient
from .contracts import (
    Alert,
    AlertIn,
    AskIn,
    AskOut,
    FleetSnapshot,
    Health,
    Incident,
    MapConfig,
    ModeMetrics,
    Pairing,
    RouteDetail,
    RouteSummary,
    RunIn,
    RunStatus,
    Weather,
)
from .modes import DISCORD_MAX_CHARS, Mode
from .pipeline import Deps
from .runner import RunManager, RunsDisabled
from .settings import Settings, get_settings
from .store import IncidentStore, open_store
from .tfl import Fleet, valid_route_id
from .weather import WeatherService

log = logging.getLogger("sixthsense")
READY_CACHE_S = 10.0
STORE_PING_TIMEOUT_S = 2.0
VSS_READY_TIMEOUT_S = 5.0
PASS_THROUGH_STATUSES = {200, 206, 304, 404, 416}
CLIP_HEADERS = ("content-type", "content-length", "content-range", "accept-ranges", "etag", "last-modified")
UPSTREAM_MSG = "Upstream service unavailable"
SNAPSHOT_EVENT = "vehicles"
SOCKETIO_PATH = "socket.io"


@dataclass
class Transports:
    """Test seam: MockTransport per upstream (VSS, GPU, public internet)."""

    vss: httpx.AsyncBaseTransport | None = None
    gpu: httpx.AsyncBaseTransport | None = None
    public: httpx.AsyncBaseTransport | None = None
    tfl: httpx.AsyncBaseTransport | None = None


@dataclass
class Resources:
    settings: Settings
    vss: VSSClient
    models: ModelClients
    store: IncidentStore
    weather: WeatherService
    public: HttpClient
    deps: Deps
    fleet: Fleet


@asynccontextmanager
async def open_resources(
    settings: Settings, transports: Transports | None = None, models: ModelClients | None = None
) -> AsyncIterator[Resources]:
    """Every long-lived client, opened once and closed on exit. Shared by the app and the CLI."""
    t = transports or Transports()
    async with (
        vss_client(settings, t.vss) as vss_http,
        gpu_client(settings, t.gpu) as gpu_http,
        public_client(t.public) as public_http,
        tfl_client(settings, t.tfl) as tfl_http,
    ):
        vss = VSSClient(vss_http)
        mc = models or ModelClients(settings, gpu_http)
        store = await open_store(settings)
        deps = Deps(settings, vss, mc, asyncio.Semaphore(settings.gpu_concurrency))
        try:
            yield Resources(
                settings,
                vss,
                mc,
                store,
                WeatherService(settings, public_http),
                public_http,
                deps,
                Fleet(settings, tfl_http, store),
            )
        finally:
            await mc.close()
            await store.close()


# ---------- dependencies ----------
def get_res(request: Request) -> Resources:
    return request.state.res


def get_runs(request: Request) -> RunManager:
    return request.state.runs


ResDep = Annotated[Resources, Depends(get_res)]
RunsDep = Annotated[RunManager, Depends(get_runs)]


# ---------- routes ----------
api = APIRouter(prefix="/api")


async def _store_call(coro: Any) -> Any:
    try:
        return await coro
    except Exception as e:  # noqa: BLE001 - UI shows its error state on 503
        log.warning("store error (%s)", type(e).__name__)
        raise HTTPException(503, "Store unavailable") from e


@api.get("/incidents")
async def list_incidents(res: ResDep, mode: Mode | None = None) -> list[Incident]:
    return await _store_call(res.store.list_incidents(mode))


@api.get("/incidents/{incident_id}")
async def get_incident(incident_id: str, res: ResDep) -> Incident:
    inc = await _store_call(res.store.get_incident(incident_id))
    if inc is None:
        raise HTTPException(404, "Incident not found")
    return inc


@api.get("/metrics")
async def get_metrics(res: ResDep) -> list[ModeMetrics]:
    return await _store_call(res.store.metrics())


@api.post("/runs", status_code=202)
async def start_run(body: RunIn, runs: RunsDep) -> RunStatus:
    try:
        status, _started = runs.start(body.mode, body.limit)
    except RunsDisabled as e:
        raise HTTPException(403, "Runs are turned off") from e
    return status


@api.get("/runs/current")
async def current_run(runs: RunsDep) -> RunStatus:
    return runs.current()


def _evidence(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [e if isinstance(e, dict) else {"text": str(e)} for e in raw]


@api.post("/ask")
async def ask(body: AskIn, request: Request, res: ResDep) -> AskOut:
    async with request.state.ask_sem:
        data = await res.vss.ask(body.question, body.original_video)
    return AskOut(answer=str(data.get("answer") or ""), evidence=_evidence(data.get("evidence")))


async def _post_discord(res: Resources, alert: Alert) -> bool:
    hook = res.settings.discord_webhook_url.get_secret_value()
    if not hook:
        return False
    text = f"SixthSense alert - risk {alert.risk} on {alert.camera_id}: {alert.what_next}"
    try:
        r = await res.public.post(
            hook,
            json={"content": text[:DISCORD_MAX_CHARS], "allowed_mentions": {"parse": []}},
            timeout=10.0,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:  # not retried: a duplicate post is worse than a missed one
        log.warning("discord webhook failed (%s)", type(e).__name__)
        return False
    return True


@api.post("/alerts")
async def send_alert(body: AlertIn, request: Request, res: ResDep) -> Alert:
    async with request.state.alert_lock:  # idempotent per incident: one Discord post, ever
        existing = next(
            (a for a in await _store_call(res.store.alerts()) if a.incident_id == body.incident_id), None
        )
        if existing:
            return existing
        inc = await _store_call(res.store.get_incident(body.incident_id))
        if inc is None:
            raise HTTPException(404, "Incident not found")
        # Built from the stored incident: client-sent fields are never trusted.
        alert = Alert(
            id=f"alert-{inc.id}",
            incident_id=inc.id,
            camera_id=inc.camera_id,
            type=inc.type,
            what_next=inc.what_next,
            risk=inc.risk,
            start_s=inc.start_s,
            sent_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        alert.delivered = await _post_discord(res, alert)
        await _store_call(res.store.add_alert(alert))
        return alert


@api.get("/alerts")
async def list_alerts(res: ResDep) -> list[Alert]:
    return await _store_call(res.store.alerts())


def _valid_source(source: str, bucket: str) -> bool:
    prefix = f"s3://{bucket}/" if bucket else "s3://"
    return source.startswith(prefix) and ".." not in source and len(source) < 1024


@api.get("/clip", response_model=None)
async def clip(
    request: Request, res: ResDep, source: Annotated[str, Query(min_length=6)]
) -> StreamingResponse:
    if not _valid_source(source, res.settings.clip_bucket):
        raise HTTPException(400, "Bad source")
    req = res.vss.stream_request(source, request.headers.get("range"), request.headers.get("if-range"))
    r = await res.vss.http.send(req, stream=True)
    if r.status_code not in PASS_THROUGH_STATUSES:
        await r.aclose()
        raise HTTPException(502, UPSTREAM_MSG)
    headers = {h: r.headers[h] for h in CLIP_HEADERS if h in r.headers}
    return StreamingResponse(
        r.aiter_bytes(), status_code=r.status_code, headers=headers, background=BackgroundTask(r.aclose)
    )


@api.get("/weather")
async def weather(res: ResDep, response: Response) -> Weather:
    response.headers["Cache-Control"] = "public, max-age=600"
    return await res.weather.current()


# ---------- v2: London buses ----------
@api.get("/vehicles")
async def vehicles(res: ResDep) -> FleetSnapshot:
    return res.fleet.snapshot


@api.get("/routes")
async def routes(res: ResDep) -> list[RouteSummary]:
    if not res.fleet.routes and res.settings.fleet_enabled:
        await res.fleet.load_routes()
    return res.fleet.routes


@api.get("/routes/{route_id}")
async def route_detail(route_id: str, res: ResDep) -> RouteDetail:
    rid = route_id.lower()
    if not valid_route_id(rid):
        raise HTTPException(400, "Bad route id")
    detail = await res.fleet.route_detail(rid)
    if detail is None:
        raise HTTPException(404, "Route not found")
    return detail


@api.get("/fleet/pairings")
async def pairings(res: ResDep) -> list[Pairing]:
    return await _store_call(res.fleet.pairings())


@api.get("/map-config")
async def map_config(res: ResDep) -> MapConfig:
    # A Mapbox public (pk.) token is meant for browsers; it still stays out of git.
    return MapConfig(mapbox_token=res.settings.mapbox_token.get_secret_value() or None)


# ---------- health ----------
health = APIRouter()


@health.get("/healthz")
async def healthz() -> Health:
    return Health(ok=True)  # liveness: no I/O


@health.get("/readyz")
async def readyz(request: Request, res: ResDep) -> JSONResponse:
    cache = request.state.ready_cache
    if cache.get("until", 0) > time.monotonic():
        body = cache["body"]
    else:
        vss_ok = res.vss.has_token
        if not vss_ok:
            try:
                async with asyncio.timeout(VSS_READY_TIMEOUT_S):
                    await res.vss.login_check()
                vss_ok = True
            except (TimeoutError, httpx.HTTPError):
                vss_ok = False
        store = res.store.backend
        try:
            async with asyncio.timeout(STORE_PING_TIMEOUT_S):
                await res.store.ping()
        except Exception as e:  # noqa: BLE001 - a store blip must not pull the only replica
            log.warning("readyz: store degraded (%s)", type(e).__name__)
            store = "degraded"
        body = Health(ok=vss_ok, store=store, vss=vss_ok).model_dump()
        cache.update(until=time.monotonic() + READY_CACHE_S, body=body)
    return JSONResponse(body, status_code=200 if body["ok"] else 503)


# ---------- app ----------
def create_app(
    settings: Settings | None = None,
    transports: Transports | None = None,
    models: ModelClients | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    # Same-origin only (default cors). Behind Ingress the browser uses path /app/socket.io.
    sio = socketio.AsyncServer(async_mode="asgi")
    live: dict[str, Fleet] = {}

    @sio.event
    async def connect(sid: str, environ: dict[str, Any], auth: Any = None) -> None:
        if fleet := live.get("fleet"):
            await sio.emit(SNAPSHOT_EVENT, fleet.snapshot.model_dump(mode="json"), to=sid)

    async def broadcast(snap: FleetSnapshot) -> None:
        await sio.emit(SNAPSHOT_EVENT, snap.model_dump(mode="json"))

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[dict[str, Any]]:
        await tracing.init_tracing(settings)
        async with open_resources(settings, transports, models) as res:
            runs = RunManager(settings, res.deps, res.store)
            live["fleet"] = res.fleet
            poller: asyncio.Task[None] | None = None  # strong ref; cancelled on shutdown
            if settings.fleet_enabled:
                poller = asyncio.create_task(res.fleet.run(broadcast), name="fleet-poller")
            try:
                yield {
                    "res": res,
                    "runs": runs,
                    "ask_sem": asyncio.Semaphore(settings.ask_concurrency),
                    "alert_lock": asyncio.Lock(),
                    "ready_cache": {},
                }
            finally:
                if poller is not None:
                    poller.cancel()
                    await asyncio.gather(poller, return_exceptions=True)
                live.clear()
                await runs.shutdown()
        await tracing.finish_tracing()

    app = FastAPI(title="SixthSense", version="1.0.0", lifespan=lifespan)
    app.state.sio = sio

    @app.exception_handler(httpx.HTTPError)
    async def _upstream_http(_: Request, exc: httpx.HTTPError) -> JSONResponse:
        log.warning("upstream error (%s)", type(exc).__name__)
        return JSONResponse({"detail": UPSTREAM_MSG}, status_code=502)

    @app.exception_handler(UpstreamError)
    async def _upstream_model(_: Request, exc: UpstreamError) -> JSONResponse:
        log.warning("model error (%s)", exc)
        return JSONResponse({"detail": UPSTREAM_MSG}, status_code=502)

    app.include_router(health)
    app.include_router(api)
    # Static export last, so it never shadows /api or health. Missing dir = API-only (tests, skeleton).
    if settings.web_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dir, html=True), name="web")
    else:
        log.warning("web_dir %s not found; serving API only", settings.web_dir)
    return app


def create_asgi(settings: Settings | None = None) -> socketio.ASGIApp:
    """Production entry (`uvicorn --factory sixthsense.main:create_asgi`): Socket.IO at /socket.io,
    everything else (and lifespan) goes to the FastAPI app."""
    app = create_app(settings)
    return socketio.ASGIApp(app.state.sio, other_asgi_app=app, socketio_path=SOCKETIO_PATH)
