#!/usr/bin/env bash
# PreCompact (matcher: manual|auto). Runs before context compaction.
# Use it to snapshot state that must survive compaction. Stdout context is re-injected by SessionStart(compact).
source "$(dirname "$0")/_lib.sh"
log "trigger=$(json_get '.trigger') transcript=$(json_get '.transcript_path')"
# TODO(stub): e.g. copy the transcript, or write a progress note to docs/CURRENT.md
exit 0
