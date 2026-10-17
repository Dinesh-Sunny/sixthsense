#!/usr/bin/env bash
# Stop (no matcher). Runs when Claude finishes a turn. Can force Claude to keep working.
# Set CLAUDE_HOOK_STOP_CHECK_CMD (e.g. "pnpm typecheck && pnpm lint") to block finishing while checks fail.
# Unset = no-op. Loop-safe: respects stop_hook_active (Claude Code also caps consecutive continuations).
source "$(dirname "$0")/_lib.sh"
check="${CLAUDE_HOOK_STOP_CHECK_CMD:-}"
[[ -z "$check" ]] && exit 0
[[ "$(json_get '.stop_hook_active')" == "true" ]] && exit 0

# Only check when files actually changed.
if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
   && [[ -z "$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null)" ]]; then
  exit 0
fi

log "stop-check: $check"
if ! out="$(cd "$PROJECT_DIR" && bash -c "$check" 2>&1)"; then
  (( ${#out} > 2000 )) && out="…${out:${#out}-2000}"   # keep the tail, where errors are
  jq -n --arg r "Checks failed (\`$check\`). Fix before finishing:"$'\n'"$out" '{decision:"block",reason:$r}'
fi
exit 0
