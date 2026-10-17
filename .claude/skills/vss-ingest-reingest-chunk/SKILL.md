---
name: ingest-reingest-chunk
description: Finds and re-ingests one specific fully indexed VSS chunk from Explore, even when the user does not know its filename or S3 URI. Use when the user gives a chunk filename such as 20260901_224739_london-luxury-walk_chunk_0000.mp4, a truncated Explore title, a scene, date, place, camera, or Explore card and wants only that chunk re-ingested. Completes the filename to original_video using the chunks bucket and username from the team config.
---

# Re-ingest one Explore chunk

Use this skill for exactly one parent chunk shown as one card in Explore. For
already-indexed archive cards, re-ingest is the right path. To add a **new** local
video file, use `ingest/upload-video` instead. Do not batch sync, manually copy S3
objects, or re-ingest an arbitrary individual segment.

The user does **not** need to know the chunk filename, `stream_id`, or full
`original_video` URI. Discover the chunk, show candidates, and let the user choose.

## Required choices

Do not start until the user has:

1. selected exactly one chunk;
2. chosen whether to keep or change prompt and metadata;
3. confirmed the final request.

Use `AskQuestion` for choices. A specific chunk always has `chunk_count: 1`; do not
ask how many chunks.

## Authenticate

Use the single `/config/*.config` team file. Do not search the repo's
`team-configs/`. If it is missing or multiple files match, ask the user.

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
TEAM_CONFIG="${TEAM_CONFIGS[0]}"
set -a && source "$TEAM_CONFIG" && set +a
BACKEND="$INGRESS_URL"
```

From that config take:

- `INGRESS_URL` → `BACKEND`
- `USERNAME` / `PASSWORD` → login (do not print them)
- `S3_CHUNKS_BUCKET` and `USERNAME` → complete a chunk filename to `original_video`

Login:

```bash
TOKEN=$(curl -s -X POST "$BACKEND/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"<USERNAME>","password":"<PASSWORD>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Use `Authorization: Bearer $TOKEN` on later calls. Never print credentials or tokens.

## Find the chunk

Choose the discovery method from what the user knows.

### Filename — complete with team-config (then confirm)

The user will often paste only the card title, for example:

```text
20260901_224739_london-luxury-walk_chunk_0000.mp4
```

or a truncated UI title such as `20260901_224739_london-luxury-walk_chun...`.
If truncated, match the unique Explore `filename` that starts with that stem.

That basename is **not** the API field. Complete it from the team config:

```text
s3://<S3_CHUNKS_BUCKET>/<USERNAME>/<filename>
```

Example for team-a:

```text
s3://team-a-vss-chunks/team-a/20260901_224739_london-luxury-walk_chunk_0000.mp4
```

Batch-sync / upload keys are `{username}/{timestamp}_{name}_chunk_NNNN.mp4` in the
chunks bucket. Do not invent a different bucket or prefix.

Then confirm the URI exists on Explore (or that search/explore returns the same
`original_video`):

```bash
curl -s "$BACKEND/api/v1/videos/explore?scope=all&limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Page until `total` is covered. Prefer the Explore/search `original_video` if it
disagrees with the constructed URI (that is what VastDB indexed).

- **One match:** show the completed URI, metadata, and clip count, then continue.
- **Several matches:** list them and ask which card.
- **No Explore match:** show the config-built URI and ask whether to proceed; the
  re-ingest API returns 404 if that parent is not indexed.

### Date, location, camera, or capture type

Browse Explore:

```bash
curl -s "$BACKEND/api/v1/videos/explore?scope=all&limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Use API `date=YYYY-MM-DD` and `location=<value>` filters when applicable. Continue
with `offset += 100` until all `total` results are collected. Filter camera ID,
capture type, filename, and upload time client-side.

### Description of what happens

If the user describes visual content or an event, use semantic search:

```bash
curl -s -X POST "$BACKEND/api/v1/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"<description>","top_k":30,"llm_top_n":0,"min_similarity":0.3,"include_public":true}'
```

Use `chunk_results`, not individual `results`. Each chunk result contains the
needed `original_video`. Resolve metadata from the matching Explore entry.

If a query is too broad or has no useful matches, ask for one helpful discriminator
(approximate date/time, location, camera, or what appears in the scene), then retry.

## Present candidates

Never silently choose the first result. If there is not exactly one unambiguous
match, show all reasonable candidates and ask the user to select one.

For every candidate show:

- filename;
- upload date/time;
- location, camera ID, and capture type;
- stream ID and chunk index when available;
- clip count (`timeline.length`) and duration;
- a short caption/reasoning preview;
- the full `original_video` URI as the stable identifier.

Offer preview when needed using the candidate's `preview_source`:

```text
$BACKEND/api/v1/videos/stream?source=<url-encoded-preview_source>&token=<JWT>
```

Explore only returns fully indexed chunks, so a displayed candidate is safe for
whole-chunk re-ingest.

## Prompt and metadata choices

Show the selected chunk's current camera ID, capture type, location, upload time,
clip count, and short reasoning preview.

Fetch valid scenario/capture options:

```bash
curl -s "$BACKEND/api/v1/metadata/ingest-config"
```

Ask for one prompt mode:

- **Keep original prompt** — omit `scenario` and `custom_prompt`;
- **Scenario preset** — show available presets and ask which one;
- **Custom prompt** — collect exact text, maximum 800 characters.

Then ask whether to keep or change `camera_id`, `capture_type`, and `location`.
Omitted/blank fields preserve original values.

The API/VastDB row does not expose the exact prior scenario or custom prompt. Say
so rather than inventing it. Keeping the prompt uses metadata from the canonical
original S3 segments; on repeated re-ingest this may differ from the override used
by the immediately preceding re-ingest.

## Confirm and start

Confirm filename, full `original_video`, clip count, prompt mode, metadata
overrides, and that only this one chunk will be affected.

Send the exact URI returned by Explore/search:

```bash
curl -s -X POST "$BACKEND/api/v1/dashboard/reingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_video":"<exact-s3-uri>",
    "chunk_count":1
  }'
```

Never send `stream_id` for this workflow. A stream request means “latest N chunks
of the session” and may target a different card.

Add only selected non-empty overrides: `camera_id`, `capture_type`, `location`,
`scenario`, or `custom_prompt`. Build JSON with Python or `jq` so user text is
escaped safely.

## Monitor

Poll every four seconds:

```bash
curl -s "$BACKEND/api/v1/dashboard/reingest/<job_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Report `<completed_chunks>/1 chunks` and
`<indexed_segments>/<total_segments> clips` until `completed`.

After completion, refresh Explore and confirm the same `original_video` still has
the expected clip count. Replacement is atomic per
`(original_video, segment_number)`, so re-ingest must not create duplicate slots.

