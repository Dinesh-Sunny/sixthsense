---
name: plan
description: Write an implementation plan for a feature or change before any code is written. Use for any non-trivial task, multi-file change, or when the user says "plan", "design", "how should we build".
when_to_use: Trigger phrases - "plan this", "design X", "break this down", "what's the approach for". Skip for one-line fixes.
argument-hint: <feature or change description>
arguments: [goal]
model: inherit
effort: high
allowed-tools: Read Grep Glob WebFetch Bash(git log *) Bash(git diff *)
---

# Plan: $goal

ultrathink

Produce a plan; do NOT edit source files in this skill.

## Steps
1. Restate the goal in one sentence plus explicit acceptance criteria.
2. Explore: find the relevant existing code, patterns, utilities, and tests (reuse first).
3. Check current docs for any library you'll touch (Context7 / official docs).
4. Fill in [template.md](template.md) and write it to `docs/plans/<yyyy-mm-dd>-<slug>.md`.
5. List open questions that block the work. Ask the user only those.

## Context
- Branch: !`git branch --show-current 2>/dev/null || echo "not a git repo"`
- Recent commits: !`git log --oneline -10 2>/dev/null || true`
