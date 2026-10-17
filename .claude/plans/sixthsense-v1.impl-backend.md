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

## v3 bus mode
- [x] mode "bus" (city+street cameras, 8 hazard queries, round-robin + near-dup skip), FORESEE_BUS prompt with fixed type set (snapped via difflib), pairings add stop_name/towards and prefer latest bus run then city. 77 tests.

## v3 bus views
- [x] modes bus_front (pie_cam-3) / bus_nearside (nyc_bike_gopro-1), verify="ego": tracking.closing_on_us (ByteTrack per class group, lane zone per view, height growth >=1.35x in <=2 s or TTC proxy dt/(s-1) <=3 s over >=0.5 s), plain verify_note; per-view prompts + hazard sets; Incident.camera_view (+ web types.ts field only); CLI --limit <=60 (API stays 10); pairings prefer bus_front+bus_nearside > bus > city; metrics ordered bus views first. 85 tests.
- Ego gap_series is empty (no car-length gap to chart).

## v3.1 ego tightening + posters
- [x] Ego gate after real runs: nearside drops camera-owned boxes (bottom 12% band or >45% frame width); tracks need start area >=1.5% and mean conf >=0.4; growth over >=0.8 s and >=8 frames, trailing-median-5 heights; pass = growth >=1.6x AND (TTC <=3 s OR box >=25% frame height). Note cites the passing test.
- [x] Hazard-matched note: pedestrian/cyclist/scooter/crowd hazards cite the matching class track; none passing -> ruled out.
- [x] Prompts ask for a CHANGE (not "continues ..."); nearside prompt says the handlebars/front wheel are the camera; bus-view judges answer partly for restated predictions (+ regex backstop capping yes -> partly).
- [x] GET /api/poster?source=&t=1 (media.py, cv2 headless, 960 px, q82, LRU 512, Semaphore(2), Cache-Control 1 day, 404 unreadable). 98 tests.

## v3.2 gate data
- [x] `sixthsense gate-debug --mode bus_front|bus_nearside --limit N`: search + detections only, one line per candidate (hazard, best track class, start->end height %, start area, growth/span/frames, conf, ttc, lane, rejecting rule) + summary counts.
- [x] Removed the regex yes->partly cap (judge instruction kept). Hazard match falls back to the best passing track with "(closest road user: <class>)".
- [x] Provisional gate: growth >=1.4x over >=0.6 s and >=6 frames, start area >=0.8%, mean conf >=0.35; nearside bottom-band mask kept. 99 tests.

## v3.3 gate from data
- [x] Class gates (person/bicycle/motorcycle >=1.25x, vehicles >=1.4x, inclusive); person span floor 0.5 s / 12 frames (others 0.6 s / 6); growth on a rising window (peak since the window minimum) and the note/debug show that window's start->end heights; front-camera lane-entry rule for person/bicycle (outside lane -> inside or within 5% of its edge, moved >=5% of width, <=2 s); gate-debug prints the passing rule (growth/ttc/lane-entry). 102 tests.
