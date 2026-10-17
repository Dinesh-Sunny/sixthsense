#!/usr/bin/env bash
# PostToolUse (matcher: Edit|Write). Lints AI context files on save: budgets, style, secrets, references.
# Errors → exit 2 (Claude must fix). Warnings → additionalContext. Non-context files are ignored.
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/scripts/ctx.py" lint --hook
