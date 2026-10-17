#!/usr/bin/env bash
# Live ToC coverage of lib outlines: every in-scope page of each lib's `toc` indexes is a
# section/entry ref or a `skipped` page (stacks.py coverage). Outline modes' exit gate.
# Indexes are agent-editable, so fetches are anonymous https GETs only (no gh/GitHub token;
# GitHub tree API indexes work unauthenticated for public repos).
# Usage: stacks_coverage.sh [stack…]   (exit 1 when a page is missing or a skip is stale)
set -uo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root" || exit 2
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
stacks() { .claude/skills/feature/scripts/stacks.sh "$@"; }
stacks toc "$@" >"$tmp/toc" || exit 2
while read -r stack n url; do
  [[ $url =~ ^https://[^[:space:]]+$ ]] || { echo "bad toc url: $stack $url" >&2; continue; }
  env -u GH_TOKEN -u GITHUB_TOKEN -u NETRC curl -q -gsfL --proto =https --proto-redir =https --max-redirs 5 \
    --max-time 30 --url "$url" </dev/null >"$tmp/$stack.$n.txt" \
    || echo "fetch failed: $stack toc[$n] $url" >&2
done <"$tmp/toc"
stacks coverage --raw "$tmp" "$@"
