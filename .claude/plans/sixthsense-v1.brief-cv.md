## supervision brief (supervision 0.31.0 + trackers 2.6.1 + opencv-python-headless 5.0.0.93)
Verified 2026-10-17 from the installed wheels' source and a scratch uv project (py3.13, uv 0.11.32, numpy 2.5.4): 150 frames x 2 boxes track in ~15 ms.

### APIs to use (signature + ref)
- [must] `from trackers import ByteTrackTracker`; kwargs (via `inspect.signature`): `lost_track_buffer=30, frame_rate=30.0, track_activation_threshold=0.7, minimum_consecutive_frames=2, minimum_iou_threshold=0.1, high_conf_det_threshold=0.6, state_estimator_class=XYXYStateEstimator, iou=None`. Plan's "confirm kwarg names" is closed: it is `minimum_iou_threshold`. trackers/core/bytetrack/tracker.py, trackers.roboflow.com/develop/api/trackers/
- [must] `tracked = tracker.update(detections)` -> `sv.Detections`; once per frame in time order, INCLUDING empty frames (a track survives a gap: id 0 before and after an empty frame, verified). Output is `detections[idx]` so `data["class_name"]` survives; row order differs from input; unconfirmed boxes stay `tracker_id == -1` -> `tracked[tracked.tracker_id >= 0]`.
- [must] `track_activation_threshold` default 0.7: a YOLO box with conf < 0.7 NEVER starts a track (verified: conf 0.3 stayed -1 for 150 frames). Set ~0.4 as TRACK_ACTIVATION in `modes.py`, keep other defaults; sanity-check the first real clip (about 1-2 unique ids per vehicle, not 10).
- [must] Fresh `ByteTrackTracker(frame_rate=n_frames/duration_s)` per clip (stateful; ids restart at 0). Key results by `(clip_id, tracker_id)`. Not thread-safe: with TaskGroup+Semaphore each clip owns its tracker. Pure CPU, ms-level: call inline, no `to_thread`.
- [must] `sv.Detections(xyxy=float32 (n,4), confidence=float32, class_id=int64, data={"class_name": np.array(labels)})`; empty frame = `sv.Detections.empty()` (shape (0,4), `data == {}`: read `class_name` only when `len(d)`). Builder drops unknown labels, non-finite values (tracker raises ValueError "xyxy must contain only finite numeric values") and boxes with x2<=x1 or y2<=y1 (no crash, junk ids).
- [must] Filter to vehicle class ids (`np.isin(d.class_id, VEHICLE_IDS)`; COCO car 2, motorcycle 3, bus 5, truck 7; label->id dict in `modes.py`) BEFORE `update`: tracker is class-agnostic, a person box can take a car's id.
- [must] `d.get_anchors_coordinates(sv.Position.CENTER)` -> (n,2); join the pair on `tracker_id` per frame, never row index; gap = centre distance / mean box diagonal (hand-written, no built-in; justified in plan).
- [should] If the detections JSON has per-frame times, pass `update(d, timestamp=t_seconds)` (non-decreasing; first call bootstraps at 1/frame_rate; backward -> skipped + UserWarning, duplicate -> predict skipped). Handles dropped/sampled frames without faking fps. Never pass `frame=` (UserWarning).
- [should] Pin exactly `supervision==0.31.0`, `trackers==2.6.1`, `opencv-python-headless>=4.8,<6`. trackers needs `supervision>=0.26.1`: no conflict. `'ByteTrack' in dir(sv)` is False, so `sv.ByteTrack` fails at import anyway; the TID251 ban is belt-and-braces.

### OpenCV / dependency facts (the headless swap)
- trackers 2.6.1 hard-requires `opencv-python>=4.8.0` (+numpy>=2.0.2, scipy, rich, requests, pydeprecate, supervision) and `import trackers` runs `trackers.io.frames` -> top-level `import cv2`. So cv2 is needed at import; headless provides the same `cv2` module.
- supervision 0.31.0 does NOT depend on opencv (its `supervision/_cv2` shim imports cv2 optionally). It depends on av, matplotlib, pillow, scipy, tqdm, defusedxml, pyyaml, requests.
- [must] Swap works as in plan: `dependencies=[..., "opencv-python-headless>=4.8,<6"]` + `[tool.uv] exclude-dependencies=["opencv-python"]`; `uv lock` + `uv sync` installed only `opencv_python_headless-5.0.0.93`; lock has no `name = "opencv-python"`. `ldd cv2*.so` needs only libz/libstdc++/libm/libgcc/libc (no libGL, no glib): fine on python:3.12-slim; step-0 pod smoke still confirms.
- [should] Also exclude `matplotlib` and `av`: `exclude-dependencies=["opencv-python","matplotlib","av"]` tested - supervision, trackers, tracking, `BoxAnnotator`, `LabelAnnotator`, `Position` all work; site-packages 554 MB -> 372 MB (kept: scipy 89, cv2 73+83, numpy 61 MB). Cuts pod start time (plan risk "~300 MB wheels"). Loses `ColorPalette.from_matplotlib` and av video utils; we use neither.

### Anti-patterns
`sv.ByteTrack` / `update_with_detections` (removed); one tracker shared across clips or concurrent tasks; skipping `update` on empty frames; matching by input row order; `np.array([])` as an empty frame; default activation 0.7 on YOLO scores; tutorials' `track_thresh/track_buffer/match_thresh` kwargs.

## Plan corrections
- [must] Library decisions, supervision row: drop "(confirm activation/IoU kwarg names via help())"; state the verified kwargs and set `track_activation_threshold` explicitly (default starves tracks).
- [must] Test plan, tracking: add "conf 0.5 box gets an id at activation 0.4", "empty frame mid-clip keeps the id", "person overlapping a car does not share its id" (vehicle filter), "NaN / inverted box dropped by builder".
- [should] Risks, wheel size: add `matplotlib`, `av` to `exclude-dependencies` (saves ~180 MB, verified).
- [should] Enforcement: ban `cv2` alongside `supervision`/`trackers` outside `tracking.py` (headless cv2 is importable everywhere); the `sv.ByteTrack` ban can stay but is not load-bearing.

## Opportunities
- [adopt] reliability: sv-tracker-reset -> one tracker per clip, constructed only inside `tracking.closing_gap` (single constructor site).
- [adopt] testing: convention test that `uv.lock` has no `name = "opencv-python"` (prove it bites by adding the package back) + step-0/CI smoke `python -c "import supervision, trackers, cv2"`.
- [later] best-practice: sv-box/label/trace-annotator for "Boxes on" thumbnails (needs decoded frames; detector JSON has none) and sv-polygonzone lanes.
- [later] perf: `iou=GIoU()`/`DIoU()` or `OCSORTTracker`/`BoTSORTTracker` only if ByteTrack id churn shows on real CCTV.

## Proposed rules
- `backend.md`: supervision/trackers/cv2 imported only in `tracking.py` - guard: ruff TID251 + per-file-ignore, `test_conventions.py` bite fixture.
- `backend.md`: lockfile has only `opencv-python-headless` - guard: convention test reading `uv.lock`.
- `backend.md`: one `ByteTrackTracker` per clip - guard: choke point (single constructor call) + test that ids restart across two clips.

## Outline updates
- lib sv-trackers-install: replace "supervision hard dependency not stated" with: trackers 2.6.1 requires supervision>=0.26.1, opencv-python>=4.8.0, numpy>=2.0.2, scipy, rich, requests, pydeprecate (extras detection/tune/mask); `import trackers` imports cv2; headless works via uv `exclude-dependencies=["opencv-python"]` (lock+sync verified). supervision 0.31.0 requires av, defusedxml, matplotlib, numpy, pillow, pydeprecate, pyyaml, requests, scipy, tqdm; no opencv.
- sv-bytetrack-params: kwarg is `minimum_iou_threshold` in 2.6.1 (full list above); activation gates track creation only; `high_conf_det_threshold` splits the 2-stage match; `lost_track_buffer` counts 30-fps frames, scaled by `frame_rate`.
- sv-bytetrack-update: add `timestamp=` semantics; empty result has no `data` keys; tracks persist across empty frames.
- sv-install: excluding matplotlib+av via uv still imports supervision and annotators; saves ~180 MB.
- Usage: sv-detections-ctor/-empty, sv-filter-mask, sv-anchors, sv-pair-distance, sv-trackers-install, sv-bytetrack-params/-update, sv-tracker-reset -> planned (`backend/src/sixthsense/tracking.py`); annotators and polygonzone -> later.
