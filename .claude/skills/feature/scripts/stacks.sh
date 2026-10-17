#!/usr/bin/env bash
# Run stacks.py with its two deps (pyyaml, packaging) without touching the project's own env,
# so it works in Python, JS-only and monorepo projects alike, and never races a .venv sync.
here="$(cd "$(dirname "$0")" && pwd)"
if command -v uv >/dev/null; then
  exec uv run --no-project --quiet --python ">=3.11" --with pyyaml --with packaging python "$here/stacks.py" "$@"
fi
exec python3 "$here/stacks.py" "$@"  # needs: pip install pyyaml packaging
