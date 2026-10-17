#!/usr/bin/env bash
# PreToolUse (matcher: Edit|Write|NotebookEdit). Blocks edits to protected paths.
# The protected globs come from CLAUDE_HOOK_PROTECTED_GLOBS (colon-separated) in settings.json "env".
source "$(dirname "$0")/_lib.sh"
file="$(json_get '.tool_input.file_path')"
[[ -z "$file" ]] && file="$(json_get '.tool_input.notebook_path')"
[[ -z "$file" ]] && exit 0
rel="${file#"$PROJECT_DIR"/}"
base="$(basename "$file")"
log "file=$rel"

IFS=':' read -r -a globs <<< "${CLAUDE_HOOK_PROTECTED_GLOBS:-.env:.env.*}"
for g in "${globs[@]}"; do
  # shellcheck disable=SC2053
  if [[ "$rel" == $g || "$base" == $g ]]; then
    [[ "$base" == ".env.example" ]] && continue
    pretool_decision deny "$rel is protected (glob '$g'). Edit it manually, or change CLAUDE_HOOK_PROTECTED_GLOBS in .claude/settings.json."
  fi
done
exit 0
