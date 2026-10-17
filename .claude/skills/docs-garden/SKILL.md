---
name: docs-garden
description: Curate the AI context system. Process the inbox, enforce budgets, fix stale or broken entries, re-tier content, regenerate the registry and adapters, then show the diff for approval.
disable-model-invocation: true
argument-hint: "[focus: inbox | budget | stale | all]"
context: fork
agent: context-curator
background: false
effort: high
---
<!-- last-verified: 2026-10-01 -->
# Docs garden ($ARGUMENTS)

## Current health
!`python3 .claude/scripts/ctx.py status 2>&1 | head -40`

## Budgets
!`python3 .claude/scripts/ctx.py budget 2>&1 | tail -15`

## Inbox
!`python3 .claude/scripts/ctx.py inbox 2>&1`

Follow your curator playbook. Finish with `python3 .claude/scripts/ctx.py check` passing, then report:
before/after hot tokens, entries placed/merged/archived/rejected, and files changed. Leave changes uncommitted for review.
