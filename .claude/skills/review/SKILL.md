---
name: review
description: Review the current branch's changes for bugs, security issues, and convention violations before a PR. Use when the user says "review", "check my changes", or before opening a PR.
argument-hint: "[base-branch | path]"
context: fork
agent: code-reviewer
background: false
effort: high
allowed-tools: Read Grep Glob Bash(git diff *) Bash(git log *) Bash(git status *)
disallowed-tools: Edit Write NotebookEdit
---

# Code review

Base / target: `$ARGUMENTS` (default: the merge-base with {{DEFAULT_BRANCH}}).

## Changed files
!`git diff --stat $(git merge-base HEAD origin/HEAD 2>/dev/null || echo HEAD~1) 2>/dev/null || echo "no git diff available"`

If a base branch or path was given above, diff against that instead.

## Instructions
1. Read every changed file in full, not just the hunks.
2. Apply [checklist.md](checklist.md).
3. Report findings ranked by severity: **blocker / major / minor / nit**.
   Format: `path:line - problem - concrete fix`.
4. End with a verdict: ✅ ready, ⚠️ ready after fixes, ❌ needs rework.
Do not modify files.
