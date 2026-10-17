#!/usr/bin/env bash
# Vet candidate PyPI/npm libraries: health verdict (gates live in stacks.py) and whether they
# resolve against this project's current dependency set (throwaway copy; nothing installed).
# Usage: lib_check.sh [--npm] [--health-only] [--installed] <package>[==ver|@ver] ...
#   --health-only  skip the compatibility check
#   --installed    recheck an installed dep (stale = HEALTH_STALE_DAYS, no age gate); implies --health-only
# Verdict line (always one per package): PASS | FAIL <gates> | REVIEW unknown:<gates> | WATCHLIST young
set -uo pipefail
eco=pypi health_only=0 installed=()
while [ $# -gt 0 ] && [[ $1 == --* ]]; do
  case $1 in
    --npm) eco=npm ;;
    --health-only) health_only=1 ;;
    --installed) installed=(--installed) health_only=1 ;;
    *) echo "unknown flag: $1" >&2; exit 1 ;;
  esac
  shift
done
[ $# -eq 0 ] && { echo "usage: $0 [--npm] [--health-only] [--installed] <package>..." >&2; exit 1; }
root=$(git rev-parse --show-toplevel)
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

stacks() { "$root/.claude/skills/feature/scripts/stacks.sh" --root "$root" "$@"; }
get() { # <out> <url> [curl args]: save the body on HTTP success only; a missing file = unknown fact
  local out=$1 url=$2; shift 2
  curl -sfL --compressed --max-time 60 "$@" -o "$out" "$url" || rm -f "$out"
}
pkg_name() { # strip a version spec: pypi `name[extra]>=1`, npm `@scope/name@1`
  if [ "$eco" = npm ]; then local s=${1#@}; s=${s%%@*}; [[ $1 == @* ]] && s="@$s"; echo "$s"
  else echo "${1%%[=<>~!\[ ;]*}"; fi
}

for spec in "$@"; do
  pkg=$(pkg_name "$spec")
  raw="$tmp/raw-${pkg//\//_}"; mkdir -p "$raw"
  echo "== $pkg ($eco)"
  if [ "$eco" = pypi ]; then
    get "$raw/project.json" "https://pypi.org/pypi/$pkg/json"
    [ -f "$raw/project.json" ] || { echo "not found on PyPI"; echo "verdict: REVIEW unknown:registry"; continue; }
    get "$raw/simple.json" "https://pypi.org/simple/$pkg/" -H "Accept: application/vnd.pypi.simple.v1+json"
    lower=$(tr '[:upper:]' '[:lower:]' <<<"$pkg")
    cache="${TMPDIR:-/tmp}/lib_check-pypistats-$(date +%F)-$lower.json"  # pypistats: daily data, IP rate limit
    [ -s "$cache" ] || { sleep 1; get "$cache" "https://pypistats.org/api/packages/$lower/recent?period=month"; }
    [ -s "$cache" ] && cp "$cache" "$raw/downloads.json"
  else
    enc=${pkg/\//%2F}
    get "$raw/packument.json" "https://registry.npmjs.org/$enc"
    [ -f "$raw/packument.json" ] || { echo "not found on npm"; echo "verdict: REVIEW unknown:registry"; continue; }
    get "$raw/downloads.json" "https://api.npmjs.org/downloads/point/last-month/$enc"
  fi
  repo=$(stacks facts "$eco" "$pkg" --raw "$raw" | jq -r '.repo // empty')
  if [ -n "$repo" ]; then
    gh api "repos/$repo" >"$raw/repo.json" 2>/dev/null || rm -f "$raw/repo.json"
    since=$(stacks since --days 180)
    gh api "repos/$repo/commits?since=$since&per_page=100" >"$raw/commits.json" 2>/dev/null \
      || rm -f "$raw/commits.json"
  fi
  facts=$(stacks facts "$eco" "$pkg" --raw "$raw")
  jq -r 'def s: if . == null then "?" else tostring end;
    "latest: \(.version | s) released \(.last_release | s) (first \(.first_release | s))",
    "license: \(.license | s | .[0:60])  downloads/month: \(.downloads | s)",
    "repo: \(.repo | s) owner=\(.owner_type | s) archived=\(.archived | s) deprecated=\(.deprecated | s) committers(180d)=\(.maintainers | s)"' <<<"$facts"
  if [ "$eco" = npm ]; then  # informational only, never a gate (bundlephobia is flaky)
    size=$(curl -sf --max-time 20 "https://bundlephobia.com/api/size?package=$enc" \
      | jq -er 'select(.gzip) | "\(.gzip) B gzip, \(.dependencyCount) deps"' 2>/dev/null)
    echo "bundle: ${size:-?}"
  fi
  echo "verdict: $(stacks verdict ${installed[@]+"${installed[@]}"} <<<"$facts")"
done
[ "$health_only" -eq 1 ] && exit 0

# Compatibility: resolve candidates against a throwaway copy of the project.
echo "== compatibility with current deps"
if [ "$eco" = pypi ]; then
  pins() { awk '/^name = /{n=$3} /^version = /{print n, $3}' "$1" | tr -d '"' | sort -u; }
  # Manifests only (root + uv workspace members), so monorepos resolve like the real repo.
  rsync -a --prune-empty-dirs --exclude node_modules --exclude .venv --include '*/' \
    --include pyproject.toml --include uv.lock --include README.md --exclude '*' "$root/" "$tmp/"
  old=$root/uv.lock new=$tmp/uv.lock
  (cd "$tmp" && uv add --no-sync --quiet "$@" 2>"$tmp/err")
else
  pins() { # `name version` per lockfile package key, both lock documents
    awk -v q="'" '/^packages:/{p=1; next} /^[^ ]/{p=0}
      p && /^  [^ ]/ {k=$0; gsub(/^  |:$/, "", k); gsub(q, "", k); i=index(substr(k, 2), "@") + 1
        print substr(k, 1, i - 1), substr(k, i + 1)}' "$1" | sort -u
  }
  # The pnpm project: a monorepo root lock, else a web/ app. Copy every manifest so workspace
  # packages resolve; LIB_CHECK_FILTER=<pkg> adds to one workspace package (e.g. web).
  dir=.; [ -f "$root/pnpm-lock.yaml" ] || dir=web
  rsync -a --prune-empty-dirs --exclude node_modules --exclude .next --include '*/' \
    --include package.json --include 'pnpm-*.yaml' --exclude '*' "$root/$dir/" "$tmp/$dir/"
  old=$root/$dir/pnpm-lock.yaml new=$tmp/$dir/pnpm-lock.yaml
  (cd "$tmp/$dir" && pnpm add ${LIB_CHECK_FILTER:+--filter "$LIB_CHECK_FILTER"} --lockfile-only \
    --ignore-scripts --silent "$@" >/dev/null 2>"$tmp/err")
fi
if [ $? -eq 0 ]; then
  echo "OK: resolves"
  before=$(pins "$old") after=$(pins "$new")
  names() { cut -d' ' -f1 | sort -u; }
  added=$(comm -13 <(names <<<"$before") <(names <<<"$after"))
  echo "new packages: $(grep -c . <<<"$added")"
  changed=$(diff <(echo "$before") <(echo "$after") | grep '^[<>]' \
    | awk 'NR==FNR {old[$1]; next} ($2 in old)' <(echo "$before") - )
  echo "${changed:-no version changes to existing packages}" | head -40
else
  echo "CONFLICT:"; tail -20 "$tmp/err"
fi
