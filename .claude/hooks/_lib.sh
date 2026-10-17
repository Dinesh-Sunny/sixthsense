#!/usr/bin/env bash
# Shared helpers for hook scripts. Source with:  source "$(dirname "$0")/_lib.sh"
# Hook contract (https://code.claude.com/docs/en/hooks):
#   stdin  : event JSON (session_id, transcript_path, cwd, permission_mode, hook_event_name, + event fields)
#   exit 0 : success; stdout parsed as JSON if it is JSON (for UserPromptSubmit/SessionStart, plain stdout becomes context)
#   exit 2 : blocking error; stderr is fed back to Claude (for events that can block)
#   other  : non-blocking error; shown in transcript, execution continues
set -euo pipefail

HOOK_INPUT="$(cat)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
LOG_DIR="$PROJECT_DIR/.claude/logs"

# json_get '.tool_input.command'  -> prints value or empty string
json_get() { printf '%s' "$HOOK_INPUT" | jq -r "$1 // empty" 2>/dev/null || true; }

# log "message"  -> appends to .claude/logs/hooks.log when CLAUDE_HOOK_LOG=1
log() {
  [[ "${CLAUDE_HOOK_LOG:-0}" == "1" ]] || return 0
  mkdir -p "$LOG_DIR"
  printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S')" "$(json_get '.hook_event_name')" "$*" >> "$LOG_DIR/hooks.log"
}

# block "reason"  -> exit 2 with reason on stderr (Claude sees it)
block() { echo "$1" >&2; exit 2; }

# pretool_decision deny|allow|ask "reason"  -> structured PreToolUse decision
pretool_decision() {
  jq -n --arg d "$1" --arg r "$2" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:$d,permissionDecisionReason:$r}}'
  exit 0
}

# add_context "EventName" "text"  -> inject additionalContext (SessionStart, UserPromptSubmit, PostToolUse, ...)
add_context() {
  jq -n --arg e "$1" --arg c "$2" '{hookSpecificOutput:{hookEventName:$e,additionalContext:$c}}'
  exit 0
}
