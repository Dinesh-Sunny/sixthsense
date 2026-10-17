#!/usr/bin/env bash
# PostToolUse (matcher: Edit|Write). Copy guard: block (exit 2) when an edited UI file's prose breaks
# VOICE.md rules (banned words, product-name form, dashes, exclamation marks, emoji).
exec python3 "${CLAUDE_PROJECT_DIR:-.}/.claude/skills/direct-response-copywriting/scripts/voice-check.py" hook
