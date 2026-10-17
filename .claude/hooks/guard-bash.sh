#!/usr/bin/env bash
# PreToolUse (matcher: Bash). Blocks destructive shell commands before they run.
# Permission rules in settings.json are the hard gate; this is defense in depth with clearer messages.
source "$(dirname "$0")/_lib.sh"
cmd="$(json_get '.tool_input.command')"
log "cmd=$cmd"

deny_patterns=(
  'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f?[[:space:]]+(/|~|\$HOME)([[:space:]]|$)'
  'git[[:space:]]+push[[:space:]].*(--force|-f)([[:space:]]|$)'
  'git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+origin'
  ':\(\)\{ *:\|:& *\};:'
  'mkfs\.'
  'dd[[:space:]]+if=.*of=/dev/'
  'chmod[[:space:]]+-R[[:space:]]+777'
  '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh'
  'DROP[[:space:]]+(DATABASE|TABLE)'
)
# TODO(stub): add project-specific patterns (prod DB hosts, deploy commands, etc.)

for p in "${deny_patterns[@]}"; do
  if printf '%s' "$cmd" | grep -Eiq -- "$p"; then
    pretool_decision deny "Blocked by .claude/hooks/guard-bash.sh (pattern: $p). Ask the user to run it manually if it is really intended."
  fi
done
exit 0
