---
name: onboard
description: Give a guided tour of this codebase - structure, how to run it, key flows, and where to start.
disable-model-invocation: true
argument-hint: "[area to focus on]"
context: fork
agent: Explore
model: sonnet
effort: medium
---

# Onboard

Focus area (optional): $ARGUMENTS

Produce a concise tour:
1. What the project does (from CLAUDE.md / README).
2. How to install, run, and test it (exact commands).
3. Directory map with one line per top-level folder.
4. 2-3 key request/data flows traced through real files (`path:line`).
5. Where a new contributor should start, plus known gotchas.

Top-level files: !`ls -la 2>/dev/null | head -40`
