---
name: playbook-sync
description: Exchange improvements with the claude-project-template and ai-playbook repos. Promote universal lessons, pull newer shared machinery, or push improved machinery back to the template.
disable-model-invocation: true
argument-hint: "<promote | pull | push>"
arguments: [action]
allowed-tools: Bash(python3 .claude/scripts/ctx.py promote) Bash(python3 .claude/scripts/ctx.py check)
---
<!-- last-verified: 2026-10-01 -->
# Playbook sync: $action

Playbook (lessons + tooling): `${AI_PLAYBOOK_DIR:-~/CodeProjects/ai-playbook}` · Template (machinery source): `${AI_TEMPLATE_DIR:-~/CodeProjects/claude-project-template}`.

- **promote**: `python3 .claude/scripts/ctx.py promote` copies `universal` inbox entries to the playbook inbox.
- **pull**: run `<playbook>/bin/playbook-sync.sh pull "$CLAUDE_PROJECT_DIR"` (dry run first, then show the diff; `--apply` only after the user approves).
- **push**: run `<playbook>/bin/playbook-sync.sh push "$CLAUDE_PROJECT_DIR"` (same dry run → approve → `--apply` flow), then commit and push the template repo.

Only paths listed in `<template>/.playbook-managed` are synced. Project-specific content (AGENTS.md, filled rules) never moves.
After a pull, run `python3 .claude/scripts/ctx.py check`.
