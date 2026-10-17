#!/usr/bin/env bash
# Generic logger: appends the raw event JSON to .claude/logs/events.jsonl.
# Not wired by default. templates/hooks.all-events.json wires it to every event, which helps when learning or debugging hooks.
source "$(dirname "$0")/_lib.sh"
mkdir -p "$LOG_DIR"
printf '%s\n' "$HOOK_INPUT" | jq -c '. + {logged_at: (now | todate)}' >> "$LOG_DIR/events.jsonl" 2>/dev/null || true
exit 0
