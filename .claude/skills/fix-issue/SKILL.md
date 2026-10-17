---
name: fix-issue
description: Fix a GitHub issue end to end - read it, reproduce it, write a failing test, fix it, verify.
argument-hint: <issue-number>
arguments: [issue]
effort: high
allowed-tools: Bash(gh issue view *) Bash(gh issue list *) Read Grep Glob
---

# Fix issue #$issue

## Issue
!`gh issue view $issue --comments 2>/dev/null || echo "gh unavailable or issue not found - ask the user for details"`

## Steps
1. Summarize the problem and the expected behavior.
2. Locate the code and reproduce it (a failing test, or exact repro steps).
3. Create a branch `fix/$issue-<slug>`.
4. Write a failing regression test → implement the minimal fix → test passes.
5. Run lint, type-check, and the related test suites.
6. Summarize the root cause, the fix, and the tests. Suggest a commit message `fix: ... (#$issue)`.
