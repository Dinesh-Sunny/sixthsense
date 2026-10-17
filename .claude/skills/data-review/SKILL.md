---
name: data-review
description: Independent review of a schema or migration change by the data-architect subagent.
argument-hint: "[base-branch | path | design doc]"
disable-model-invocation: true
context: fork
agent: data-architect
background: false
allowed-tools: Read Grep Glob Bash(git diff *) Bash(git log *) Bash(git status *)
---
<!-- last-verified: 2026-10-03 -->
# Data model review

Target: `$ARGUMENTS` (default: the merge-base with the default branch).

## Changed data files
!`git diff --stat $(git merge-base HEAD origin/HEAD 2>/dev/null || echo HEAD~1) -- '*schema*' '*migrations*' '*/payload/collections/*' '*.sql' 2>/dev/null || echo "no git diff available"`

If a base branch, path, or design doc was given above, review that instead.
