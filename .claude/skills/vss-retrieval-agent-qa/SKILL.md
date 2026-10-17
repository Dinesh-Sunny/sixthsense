---
name: retrieval-agent-qa
description: >-
  Ask natural-language questions about the video archive and get grounded answers via
  POST /api/v1/agent/ask and /agent/search-and-answer, backed by /api/v1/tools/* (search,
  segments, segment, detections, explore, synthesize). Use for Q&A over all videos or one
  specific video, instead of raw search hits.
---

# Retrieval: agent Q&A (vss2)

Thin agent that plans → searches/reads VastDB tools → returns a grounded answer. Use this (not `/search`) when the user wants an **answer**, not a hit list. JWT required (`retrieval/login`). There is **no** `/videos/ask` route — use `/agent/ask`.

## Ask — `POST /api/v1/agent/ask`

```bash
curl -s -X POST "$BACKEND/api/v1/agent/ask" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"Was anyone near the loading dock after 6pm?","top_k":10}'
```

| Field | Default | Behavior |
|-------|---------|----------|
| `question` | — | required |
| `original_video` | null | if set → answer from **that** parent video's segments; else global hybrid search |
| `top_k` | 10 | segments/results considered (1–50) |

Response: `{ answer, tool_used ("search_hybrid"|"video_segments"), evidence }`.

## Search + answer with filters — `POST /api/v1/agent/search-and-answer`

Same body as `POST /search` (`retrieval/search`: `tags`, `time_filter`, `metadata_filters`, `min_similarity`…) → grounded answer + rich chunk evidence.

```bash
curl -s -X POST "$BACKEND/api/v1/agent/search-and-answer" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"forklift incidents","time_filter":"7d","metadata_filters":{"location":"Warehouse A"},"top_k":10}'
```

`evidence` includes `chunks[]` (`original_video`, `similarity_score`, `best_match_start_sec/end_sec`, `preview_source`), timings, and `llm_synthesis`.

## Agent tools — `GET/POST /api/v1/tools/*`

Composable building blocks (same auth): `POST tools/search`, `GET tools/segments?original_video=`, `GET tools/segment?source=`, `GET tools/detections?source=`, `GET tools/explore`, `POST tools/synthesize`. Use these to gather evidence when you orchestrate multi-step reasoning yourself.

## Choosing an endpoint

- General question over everything → `POST /agent/ask`.
- Question about one known video → `POST /agent/ask` with `original_video`.
- Question needing filters (time/location/tags) + evidence → `POST /agent/search-and-answer`.
- Whole-video summary/report → `retrieval/videos` `POST /videos/synthesize`.

## Agent instructions

1. Ensure a JWT.
2. Prefer `agent/*` for answers; cite `answer` and back it with `evidence` chunks (link via `retrieval/videos` playback).
3. Apply filters through `search-and-answer` (resolve fields via `retrieval/list-metadata`).
