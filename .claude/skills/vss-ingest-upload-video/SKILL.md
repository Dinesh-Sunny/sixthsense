---
name: ingest-upload-video
description: >-
  Upload a new video file into VSS via POST /api/v1/videos/upload (multipart form
  proxied to the team's chunks S3 bucket). Use when the user wants to add a local
  or downloaded .mp4/.mov/.webm/.avi/.mkv through the backend upload endpoint — not
  for re-processing already-indexed archive content (use ingest/reingest-videos or
  reingest-chunk for that).
---

# Ingest: upload video (vss2)

Uploads a video through the retrieval backend. The backend writes the object into
the team's chunks bucket with ingest metadata; the DataEngine pipeline then runs
segmenter → detector → reasoner → embedder → VastDB writer.

This is **new content**. For an already-indexed video/stream or Explore card, use
`ingest/reingest-videos` / `ingest/reingest-chunk` instead.

## Non-negotiable interaction

Do not upload until the user has provided or chosen:

1. the video file path(s) to upload;
2. visibility (public vs private + optional allowed users);
3. analysis prompt mode (default / scenario preset / custom prompt);
4. optional metadata: `camera_id`, `capture_type`, `location`, tags;
5. confirmation of the final request.

Use `AskQuestion` for choices. Never guess missing choices. Do not print passwords
or JWTs.

## Authenticate

Resolve the backend URL and credentials from the single `/config/*.config` team
file. Do not search the repo's `team-configs/`. If the file is missing or there
are multiple candidates, ask the user.

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
TEAM_CONFIG="${TEAM_CONFIGS[0]}"
set -a && source "$TEAM_CONFIG" && set +a
BACKEND="$INGRESS_URL"

TOKEN=$(curl -s -X POST "$BACKEND/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

Pass `Authorization: Bearer $TOKEN` on the upload call. Prefer
`retrieval/login` if a token is already cached for the session.

## Limits and allowed types

Read live limits from config (do not hardcode):

```bash
curl -s "$BACKEND/api/v1/config" -H "Authorization: Bearer $TOKEN"
# use app.max_upload_size_mb (and note allowed extensions from backend)
```

Typical defaults: max size from `max_upload_size_mb` (often 25–100 MB), extensions
`.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`. Reject files that fail size/extension
checks before calling the API. Upload **one file per request**; for multiple
files, loop sequentially and report per-file success/failure.

## Discover ingest field options

```bash
curl -s "$BACKEND/api/v1/metadata/ingest-config"
```

Use returned `capture_types`, `analysis_scenarios`, and
`custom_prompt_max_length` (800) when asking for metadata / prompt choices.
Blank optional fields are fine — omit them from the form rather than sending
empty strings when the user skipped them.

## Confirm, then upload

Show a short confirmation: filename, size, `is_public`, scenario/custom prompt,
camera/capture/location/tags. Start only after explicit confirmation.

`POST /api/v1/videos/upload` — `multipart/form-data`:

| Field | Required | Notes |
|-------|----------|--------|
| `file` | yes | The video file |
| `is_public` | no | Default API `false`; UI usually sends `true` unless user chose private |
| `tags` | no | Comma-separated |
| `allowed_users` | no | Comma-separated; uploader is always included server-side |
| `scenario` | no | Preset key from `ingest-config`; ignored if `custom_prompt` is set |
| `custom_prompt` | no | Overrides scenario; max 800 chars |
| `camera_id` | no | Free text |
| `capture_type` | no | Value from `ingest-config` capture types |
| `location` | no | Free text |

```bash
VIDEO_PATH="/path/to/video.mp4"

curl -s -X POST "$BACKEND/api/v1/videos/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@${VIDEO_PATH}" \
  -F "is_public=true" \
  -F "tags=demo,test" \
  -F "scenario=general" \
  -F "camera_id=cam-1" \
  -F "capture_type=traffic" \
  -F "location=bangkok"
```

Private example — set `is_public=false` and optionally `-F "allowed_users=alice,bob"`.
Custom prompt — omit `scenario` and pass `-F "custom_prompt=..."`.

Success response shape:

```json
{
  "success": true,
  "object_key": "<username>/<timestamp>_<filename>",
  "message": "Video uploaded successfully and will be processed shortly"
}
```

Save `object_key`. On 400/413, report the API `detail` (bad extension or oversize).
On 401, re-login and retry once.

## After upload

Processing is asynchronous (pipeline). Tell the user indexing usually takes on the
order of tens of seconds to a few minutes depending on length and cluster load.

Optionally verify with:

```bash
curl -s "$BACKEND/api/v1/dashboard/stats?scope=mine" \
  -H "Authorization: Bearer $TOKEN"

curl -s "$BACKEND/api/v1/videos/explore?scope=mine&limit=20&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

Look for a new/recent parent whose filename or upload time matches. Do not claim
searchability until explore/dashboard shows the indexed clips.

## Agent instructions

1. Prefer this skill for **new file upload** via the backend; prefer re-ingest
   skills for content already in the team archive.
2. Always auth first; never log credentials or the bearer token.
3. Collect file path + visibility + prompt mode + optional metadata; confirm
   before `curl -F`.
4. One multipart request per file; surface each `object_key` or error.
5. After success, point the user at dashboard/explore (or offer to poll) rather
   than inventing pipeline status.
