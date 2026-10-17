#!/usr/bin/env bash
# Network refresh checks for the stack registry (report only, exit 0): lib refs resolve
# (`stacks.py refs` expands them to URLs), live ToC coverage, lib version drift, locked skills vs upstream,
# MCP pins vs latest, installed-dep health.
# Usage: stacks_check.sh [--diff]   (--diff prints upstream skill diffs, not just CHANGED)
set -uo pipefail
show_diff=0; [ "${1:-}" = "--diff" ] && show_diff=1
root=$(git rev-parse --show-toplevel)
cd "$root" || exit 1
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
stacks() { .claude/skills/feature/scripts/stacks.sh "$@"; }
broken=0 agent_refs=0 uncovered=0 drifted=0 changed=0 stale_pins=0 unhealthy=0

echo "== lib refs"
stacks refs >"$tmp/refs" || echo "stacks.py refs failed"
while read -r where ref; do
  case $ref in
    mcp:docs-langchain/*) p=${ref#mcp:docs-langchain/}; url="https://docs.langchain.com/${p%.mdx}" ;;
    mcp:reference-langchain/*) url="https://reference.langchain.com/${ref#mcp:reference-langchain/}" ;;
    mcp:*) agent_refs=$((agent_refs + 1)); continue ;;
    *) url=$ref ;;
  esac
  echo "$where $url"
done <"$tmp/refs" >"$tmp/urls"
# HEAD first, ranged GET fallback (some docs hosts reject HEAD); 8 in parallel.
cut -d' ' -f2 "$tmp/urls" | sort -u | xargs -P 8 -I{} sh -c 'curl -gsfLI --max-time 20 -o /dev/null "$1" \
  || curl -gsfL --max-time 20 -r 0-0 -o /dev/null "$1" || echo "$1"' _ {} >"$tmp/dead"
while read -r url; do
  awk -v u="$url" '$2 == u {print "BROKEN " $1 " " u}' "$tmp/urls"
done <"$tmp/dead"
broken=$(grep -c . "$tmp/dead")
echo "$(cut -d' ' -f2 "$tmp/urls" | sort -u | grep -c .) urls checked, $broken broken; $agent_refs mcp refs to verify via agent"

echo "== toc coverage"
.claude/skills/feature/scripts/stacks_coverage.sh >"$tmp/coverage" 2>&1
cat "$tmp/coverage"
uncovered=$(grep -c ': missing ' "$tmp/coverage")

echo "== lib drift"
stacks drift >"$tmp/drift" 2>&1 || echo "stacks.py drift failed:"
cat "$tmp/drift"
drifted=$(grep -c . "$tmp/drift")

echo "== locked skills vs upstream"
if [ -f skills-lock.json ]; then
  jq -r '.skills | to_entries[] | select(.value.sourceType == "github")
    | "\(.key) \(.value.source) \(.value.skillPath)"' skills-lock.json >"$tmp/skills"
  while read -r name source path; do
    curl -sfL --max-time 30 -o "$tmp/upstream.md" \
      "https://raw.githubusercontent.com/$source/HEAD/$path" </dev/null \
      || { echo "UNKNOWN $name (fetch failed)"; continue; }
    local_md=.agents/skills/$name/SKILL.md
    if ! diff -q "$local_md" "$tmp/upstream.md" >/dev/null 2>&1; then
      changed=$((changed + 1))
      echo "CHANGED $name (re-lock after review: npx skills update -p $name)"
      [ "$show_diff" -eq 1 ] && diff -u "$local_md" "$tmp/upstream.md" | head -60
    fi
  done <"$tmp/skills"
fi

echo "== MCP pins"
if [ -f .mcp.json ]; then
  jq -r '.mcpServers[] | (.args // [])[] | select(test("^[@a-z0-9][^@]*@[0-9]"))' .mcp.json \
    | while read -r pinned; do
        pkg=${pinned%@*} ver=${pinned##*@}
        latest=$(npm view "$pkg" version </dev/null 2>/dev/null)
        [ "$latest" = "$ver" ] && echo "OK $pkg@$ver" || echo "BEHIND $pkg@$ver (latest ${latest:-?})"
      done | tee "$tmp/pins"
  stale_pins=$(grep -c '^BEHIND' "$tmp/pins")
else
  echo "no .mcp.json"
fi

echo "== installed dep health (report only)"
stacks deps >"$tmp/deps" || echo "stacks.py deps failed"
while read -r eco name; do
  flag=(); [ "$eco" = npm ] && flag=(--npm)
  .claude/skills/feature/scripts/lib_check.sh ${flag[@]+"${flag[@]}"} --installed "$name" </dev/null 2>&1 \
    | grep -E '^(== |verdict: )' | paste -d' ' - - | sed 's/^== //; s/ verdict: / -> /'
done <"$tmp/deps" | tee "$tmp/health"
unhealthy=$(grep -vc -- '-> PASS$' "$tmp/health")

echo "== summary: broken refs $broken, uncovered pages $uncovered, drift $drifted, skills changed $changed, MCP pins behind $stale_pins, deps not PASS $unhealthy"
exit 0
