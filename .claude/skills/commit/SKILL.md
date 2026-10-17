---
name: commit
description: Stage and commit the current changes with a Conventional Commits message.
disable-model-invocation: true
argument-hint: "[optional message hint]"
model: haiku
effort: low
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git add *) Bash(git commit *) Bash(git log *)
---

# Commit

## Current state
- Status: !`git status --short 2>/dev/null || echo "not a git repo"`
- Staged diff: !`git diff --cached --stat 2>/dev/null`
- Unstaged diff: !`git diff --stat 2>/dev/null`
- Recent messages (match their style): !`git log --oneline -8 2>/dev/null`

## Steps
1. If nothing is staged, stage the files related to one logical change. Never stage `.env*`, secrets, or build output.
2. If the changes span unrelated concerns, propose splitting them into separate commits.
3. Message: `<type>(<scope>): <imperative subject ≤72 chars>`, blank line, body with the *why*.
   Types: feat, fix, refactor, perf, test, docs, build, ci, chore. Hint from user: $ARGUMENTS
4. Commit, then show `git log -1 --stat`.
Never push, amend, or use --no-verify unless the user asks.
