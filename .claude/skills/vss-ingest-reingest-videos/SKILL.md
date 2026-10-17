---
name: ingest-reingest-videos
description: Re-ingest an existing indexed VSS video or stream through detector, reasoner, embedder, and writer using the retrieval API. Use for re-processing already-indexed archive content. Discovers available targets, asks the user to select a video, prompt/metadata behavior, and chunk count, then starts and monitors re-ingest. For uploading a new local video file, use ingest/upload-video instead.
---

# Ingest: re-ingest existing videos

Use this skill to re-process **already-indexed** archive content. To add a **new**
local video file through the backend, use `ingest/upload-video` instead. Do not
run batch sync, copy objects manually, or write directly to S3.

If the request is specifically for one Explore card/chunk—or the user describes a
scene but does not know its filename—use `ingest/reingest-chunk` instead.

Re-ingest copies existing segment objects to unique S3 keys, runs them through
detector → reasoner → embedder → writer, and atomically replaces each matching
VastDB segment slot.

## Non-negotiable interaction

Do not start re-ingest until the user has chosen:

1. the target video/stream;
2. whether to preserve or override prompt/metadata;
3. the number of latest complete chunks;
4. confirmation of the final request.

Use `AskQuestion` for choices. Never guess missing choices.

## Authenticate

Resolve the backend URL and credentials from the single `/config/*.config` team
file. Do not search the repo's `team-configs/`. If the file is missing or there
are multiple candidates, ask the user. Load it with:

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
TEAM_CONFIG="${TEAM_CONFIGS[0]}"
set -a && source "$TEAM_CONFIG" && set +a
BACKEND="$INGRESS_URL"
```

Authenticate with:

```bash
TOKEN=$(curl -s -X POST "$BACKEND/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Pass `Authorization: Bearer $TOKEN` on every request below. Do not print passwords
or tokens.

## 1. Discover and select a target

If the user did not identify one exact video/stream, fetch **all accessible
options**, not only the dashboard's 15 recent entries:

```bash
curl -s "$BACKEND/api/v1/videos/explore?scope=all&limit=100&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Continue with `offset += 100` until all `total` entries are collected. A chunk is
complete only when its timeline contains every segment number from 1 through
`total_segments`; exclude incomplete chunks from the available count. Group chunks
that have the same non-empty `stream_id`; otherwise use each `original_video` as
one target.

Present every target before asking the user to choose. For each option show:

- display name / filename;
- target ID: `stream_id`, or `original_video` when no stream ID exists;
- ingest kind;
- upload time;
- camera ID, capture type, and location;
- number of complete chunks represented;
- total indexed clips/segments.

Use the stable ID as the choice value. If there are no accessible targets, stop
and report that nothing can be re-ingested.

If the user supplied a name or partial ID, resolve it against the same inventory.
Proceed directly only when exactly one target matches; otherwise show the matching
options and ask.

## 2. Show current settings and ask about overrides

Before asking for changes, show the selected target's current values:

- camera ID;
- capture type;
- location;
- ingest kind;
- number of chunks and clips.

For a representative chunk, fetch its current row:

```bash
curl -sG "$BACKEND/api/v1/videos/metadata" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "source=<preview_source>"
```

Use it to supplement the displayed metadata. Be explicit about unavailable data:
the current API/VastDB row does not persist the original `scenario` or
`custom_prompt`, so do not invent or claim to display them. Say that leaving both
blank preserves prompt metadata from the canonical original S3 segment. On a
second re-ingest this means the original ingest prompt, not necessarily an override
used by the preceding re-ingest.

Fetch valid prompt presets and field options:

```bash
curl -s "$BACKEND/api/v1/metadata/ingest-config"
```

Ask the user to choose one prompt mode:

- **Keep original prompt** — omit both `scenario` and `custom_prompt`;
- **Scenario preset** — show the scenario names/descriptions returned by
  `ingest-config`, then ask which one;
- **Custom prompt** — ask for the exact prompt text (maximum 800 characters).

Explain that a custom prompt overrides a scenario. Sending a new scenario without
a custom prompt intentionally removes the old custom prompt.

Separately ask whether to:

- **Keep original metadata** — omit `camera_id`, `capture_type`, and `location`;
- **Change metadata** — show existing values and valid options from
  `ingest-config`, then collect only the fields the user wants changed. Blank
  fields mean preserve, not erase.

## 3. Ask for chunk count

Show how many complete chunks are available for the selected target and ask how
many of the **latest** chunks to re-ingest.

- Minimum: 1
- Maximum: available complete chunks and API limit 100
- For a target identified only by `original_video`, use 1.

Explain the resulting clip count when known. Re-ingest always selects whole
chunks; it never selects arbitrary individual clips.

## 4. Confirm and start

Show a concise confirmation containing target ID, chunk count, expected clips,
prompt mode, and metadata overrides. Start only after explicit confirmation.

For a stream:

```bash
curl -s -X POST "$BACKEND/api/v1/dashboard/reingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stream_id":"<stream-id>","chunk_count":<N>}'
```

For a non-stream video:

```bash
curl -s -X POST "$BACKEND/api/v1/dashboard/reingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"original_video":"<s3-uri>","chunk_count":1}'
```

Add only the chosen non-empty overrides: `camera_id`, `capture_type`, `location`,
`scenario`, or `custom_prompt`. Build JSON with Python or `jq`; do not interpolate
unescaped user prompt text into shell JSON.

Save the returned `job_id`, `selected_chunks`, and `copied_segments`.

## 5. Monitor and report

Poll every four seconds:

```bash
curl -s "$BACKEND/api/v1/dashboard/reingest/<job_id>" \
  -H "Authorization: Bearer $TOKEN"
```

Report progress as:

```text
Re-ingest: <completed_chunks>/<total_chunks> chunks,
<indexed_segments>/<total_segments> clips
```

Finish only when status is `completed`, or report a concrete API/pipeline error.
A 404 after a backend restart means only the in-memory progress record was lost;
it does not prove that processing stopped.

## Validation

After completion, refresh `/api/v1/dashboard/stats?scope=mine` or
`/api/v1/videos/explore`. Confirm that the target remains present with the expected
clip count. Re-ingest replaces slots, so row count should not increase from
duplicates.

