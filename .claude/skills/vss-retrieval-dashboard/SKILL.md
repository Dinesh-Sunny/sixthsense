---
name: retrieval-dashboard
description: >-
  Get aggregate VSS stats via GET /api/v1/dashboard/stats — overview counts, ingest
  quality, detected objects, uploads-by-day, S3-vs-VastDB inventory/pipeline alignment,
  and recent videos. Use to check ingest health, how many videos are indexed, or spot
  chunks that failed to index.
---

# Retrieval: dashboard (vss2)

One bundled aggregate over the VastDB collection (ACL-filtered), plus live S3 inventory. Requires a JWT (`retrieval/login`).

## Request — `GET /api/v1/dashboard/stats`

`scope` query param: `all` (default) | `mine` | `public`.

```bash
curl -s "$BACKEND/api/v1/dashboard/stats?scope=all" -H "Authorization: Bearer $TOKEN"
```

The response is one object with **all** sections (no per-section `scope` param):

| Section | Highlights |
|---------|-----------|
| `overview` | `total_rows`, `segment_rows`, `unique_videos`, `fully_indexed_videos`, `indexed_clips`, `re_ingest_rows`, `stream_sessions`, `duplicate_segment_rows`, public/private counts |
| `quality` | `reasoning_ok(_pct)`, `perception_ok(_pct)`, `with_object_classes(_pct)` |
| `objects[]` | detected object classes: `label`, `segment_count`, `instance_count` |
| `metadata{}` | value distributions per upload field (`location`, `camera_id`, `capture_type`…) |
| `uploads_by_day[]` | `date`, `segment_rows` |
| `recent_videos[]` | per parent: `original_video`, `filename`, `segment_rows`, `indexed_clips`, `unique_segments`, `expected_segments`, `duplicate_rows`, `ingest_kind`, upload metadata |
| `s3_inventory` | `chunks_mp4`, `segments_mp4`, `segmenter_output_mp4` per bucket (`vss-chunks`, `vss-chunks-segments`) |
| `pipeline_alignment` | `segments_s3_mp4` vs `indexed_clips`/`segment_rows`, `pending_index`, `healthy` flags |

## Diagnosing "segments didn't index"

Compare `s3_inventory.segments_mp4` (clips written by the segmenter) with `pipeline_alignment.indexed_clips` / `overview.indexed_clips`:
- `pending_index > 0` or `indexed_matches_segments_s3: false` → clips in S3 not yet in VastDB (reasoner/embedder/writer lag or silent drop — check the DataEngine function logs/traces).
- Per video, `unique_segments < expected_segments` in `recent_videos` → that upload is partially indexed.
- `duplicate_segment_rows > 0` → re-ingest/dedup slots (writer skips duplicate `source`).

## Agent instructions

1. Ensure a JWT; pick `scope` (`mine` for the caller's uploads).
2. For "is my video processed?", read `recent_videos[]` + `pipeline_alignment`, not just totals.
3. This is read-only aggregation; to inspect a specific row, use `retrieval/videos` or `vast-database/vastdb-read`.
