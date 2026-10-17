#!/usr/bin/env bash
# PostToolUse (matcher: Edit|Write). Formats the file Claude just changed, choosing the formatter by extension.
# Configure in settings.json "env":
#   CLAUDE_HOOK_FORMAT_MAP  "ext,ext=cmd;ext=cmd"   e.g. "py=uv run ruff format;ts,tsx=pnpm exec biome format --write"
#   CLAUDE_HOOK_FORMAT_CMD  fallback command for extensions not in the map (optional)
# The file path is appended to the command. Empty config = no-op.
source "$(dirname "$0")/_lib.sh"
file="$(json_get '.tool_input.file_path')"
[[ -z "$file" || ! -f "$file" ]] && exit 0
ext="${file##*.}"

fmt=""
IFS=';' read -r -a entries <<< "${CLAUDE_HOOK_FORMAT_MAP:-}"
for entry in "${entries[@]}"; do
  [[ "$entry" == *=* ]] || continue
  IFS=',' read -r -a exts <<< "${entry%%=*}"
  for e in "${exts[@]}"; do
    [[ "$e" == "$ext" ]] && { fmt="${entry#*=}"; break 2; }
  done
done
fmt="${fmt:-${CLAUDE_HOOK_FORMAT_CMD:-}}"
[[ -z "$fmt" ]] && exit 0

log "format [$ext] $file"
if ! out="$(cd "$PROJECT_DIR" && $fmt "$file" 2>&1)"; then
  # Non-blocking: tell Claude formatting failed so it can fix syntax.
  add_context "PostToolUse" "Formatter failed on $file: ${out:0:500}"
fi
exit 0
