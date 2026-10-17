#!/usr/bin/env bash
# SessionEnd. Runs on exit (shared 1.5s budget unless a longer timeout is set). Keep it fast.
source "$(dirname "$0")/_lib.sh"
log "reason=$(json_get '.reason') session=$(json_get '.session_id')"
# TODO(stub): cleanup temp files, stop local services started by SessionStart, etc.
exit 0
