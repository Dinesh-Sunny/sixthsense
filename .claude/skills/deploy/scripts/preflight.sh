#!/usr/bin/env bash
# Preflight checks for /deploy. Prints a report; exits non-zero on any failure.
env="${1:-staging}"; fail=0
echo "Preflight for: $env"
check() { if eval "$2" >/dev/null 2>&1; then echo "✅ $1"; else echo "❌ $1"; fail=1; fi; }
check "git repo"            "git rev-parse --is-inside-work-tree"
check "clean working tree"  "test -z \"\$(git status --porcelain)\""
check "on expected branch"  "test \"\$(git branch --show-current)\" = \"{{DEPLOY_BRANCH}}\" -o \"$env\" != production"
# TODO(stub): replace with real checks
# check "lint"       "{{LINT_CMD}}"
# check "typecheck"  "{{TYPECHECK_CMD}}"
# check "tests"      "{{TEST_CMD}}"
# check "build"      "{{BUILD_CMD}}"
exit $fail
