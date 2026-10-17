#!/usr/bin/env bash
# SessionStart (matcher: startup|resume|clear|compact)
# Injects live project state as context at the start of each session.
source "$(dirname "$0")/_lib.sh"
source_type="$(json_get '.source')"
log "source=$source_type"

ctx="Session source: ${source_type:-unknown}."
if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch="$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || echo detached)"
  dirty="$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | head -20)"
  last="$(git -C "$PROJECT_DIR" log -5 --oneline 2>/dev/null || true)"
  ctx+=$'\n'"Git branch: $branch"
  ctx+=$'\n'"Recent commits:"$'\n'"${last:-none}"
  [[ -n "$dirty" ]] && ctx+=$'\n'"Uncommitted changes (first 20):"$'\n'"$dirty"
fi
# Derived, never-stale facts: real commands from package.json / Makefile / justfile.
cmds="$(python3 "$PROJECT_DIR/.claude/scripts/ctx.py" commands 2>/dev/null | head -25)"
[[ -n "$cmds" && "$cmds" != no\ * ]] && ctx+=$'\n'"Project commands (derived from manifests, authoritative over docs):"$'\n'"$cmds"
# Context health: budgets, broken refs, inbox size, adapter drift.
health="$(python3 "$PROJECT_DIR/.claude/scripts/ctx.py" status --brief 2>/dev/null)"
[[ -n "$health" ]] && ctx+=$'\n'"$health"
# TODO(stub): append more context here, e.g. the active issue, required services, or a TODO file
# [[ -f "$PROJECT_DIR/docs/CURRENT.md" ]] && ctx+=$'\n'"$(cat "$PROJECT_DIR/docs/CURRENT.md")"

add_context "SessionStart" "$ctx"
