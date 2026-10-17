---
name: gpu-models
description: >-
  Explain and call the shared VSS GPU models (Cosmos3-Reason, YOLO11, Cosmos Embed1,
  Canary-1B). Load the GPU bearer token from /config/<team>.config. Use for
  health checks, smoke tests, wiring Canary into a custom demo, or debugging empty
  reasoning / embeddings / detections.
---

# GPU models (vss2)

Shared inference endpoints for the hackathon. **Always** load the team config from the VM's absolute `/config/` directory. Do not search this repository's `team-configs/`.

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

If `/config/<team>.config` is missing or has no real `GPU_BEARER_TOKEN`, ask the user to put/fix it there. Do not invent or print the token.

## Quick map

| Model | Env URL | Port | In default pipeline? | Skill follow-ups |
|-------|---------|------|----------------------|------------------|
| Cosmos3-Reason | `$COSMOS3_REASON_URL` | 8001 | Yes — reasoner + backend LLM | [model-health](model-health/SKILL.md), [model-smoke-test](model-smoke-test/SKILL.md) |
| YOLO11 (Ultralytics) | `$YOLO_URL` | 8002 | Yes — detector | same |
| Cosmos Embed1 | `$COSMOS_EMBED1_URL` | 8003 | Yes — embedder + search | same |
| Canary-1B (Riva / NeMo ASR) | `$CANARY_1B_URL` | 8004 | **No** — optional demos | invent with Cursor |

## Health checks (verified — different per NIM)

**Never** assume every model has `/v1/models`. Use [model-health](model-health/SKILL.md).

| Model | Pass health with | Ignore (404 is normal) |
|-------|------------------|------------------------|
| Cosmos3-Reason | `/v1/models`, `/v1/health/ready`, `/v1/health/live` | `/v1/health` |
| YOLO11 | **`/healthz`** only (`ok` + `model_loaded`) | `/v1/models`, `/v1/health/*` |
| Embed1 | `/v1/models`, `/v1/health/ready`, `/v1/health/live` | `/v1/health` |
| Canary | `/v1/health/ready`, `/v1/health/live` | **`/v1/models`**, `/healthz` |

---

## 1. NVIDIA Cosmos3-Reason (`nvidia/cosmos3-reason`)

**What it is:** Vision-language model (VLM). Understands video/image + text; writes natural-language descriptions and answers.

**Used by:** DataEngine `video-reasoner` (segment captions / reasoning), retrieval backend (LLM synthesis / agent answers).

**API:** OpenAI-compatible chat

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

Production-style content can mix text + video:

```json
"content": [
  {"type": "text", "text": "Describe this clip for search."},
  {"type": "video_url", "video_url": {"url": "data:video/mp4;base64,..."}}
]
```

Health: `GET ${COSMOS3_REASON_URL}/v1/models`, `/v1/health/ready`, `/v1/health/live` (all with bearer).

---

## 2. YOLO11 (`yolo11s`) — Ultralytics, not Cosmos

**What it is:** Object detector — classes, counts, bounding boxes on video frames.

**Used by:** DataEngine `video-detector` (perception metadata + optional bbox sidecars on S3).

**API:** custom infer

```bash
B64=$(base64 -i clip.mp4 | tr -d '\n')
curl -s -X POST "${YOLO_URL}/v1/infer" \
  "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"video_base64\":\"$B64\",\"filename\":\"clip.mp4\",\"include_frames\":true}"
```

Expect fields like `perception_ok` / `object_classes` / `object_counts` / `frames`.

**Health (not NIM-style):** `GET ${YOLO_URL}/healthz` → `{"ok":true,"model_loaded":true,...}`. There is **no** `/v1/models` or `/v1/health/ready` on this server.

---

## 3. NVIDIA Cosmos Embed1 (`cosmos-embed1`)

**What it is:** Embedding model for hybrid search — **256-dim** vectors for text and video.

**Used by:** DataEngine `video-embedder`, backend semantic search. Dims **must** stay 256 (VastDB `vectors` column).

**API:** embeddings with Cosmos `request_type` (not OpenAI `dimensions`)

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

Expect `dim= 256`. Video: `input` as `data:video/mp4;base64,...` with `request_type:"query"`.

---

## 4. NVIDIA Canary-1B (`canary-1b`) — optional (Riva HTTP ASR)

**What it is:** Speech-to-text (ASR) / speech translation via **Riva HTTP API**. **Not** a Cosmos video model; **not** in the default VSS pipeline.

**Used by:** Nothing by default — optional demos (transcripts, spoken-word search, subtitles).

**Health (verified):** only these:

```bash
curl -s "${AUTH[@]}" "$CANARY_1B_URL/v1/health/ready"   # {"status":"ready"}
curl -s "${AUTH[@]}" "$CANARY_1B_URL/v1/health/live"    # {"status":"live"}
```

`/v1/models` returns **404** on this NIM — **do not** treat that as down. Optional: `/docs`, `/openapi.json`.

**Infer:** `POST /v1/audio/transcriptions` (multipart `file` required):

```bash
curl -s -X POST "${CANARY_1B_URL}/v1/audio/transcriptions" \
  "${AUTH[@]}" \
  -F "file=@clip_audio.wav" \
  -F "model=nvidia/canary-1b"
```

Wire results into your demo (metadata, UI, or a mini-app). Do not change the shared DataEngine ingest pipeline.

---

## Agent instructions

1. Find the single `/config/*.config` team file; if missing or ambiguous, ask the user. Never search the repo's `team-configs/`.
2. Source it and require a non-empty, non-placeholder `GPU_BEARER_TOKEN`; never copy it into the repository.
3. Always send `Authorization: Bearer $GPU_BEARER_TOKEN`.
4. For pipeline debugging: Cosmos3-Reason / YOLO / Embed1 first (`gpu-model-health`, then `gpu-model-smoke-test`).
5. For Canary: explain it is optional ASR; probe the endpoint; help the user design a custom flow — never claim it runs in default ingest.
6. Never invent alternate hosts/ports; never echo the bearer token.

## Related skills

| Skill | When |
|-------|------|
| [model-health](model-health/SKILL.md) | Up / ready checks for all four |
| [model-smoke-test](model-smoke-test/SKILL.md) | Minimal real inference per model |
