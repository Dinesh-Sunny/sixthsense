"""`sixthsense run --mode road --limit 3` and `sixthsense probe` (shapes and ok/fail only, never values)."""

import argparse
import asyncio
import json
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from . import tracing
from .main import Resources, open_resources
from .modes import CLI_LIMIT_MAX, MODE_NAMES, MODES
from .pipeline import Candidate, Forecast, execute_run, watch
from .settings import get_settings
from .store import VastStore
from .tracking import EgoDiag, ego_diagnostics


def shape(x: Any, depth: int = 0) -> Any:
    """Keys and types only: probe output is pasted into chats, so no values leave the VM."""
    if depth > 4:
        return "..."
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in list(x.items())[:30]}
    if isinstance(x, list):
        return [shape(x[0], depth + 1), f"len={len(x)}"] if x else []
    return type(x).__name__


async def _step(name: str, fn: Callable[[], Awaitable[Any]]) -> Any:
    t = time.perf_counter()
    try:
        r = await fn()
    except Exception as e:  # noqa: BLE001 - probe reports every failure and keeps going
        print(f"FAIL {name}: {type(e).__name__}")
        return None
    print(f"OK   {name} ({time.perf_counter() - t:.1f}s)")
    return r


async def probe() -> int:
    settings = get_settings()
    report: dict[str, Any] = {}
    traced = await tracing.init_tracing(settings)
    print(f"{'OK  ' if traced else 'SKIP'} weave.init")
    async with open_resources(settings) as res:
        report["store_backend"] = res.store.backend
        await _probe_vss(res, report)
        await _probe_models(res, report)
        if isinstance(res.store, VastStore):
            report["vastdb_types"] = await _step(
                "vastdb type probe", lambda: asyncio.to_thread(res.store.probe_types_sync)
            )
    await tracing.finish_tracing()
    print(json.dumps(report, indent=1))
    return 0


async def _probe_vss(res: Resources, report: dict[str, Any]) -> None:
    v = res.vss
    await _step("vss login", v.login_check)
    report["dashboard"] = shape(await _step("vss dashboard", v.dashboard))
    cam = MODES["road"]["cameras"][0]
    found = await _step("vss search road", lambda: v.search(MODES["road"]["queries"][0], cam, 3, 0.1))
    if not found or not found.results:
        return
    hit = found.results[0]
    report["search_hit_fields_set"] = sorted(hit.model_fields_set)
    det = await _step("vss detections", lambda: v.detections(hit.source))
    report["detections"] = {"frames": len(det.frames), "fps": det.fps} if det else None
    if hit.original_video:
        segs = await _step("vss segments", lambda: v.segments(hit.original_video or ""))
        report["segments"] = len(segs.segments) if segs else None
    clip = await _step("vss clip bytes", lambda: v.clip_bytes(hit.source))
    report["clip_kb"] = len(clip) // 1024 if clip else None
    if clip:
        m = res.models
        reply = await _step("cosmos on clip", lambda: m.cosmos("Describe this clip in one sentence.", clip, 120))
        report["cosmos_reply_chars"] = len(reply) if reply else None
        yolo = await _step("yolo on clip", lambda: m.yolo(clip))
        report["yolo_frames"] = len(yolo.frames) if yolo else None


async def _probe_models(res: Resources, report: dict[str, Any]) -> None:
    m = res.models
    report["cosmos_model_resolved"] = bool(await _step("cosmos /v1/models", m.cosmos_model))
    models = await _step("W&B models", m.llm_models)
    report["wandb_llm_model_available"] = bool(models and res.settings.llm_model in models)
    report["structured_output"] = {
        "cosmos": await _step("cosmos json_schema", lambda: m.supports_schema("cosmos", Forecast)),
        "wandb": await _step("W&B json_schema", lambda: m.supports_schema("llm", Forecast)),
    }


async def run(mode: str, limit: int) -> int:
    settings = get_settings()
    await tracing.init_tracing(settings)
    run_id = f"{mode}-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    async with open_resources(settings) as res:
        print(f"store: {res.store.backend}, run: {run_id}")
        metrics = await execute_run(res.deps, res.store, mode, limit, run_id)  # type: ignore[arg-type]
    await tracing.finish_tracing()
    print(metrics.model_dump_json(indent=1))
    return 0


def _hazard_for(mode: str, query: str) -> str:
    cfg = MODES[mode]  # type: ignore[index]
    types = cfg.get("hazard_types", ())
    queries = cfg["queries"]
    # the bus-view query lists are written in the same order as their hazard sets
    return types[queries.index(query)] if len(types) == len(queries) and query in queries else query


def _diag_line(n: int, hazard: str, cand: Candidate, d: EgoDiag | None, note: str = "") -> str:
    head = f"[{n:02d}] {hazard[:26]:<26} | {cand.hit.source.rsplit('/', 1)[-1][-34:]:<34}"
    if d is None:
        return f"{head} | {note}"
    ttc = "-" if d.ttc_s is None else f"{d.ttc_s:.1f}s"
    return (
        f"{head} | {d.label:<10} h {d.start_h:5.1%}->{d.end_h:5.1%} area0 {d.start_area:5.1%}"
        f" | growth {d.growth:4.2f}x {d.span_s:4.2f}s {d.span_frames:3d}fr/{d.frames:3d}"
        f" | conf {d.mean_conf:.2f} | ttc {ttc:>6} | lane {'yes' if d.in_lane else 'no '}"
        f" | {d.reason}{f' ({d.rule})' if d.rule else ''}"
    )


async def gate_debug(mode: str, limit: int) -> int:
    """Search + detections only (no model calls): show why each candidate passes or fails the ego gate."""
    settings = get_settings()
    cfg = MODES[mode]  # type: ignore[index]
    if cfg["verify"] != "ego":
        print(f"{mode} uses the {cfg['verify']} check, not the ego gate")
        return 2
    async with open_resources(settings) as res:
        cands = (await watch(res.deps, mode, settings.per_query))[:limit]  # type: ignore[arg-type]
        sem = asyncio.Semaphore(settings.gpu_concurrency)

        async def one(c: Candidate) -> Any:
            async with sem:
                try:
                    return await res.vss.detections(c.hit.source)
                except Exception as e:  # noqa: BLE001 - report and keep going
                    return e

        dets = await asyncio.gather(*(one(c) for c in cands))
    reasons: dict[str, int] = {}
    for n, (c, det) in enumerate(zip(cands, dets, strict=True), 1):
        hazard = _hazard_for(mode, c.query)
        if isinstance(det, Exception) or det is None or not det.frames:
            why = f"detections error ({type(det).__name__})" if isinstance(det, Exception) else "no detections"
            print(_diag_line(n, hazard, c, None, why))
            reasons[why] = reasons.get(why, 0) + 1
            continue
        diags = ego_diagnostics(det, cfg["classes"], cfg["view"])
        top = diags[0] if diags else None
        print(_diag_line(n, hazard, c, top, "" if top else "no tracks"))
        key = (top.reason.split(" ")[0] if top else "no tracks")
        reasons[key] = reasons.get(key, 0) + 1
    print("summary: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sixthsense")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="watch -> verify -> foresee -> self-check -> store")
    r.add_argument("--mode", default="road", choices=MODE_NAMES)
    r.add_argument("--limit", type=int, default=3, choices=range(1, CLI_LIMIT_MAX + 1), metavar="N")
    sub.add_parser("probe", help="check every upstream; prints shapes and ok/fail, never values")
    g = sub.add_parser("gate-debug", help="ego gate numbers per candidate (search + detections, no models)")
    g.add_argument("--mode", default="bus_front", choices=[m for m in MODE_NAMES if MODES[m]["verify"] == "ego"])
    g.add_argument("--limit", type=int, default=40, choices=range(1, CLI_LIMIT_MAX + 1), metavar="N")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if a.cmd == "run":
        return asyncio.run(run(a.mode, a.limit))
    if a.cmd == "gate-debug":
        return asyncio.run(gate_debug(a.mode, a.limit))
    return asyncio.run(probe())


if __name__ == "__main__":
    sys.exit(main())
