#!/usr/bin/env bash
# Unattended stack-outline refresh, launched weekly in the background by
# .claude/hooks/stack-drift.sh. Runs stacks_check.sh (network only, no tokens), then one
# headless `stack-expert` refresh per stack with lib drift, broken refs or uncovered ToC pages, in a throwaway
# worktree; commits to chore/stacks-refresh-<stamp> only if the stack guards pass.
# Skill/MCP-pin updates stay report-only (supply chain: a human re-locks them).
# State + log + one-line result: <git-common-dir>/stacks-refresh/.
# Usage: stacks_refresh.sh [--dry-run]   (--dry-run prints the stacks it would refresh)
set -uo pipefail
root=$(git rev-parse --show-toplevel) || exit 1
cd "$root" || exit 1
state="$(git rev-parse --path-format=absolute --git-common-dir)/stacks-refresh"
mkdir -p "$state"
mkdir "$state/lock" 2>/dev/null || { echo "stacks refresh already running"; exit 0; }
trap 'rmdir "$state/lock"' EXIT
dry=0; [ "${1:-}" = "--dry-run" ] && dry=1
stamp=$(date +%Y%m%d-%H%M)
report() { echo "$(date +%F) $1" | tee "$state/result"; }

echo "== $(date) stacks_check"
.claude/skills/feature/scripts/stacks_check.sh >"$state/check.txt" 2>&1
summary=$(sed -n 's/^== summary: //p' "$state/check.txt")
# Drift + coverage lines start with the lib path; broken refs read "BROKEN <lib path>:<id> <url>".
stacks=$(grep -oE '^(BROKEN )?\.claude/stacks/lib/[a-z0-9-]+\.yaml' "$state/check.txt" \
  | sed -E 's#.*/##; s#\.yaml$##' | sort -u)
[ -z "$stacks" ] && { report "stacks: nothing to refresh ($summary)"; exit 0; }
[ "$dry" -eq 1 ] && { echo "$stacks"; exit 0; }
command -v claude >/dev/null || { report "stacks refresh failed: claude CLI not on PATH"; exit 1; }

branch="chore/stacks-refresh-$stamp" wt="$state/wt-$stamp"
git worktree add -q -b "$branch" "$wt" HEAD || { report "stacks refresh failed: git worktree add"; exit 1; }
cd "$wt" || exit 1
[ ! -f uv.lock ] || uv sync --quiet --frozen || { report "stacks refresh failed: uv sync in $wt"; exit 1; }

# dontAsk denies anything not listed: edits only in outlines + the expert's memory, Bash only
# stacks.py. Reads in the worktree need no rule.
allowed="Read,Grep,Glob,WebFetch,WebSearch,Skill,mcp__context7"
allowed+=",Edit(./.claude/stacks/**),Write(./.claude/stacks/**)"
allowed+=",Edit(./.claude/agent-memory/stack-expert/**),Write(./.claude/agent-memory/stack-expert/**)"
allowed+=",Bash(.claude/skills/feature/scripts/stacks.sh *)"
allowed+=",Bash(.claude/skills/feature/scripts/stacks_coverage.sh *)"
allowed+=$(jq -r '.mcpServers | keys[] | ",mcp__" + .' .mcp.json | tr -d '\n')

done_stacks=""
for s in $stacks; do
  findings=$(grep -E "lib/$s\.yaml" "$state/check.txt" | head -20)
  echo "== $(date) refresh $s"
  printf '%s\n' "Refresh mode for stack \`$s\`. Unattended: nobody can answer questions." \
    "Findings from stacks_check.sh:" "$findings" \
    "Fix broken refs; cover or skip (with why) every missing ToC page; diff release notes from the lib version to the installed one; add," \
    "deprecate, bump version/verified. End with \`.claude/skills/feature/scripts/stacks.sh" \
    "view $s\`, \`... stacks.sh validate\` clean and" \
    "\`.claude/skills/feature/scripts/stacks_coverage.sh $s\` at 0 missing." \
    "Reply with one line: what changed." \
    | STACKS_REFRESH=1 claude -p --agent stack-expert --permission-mode dontAsk \
      --allowedTools "$allowed" --mcp-config .mcp.json \
    && done_stacks+="$s " || echo "refresh $s: claude exited non-zero"
done

git add -A .claude/stacks .claude/agent-memory/stack-expert
if git diff --cached --quiet; then
  cd "$root" && git worktree remove --force "$wt" && git branch -q -D "$branch"
  report "stacks: experts found nothing to change for: $stacks ($summary)"
  exit 0
fi
if out=$(.claude/skills/feature/scripts/stacks.sh guards 2>&1); then
  git commit -q -m "chore(stacks): automated outline refresh (${done_stacks% })" \
    && cd "$root" && git worktree remove --force "$wt"
  report "stacks refreshed on branch $branch (${done_stacks% }); review + git merge $branch ($summary)"
else
  echo "$out" | tail -40
  report "stacks refresh failed guards; inspect $wt (log $state/log) ($summary)"
  exit 1
fi
