---
name: gpu-model-smoke-test
description: >-
  Minimal real inference against Cosmos3-Reason, YOLO11, Embed1 (256-dim), and optional Canary-1B
  using /config/<team>.config for auth. Use when health is green but reasoning,
  embeddings, detections, or ASR demos still fail.
---

# GPU: model smoke test (vss2)

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

See also the full model guide: [gpu/README.md](../README.md).

## Cosmos3-Reason — chat/completions

```bash
COSMOS3_REASON_MODEL=$(
  curl -fsS "${AUTH[@]}" "$COSMOS3_REASON_URL/v1/models" |
    python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"
)
curl -s -X POST "${COSMOS3_REASON_URL}/v1/chat/completions" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${COSMOS3_REASON_MODEL}\",
    \"messages\": [{\"role\":\"user\",\"content\":\"Reply with the single word: OK\"}],
    \"max_tokens\": 16, \"temperature\": 0
  }"
```

Expect `choices[0].message.content`.

## YOLO11 — infer

Health first (this server has **no** `/v1/models`): `GET $YOLO_URL/healthz` → `ok` + `model_loaded`.

```bash
B64=$(base64 -i clip.mp4 | tr -d '\n')
curl -s -X POST "${YOLO_URL}/v1/infer" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"video_base64\":\"$B64\",\"filename\":\"clip.mp4\",\"include_frames\":true}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin);print('ok=',d.get('perception_ok') or d.get('ok'),'classes=',d.get('object_classes'))"
```

## Embed1 — embeddings (must be 256-dim)

```bash
COSMOS_EMBED1_MODEL=$(
  curl -fsS "${AUTH[@]}" "$COSMOS_EMBED1_URL/v1/models" |
    python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])"
)
curl -s -X POST "${COSMOS_EMBED1_URL}/v1/embeddings" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"input\":\"a person walking\",\"model\":\"${COSMOS_EMBED1_MODEL}\",\"request_type\":\"query\",\"encoding_format\":\"float\"}" \
  | python3 -c "import sys,json;d=json.load(sys.stdin)['data'][0]['embedding'];print('dim=',len(d))"
```

Assert `dim= 256`.

## Canary-1B — ASR (optional; not in default pipeline)

Health: `/v1/health/ready` + `/v1/health/live` only — **`/v1/models` is 404 and is not a failure**.

```bash
curl -s "${AUTH[@]}" "$CANARY_1B_URL/v1/health/ready"
curl -s -X POST "${CANARY_1B_URL}/v1/audio/transcriptions" \
  "${AUTH[@]}" \
  -F "file=@clip_audio.wav" \
  -F "model=nvidia/canary-1b"
```

## Failures

| Symptom | Likely cause |
|---------|--------------|
| Cosmos3-Reason empty `content` | overloaded / rejected prompt |
| Embed1 dim ≠ 256 | wrong model → breaks search / VastDB |
| YOLO `/healthz` not ok | model not loaded / GPU issue |
| YOLO 404 on `/v1/infer` | wrong URL |
| Canary `/v1/models` 404 | **expected** — use ready/live instead |
| 401/403 | missing/wrong `GPU_BEARER_TOKEN` |

## Agent instructions

1. Source the single `/config/*.config` team file; if missing or bearer is empty, ask the user. Never search `team-configs/` or copy credentials into the repo.
2. Run health with the **per-model** paths in `gpu-model-health` before smoke tests.
3. Assert Embed1 dim == 256.
4. For Canary, never require `/v1/models`; do not claim it is part of default ingest.
