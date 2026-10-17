# Request: SixthSense v1 - library-first rebuild (tier L, debate R1 only - deadline 16:30 today)

## Goal
Rebuild SixthSense as a clean, library-first codebase: Python backend (FastAPI) + Next.js 16 static frontend,
implementing the APPROVED wireframes. No hand-rolled code where a library API exists. Architecture must be the
thin slice of a design that scales to 100k DAU (target documented in docs/architecture.md, not all built today).

## Decided with the user (do not re-ask)
- Frontend: Next.js 16 + React + shadcn/ui + Tailwind + TanStack Query, `output: 'export'` static build,
  served by FastAPI StaticFiles. Built in CI/workspace (no Node on the lab VM).
- Scope today: thin vertical slice + documented 100k-DAU target (Redis cache, arq workers, DataEngine event
  triggers, CDN, HPA) in docs/architecture.md + README.
- Deploy: team K8s namespace, public image python:3.12-slim, NO image build. Pod downloads our release
  (GitHub tarball, verified reachable) + pip installs from PyPI (verified reachable) at start. Ingress /app.
- Design: docs/design/DESIGN.md (voice + rules), docs/design/tokens.json, docs/design/wireframes/*.dc.html
  + ss.css (Hark-inspired; sky atmosphere follows live city weather: wx-clear/cloudy/rain/night).
- Copy voice: Airbnb-style simple/precise/helpful/human. Real data only; fixtures labelled Sample.

## Replace hand-rolled code with libraries
- pipeline/run.py tracker (_iou/_tracks/closing_gap) -> supervision ByteTrack + sv.Detections + anchors.
- pipeline/vss.py urllib client -> httpx.AsyncClient + tenacity + Pydantic models of VSS responses.
- pipeline/models.py raw HTTP -> openai.AsyncOpenAI (Cosmos3-Reason NIM + W&B inference base_url) + weave.op;
  structured outputs via Pydantic.
- app/main.py http.server -> FastAPI (lifespan client, pydantic-settings, StreamingResponse Range proxy).
- incidents.json -> VastDB `incidents` table via vastdb SDK (JSON fallback flag).

## Real API facts (from probe on the VM - see fixtures shapes in pipeline/probe.py output)
- VSS /api/v1: POST /auth/login -> access_token; POST /search (llm_top_n >= 1 required!) results[] keys:
  source, original_video, segment_number, total_segments, segment_start_sec, segment_end_sec,
  reasoning_content, camera_id, location, object_classes, similarity_score (~0.2 typical).
- GET /tools/segments?original_video= -> {original_video,total,segments:[...same keys]}.
- GET /videos/detections?source= -> {source, fps:30, frame_count:150, video_shape:[1080,1920],
  frames:[{frame_index,time_sec,detections:[{label,confidence,bbox:[x1,y1,x2,y2]}]}]}; 404 = none.
- GET /videos/stream?source=&token= (Range ok). Cosmos3-Reason: OpenAI chat with video_url data URL, ~2.6 s.
- W&B inference models include meta-llama/Llama-3.3-70B-Instruct, openai/gpt-oss-120b.
- 13 cameras, 3,537 segments. Modes: road (i24_cam-1), city (nyc_streets_cam-1/2, sf_streets_cam-1/2/4/5),
  street (neighborhood_cam-1).

## Stack outlines (read the relevant one before deciding APIs)
.claude/stacks/lib/: fastapi.yaml, supervision.yaml, weave.yaml, vastdb.yaml, tanstack-query.yaml,
arq-httpx.yaml, next.yaml, react.yaml, shadcn-ui.yaml, uv.yaml, ruff.yaml, pytest.yaml, mypy.yaml.

## Constraints
- Python deps managed with uv (pyproject.toml + uv.lock); web with pnpm.
- Never print/commit /config values or tokens. Stay in team namespace.
- Plan must be implementable by ~15:00 with the slice; mark everything else `later`.
