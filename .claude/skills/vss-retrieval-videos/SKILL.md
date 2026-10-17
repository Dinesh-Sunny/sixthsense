---
name: retrieval-videos
description: >-
  Browse, play, and summarize indexed videos via /api/v1/videos/* — explore (timeline),
  stream and playback-url (playback), detections (YOLO bbox), metadata (segment row), and
  POST /videos/synthesize (LLM summary/report over a whole parent video). Use to list,
  play back, inspect, or summarize a specific video.
---

# Retrieval: videos (vss2)

Playback + per-video inspection + on-demand summarization. All JWT (`retrieval/login`). `original_video` = parent upload S3 URI; `source` = a single segment clip S3 URI.

## Browse — `GET /api/v1/videos/explore`

Lists **fully-indexed** parent chunks (no query needed).

```bash
curl -s "$BACKEND/api/v1/videos/explore?scope=all&limit=48&offset=0" -H "Authorization: Bearer $TOKEN"
# optional: &date=YYYY-MM-DD &location=<label>
```

## Play — `GET /api/v1/videos/stream` / `playback-url`

JWT goes in `?token=` (not header) so `<video>` works.

```bash
# Range-capable proxy stream (seekable):
"$BACKEND/api/v1/videos/stream?source=s3://vss-chunks-segments/<key>&token=$TOKEN"
# Or a presigned S3 GET URL (needs bucket CORS for direct browser playback):
curl -s "$BACKEND/api/v1/videos/playback-url?source=s3://vss-chunks-segments/<key>&token=$TOKEN&expires_in=3600"
```

## Inspect a segment

```bash
curl -s "$BACKEND/api/v1/videos/metadata?source=s3://vss-chunks-segments/<key>" -H "Authorization: Bearer $TOKEN"    # row: reasoning, tags, timing
curl -s "$BACKEND/api/v1/videos/detections?source=s3://vss-chunks-segments/<key>" -H "Authorization: Bearer $TOKEN"  # YOLO bbox sidecar JSON
```

`detections` 404 = no YOLO sidecar for that segment (detector disabled or no detections).

## Summarize / report — `POST /api/v1/videos/synthesize`

LLM summary over **all** segments of one parent video (no VastDB write). This is the "generate a report/summary for this video" capability (there is no `/reports` route).

```bash
curl -s -X POST "$BACKEND/api/v1/videos/synthesize" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "original_video": "s3://vss-chunks/user/20260101_120000_ab12cd34.mp4",
    "question": "Summarize what happens in this video",
    "max_segments": 40
  }'
```

Optional `system_prompt` overrides the default (chronological Overview + Timeline markdown). Response: `answer`, `llm_synthesis`, `segment_count`, `segments_used`, `generated_at`. 404 if no accessible segments.

## Related

Same functions are exposed as agent tools under `/api/v1/tools/*` (`segments`, `segment`, `explore`, `synthesize`, `detections`) — see `retrieval/agent-qa`.

## Agent instructions

1. Ensure a JWT; use `explore`/`search` to get `original_video`/`source` URIs first.
2. Playback endpoints take the token as `?token=`; all others use the header.
3. For "summarize/report on this video" → `POST /videos/synthesize` (whole parent); for a specific question → `retrieval/agent-qa`.
