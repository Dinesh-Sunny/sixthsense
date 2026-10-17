#!/usr/bin/env bash
# Build and publish a release to the `dist` branch; prints the dist commit SHA for deploy.sh.
#
#   bash scripts/release.sh
#
# The dist branch holds only what the pod needs: backend/{pyproject.toml,uv.lock,.python-version,src}
# + web/out. Each release is a new commit on top of the previous dist commit (old SHAs stay
# reachable for rollback, no force-push). Run from a clean checkout; guards run first.
# DRY_RUN=1 builds the commit locally and skips the push.
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel); cd "$ROOT"
SRC_SHA=$(git rev-parse --short HEAD)

echo "== backend guards"
(cd backend && uv lock --check && uv run ruff check && uv run pytest -q)

if [ -f web/package.json ]; then
  echo "== web build"
  (cd web && pnpm install --frozen-lockfile && pnpm build)
fi

STAGE=$(mktemp -d); IDX=$(mktemp -u); trap 'rm -rf "$STAGE" "$IDX"' EXIT
mkdir -p "$STAGE/backend"
cp backend/pyproject.toml backend/uv.lock backend/.python-version "$STAGE/backend/"
cp -r backend/src "$STAGE/backend/src"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
if [ -d web/out ]; then
  mkdir -p "$STAGE/web" && cp -r web/out "$STAGE/web/out"
else
  echo "warning: web/out missing - this release serves the API only"
fi

# Commit the staged tree without touching the working tree or the real index.
git fetch -q origin dist 2>/dev/null || true
PARENT=$(git rev-parse -q --verify origin/dist || true)
GITDIR=$(git rev-parse --absolute-git-dir)
TREE=$(cd "$STAGE" && GIT_INDEX_FILE="$IDX" git --git-dir="$GITDIR" --work-tree="$STAGE" add -A -f . \
  && GIT_INDEX_FILE="$IDX" git --git-dir="$GITDIR" write-tree)
MSG="dist: build of ${SRC_SHA}"
if [ -n "$PARENT" ]; then
  if [ "$(git rev-parse "$PARENT^{tree}")" = "$TREE" ]; then
    echo "no change since last dist commit"; echo "DIST_SHA=$PARENT"; exit 0
  fi
  COMMIT=$(git commit-tree "$TREE" -p "$PARENT" -m "$MSG")
else
  COMMIT=$(git commit-tree "$TREE" -m "$MSG")  # first release: orphan root
fi
if [ "${DRY_RUN:-0}" = 1 ]; then
  git ls-tree -r --name-only "$COMMIT" | sed 's|/.*||' | sort | uniq -c; echo "DRY_RUN: not pushed"; echo "DIST_SHA=$COMMIT"; exit 0
fi
git push origin "$COMMIT:refs/heads/dist"
echo "DIST_SHA=$COMMIT"
echo "On the VM: git pull && bash deploy.sh $COMMIT"
