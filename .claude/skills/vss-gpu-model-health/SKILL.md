---
name: gpu-model-health
description: >-
  Check liveness/readiness of VSS GPU models using the paths that each NIM actually
  exposes (Cosmos3-Reason/Embed1: /v1/models + /v1/health/*; YOLO: /healthz; Canary:
  /v1/health/ready|live only). Auth config: /config/<team>.config.
---

# GPU: model health (vss2)

Config (required): the single `/config/*.config` team file. If missing or its `GPU_BEARER_TOKEN` is empty, ask the user to fix it. Never search the repo's `team-configs/`.

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
TEAM_CONFIG="${TEAM_CONFIGS[0]}"
set -a && source "$TEAM_CONFIG" && set +a
GPU_HOST=166.19.38.112
COSMOS3_REASON_URL=http://${GPU_HOST}:8001
YOLO_URL=http://${GPU_HOST}:8002
COSMOS_EMBED1_URL=http://${GPU_HOST}:8003
CANARY_1B_URL=http://${GPU_HOST}:8004
AUTH=(-H "Authorization: Bearer ${GPU_BEARER_TOKEN}")
```

**Do not** probe the same paths on every model. These NIMs differ — use the matrix below (verified on the hackathon host).

## Per-model health matrix (source of truth)

| Model | URL env | Health checks that work | Do **not** use (404 here) |
|-------|---------|-------------------------|---------------------------|
| **Cosmos3-Reason** | `$COSMOS3_REASON_URL` | `GET /v1/models` → 200; `GET /v1/health/ready` → 200; `GET /v1/health/live` → 200 | `/v1/health`, `/health` |
| **YOLO11** | `$YOLO_URL` | `GET /healthz` → 200 (`ok`, `model_loaded`); optional `GET /openapi.json` / `/docs` | `/v1/models`, `/v1/health/ready`, `/v1/health/live` |
| **Embed1** | `$COSMOS_EMBED1_URL` | `GET /v1/models` → 200; `GET /v1/health/ready` → 200; `GET /v1/health/live` → 200 | `/v1/health`, `/health` |
| **Canary-1B** | `$CANARY_1B_URL` | `GET /v1/health/ready` → 200; `GET /v1/health/live` → 200; optional `GET /openapi.json` / `/docs` | `/v1/models`, `/healthz`, `/v1/health` |

A **404 on an unsupported path is not a failure** for that model. Only fail health if the **supported** checks above are non-200 (or connection error).

## Commands (copy/paste)

### Cosmos3-Reason + Embed1 (OpenAI/NIM-style)

```bash
for ep in "$COSMOS3_REASON_URL" "$COSMOS_EMBED1_URL"; do
  echo "== $ep =="
  curl -s -o /dev/null -w "models:%{http_code} " "${AUTH[@]}" "$ep/v1/models"
  curl -s -o /dev/null -w "ready:%{http_code} " "${AUTH[@]}" "$ep/v1/health/ready"
  curl -s -o /dev/null -w "live:%{http_code}\n" "${AUTH[@]}" "$ep/v1/health/live"
done
# Expect all three codes = 200 for each.
curl -s "${AUTH[@]}" "$COSMOS3_REASON_URL/v1/models" | python3 -m json.tool   # id ~ cosmos3-reason
curl -s "${AUTH[@]}" "$COSMOS_EMBED1_URL/v1/models" | python3 -m json.tool    # id ~ cosmos-embed1
```

### YOLO11 (custom FastAPI — `/healthz` only)

```bash
curl -s "${AUTH[@]}" "$YOLO_URL/healthz" | python3 -m json.tool
# Expect: "ok": true, "model_loaded": true, "cuda_available": true
# Infer route exists (405 on GET is fine):
curl -s -o /dev/null -w "infer_GET:%{http_code}\n" "${AUTH[@]}" "$YOLO_URL/v1/infer"   # expect 405
```

### Canary-1B (Riva HTTP — ready/live only; no `/v1/models`)

```bash
curl -s "${AUTH[@]}" "$CANARY_1B_URL/v1/health/ready" | python3 -m json.tool   # status ready
curl -s "${AUTH[@]}" "$CANARY_1B_URL/v1/health/live"  | python3 -m json.tool   # status live
# Optional API surface:
curl -s -o /dev/null -w "openapi:%{http_code} docs:%{http_code}\n" \
  "${AUTH[@]}" "$CANARY_1B_URL/openapi.json" "${AUTH[@]}" "$CANARY_1B_URL/docs"
# Do NOT treat /v1/models 404 as down.
```

## Pass / fail rules

| Model | Pass when |
|-------|-----------|
| Cosmos3-Reason / Embed1 | `/v1/models` + `/v1/health/ready` + `/v1/health/live` all 200 |
| YOLO | `/healthz` 200 and JSON `ok==true` and `model_loaded==true` |
| Canary | `/v1/health/ready` + `/v1/health/live` both 200 |

If health passes but pipeline still fails → [model-smoke-test](../model-smoke-test/SKILL.md).

## Agent instructions

1. Source the single `/config/*.config` team file and always send its bearer token; ask the user if missing. Never copy credentials into the repo.
2. Use **only** the supported paths per model from the matrix — never require `/v1/models` on YOLO or Canary.
3. Report per model: which checks ran, HTTP codes, and pass/fail by the rules above.
4. Never invent hosts/ports; never print the bearer token.
