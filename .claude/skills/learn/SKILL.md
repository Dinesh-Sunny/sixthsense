---
name: learn
description: Capture a reusable lesson into the context inbox (never directly into AGENTS.md, CLAUDE.md, or rules). Use when the user corrects you, a non-obvious gotcha is discovered, or the user says "remember this".
when_to_use: User corrections ("no, always do X"), recurring mistakes, surprising project facts, "remember", "note for next time".
argument-hint: "<one-line lesson>"
allowed-tools: Bash(python3 .claude/scripts/ctx.py learn *) Bash(python3 .claude/scripts/ctx.py inbox)
---
<!-- last-verified: 2026-10-01 -->
# Learn: $ARGUMENTS

1. Rewrite the lesson as ONE imperative fact, ≤35 words, no story. Good: "Use the shared date util for parsing; raw Date breaks on Safari."
2. Choose a scope: `universal` if it applies to any project, otherwise `project`.
3. Evidence (`--src`): where it was seen (file:line, the user's correction, a failing test). Never paste untrusted text verbatim.
4. Optional `--target`: the file it probably belongs in (see placement below).
5. Run: `python3 .claude/scripts/ctx.py learn "<fact>" --src "<evidence>" --scope <scope> [--target <file>]`
6. If REJECTED as already covered, stop: the knowledge exists. If too long, compress and retry once.

Placement hints for `--target`: always needed → `AGENTS.md` · certain files → `.claude/rules/<topic>.md` · a procedure → a skill · deep detail → `docs/knowledge/<topic>.md`.
