# sixthsense-v1 backend implementation status (13:4x)
- [x] scaffold: backend/ uv package `sixthsense` (py3.12), deps pinned; opencv-python/matplotlib/av excluded (lock has headless only)
- [x] settings, contracts, clients (http: VSSAuth async_auth_flow + retry; vss models; models: AsyncOpenAI Cosmos/W&B + YOLO), tracing (drop_media client-level, key-gated, weave.thread), store (JsonStore + VastStore behind CapacityLimiter(1), runs table, latest run per mode, Sample seed), weather (Open-Meteo + clock fallback), main (lifespan, /api, health, static mount last), runner (single-flight, cooldown, RUNS_ENABLED)
- [x] tracking: per-class-group ByteTrackTracker, at-least-one-vehicle pairs, gap_series. FINDING: trackers 2.6.1 births tracks only from boxes >= high_conf_det_threshold (default 0.6), so HIGH_CONF_DET=0.4 is set alongside TRACK_ACTIVATION=0.4
- [x] pipeline async port (gather + Semaphore, asyncio.timeout per step), cli `sixthsense run|probe`
- [x] tests: 69 passing (socket guard, MockTransport), ruff clean, `uv lock --check` ok
- [x] deploy/bootstrap.py (codeload by SHA, uv via pip --target, uv sync --locked --no-dev --no-editable, uvicorn --factory), deploy.sh <sha> + --cutover/--rollback, deploy/legacy.sh (old script), scripts/release.sh (DRY_RUN=1 supported)
- Verified locally: dist tree -> `uv sync --locked --no-dev --no-editable` with py3.12 -> imports cv2/trackers/vastdb/weave OK; uvicorn serves web/out + /api. Venv is ~770 MB (not 372).
- Not done: golden check old vs new closing_gap on real road detections (needs VM data); EvaluationLogger (tier 2); OpenAPI snapshot (deferred, d2); VastStore has no unit test (probe covers it live); AGENTS.md dist-branch note; live probe/run on VM.

## v2 buses (backend)
- [x] tfl.py (TfL client w/ User-Agent + optional app_key, paced 40 req/min unkeyed, stop cache in data_dir, route geometry cache, stand-in pairings 30 min), fleet poller in lifespan, python-socketio 5.16.1 `vehicles` emit, /api/vehicles|routes|routes/{id}|fleet/pairings|map-config, uvicorn entry `sixthsense.main:create_asgi`, deploy.sh loads ~/.config/sixthsense.env + MAPBOX_TOKEN/TFL_APP_KEY. Tests: 73 passing.
- Note: unkeyed full sweep of ~700 routes = ~35 batches at 1.5 s = ~55 s, so updates land every ~55 s without TFL_APP_KEY.
