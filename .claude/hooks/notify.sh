#!/usr/bin/env bash
# Notification (matcher: permission_prompt|idle_prompt). Sends a desktop notification when Claude needs you.
source "$(dirname "$0")/_lib.sh"
msg="$(json_get '.message')"; title="Claude Code · $(basename "$PROJECT_DIR")"
log "notify: $msg"
if command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"${msg//\"/\\\"}\" with title \"$title\"" >/dev/null 2>&1 || true
elif command -v notify-send >/dev/null 2>&1; then
  notify-send "$title" "$msg" || true
fi
exit 0
