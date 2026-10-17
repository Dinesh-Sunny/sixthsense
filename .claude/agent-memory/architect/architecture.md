# Architecture map (mapped at commit 357c01d, 2026-10-17)
Pre-v1 (being replaced by plan .claude/plans/sixthsense-v1.md):
- pipeline/run.py - watch/verify/foresee/selfcheck/store; hand-rolled IoU tracker + closing_gap (lines 59-123)
- pipeline/vss.py - urllib VSS client, team_config() parses /config/*.config, first() key lookups
- pipeline/models.py - raw HTTP to Cosmos3-Reason, YOLO11, W&B inference; optional weave.op; parse_json
- pipeline/modes.py - MODES (road/street/city): cameras, queries, verify kind, role, horizon
- app/main.py - stdlib http.server: /api/incidents, /api/metrics, /api/alerts, /api/ask, /clip Range proxy
- deploy.sh - ConfigMap code + Secret + python:3.12-slim Deployment + Ingress /app (rewrite strips /app)
Target v1 layout: backend/src/sixthsense/{settings,contracts,modes,clients/{http,vss,models},tracing,tracking,pipeline,store,weather,main,cli}.py; web/ Next 16 static export (src/app, src/lib/api).
