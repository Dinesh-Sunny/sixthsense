#!/usr/bin/env bash
# Report always-loaded / per-spawn instruction files that exceed their line budget.
cd "$(git rev-parse --show-toplevel)" || exit 1
over=0
check() { # <limit> <files...>
  local limit=$1; shift
  for f in "$@"; do
    [ -f "$f" ] || continue
    n=$(wc -l <"$f" | tr -d ' ')
    [ "$n" -gt "$limit" ] && { echo "OVER $f: $n lines (budget $limit)"; over=1; }
  done
}
check 80  CLAUDE.md
check 45  .claude/agents/*.md
check 40  .claude/skills/feature/SKILL.md .claude/rules/*.md
check 60  .claude/skills/feature/standards.md .claude/agent-memory/*/MEMORY.md
check 100 .claude/agent-memory/*/*.md
check 80  .claude/stacks/README.md
# stacks lib/usage/view are knowledge, not always-loaded instructions: uncapped
[ $over -eq 0 ] && echo "context budget OK"
exit 0
