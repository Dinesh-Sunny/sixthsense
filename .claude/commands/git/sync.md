---
description: Sync the current branch with the default branch (fetch + rebase), stopping on conflicts.
argument-hint: "[base-branch]"
allowed-tools: Bash(git fetch *) Bash(git rebase *) Bash(git status *) Bash(git log *) Bash(git branch *)
disable-model-invocation: true
---
<!--
  LEGACY command format (single file). Invoked as /git:sync (subfolder → namespace).
  For anything new, prefer .claude/skills/<name>/SKILL.md: same frontmatter, plus bundled files.
-->
Current branch: !`git branch --show-current 2>/dev/null`

1. `git fetch origin`
2. Rebase onto `origin/$ARGUMENTS` (default branch if empty: !`git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main`).
3. On conflict: stop, list the conflicted files, and explain each one. Do NOT auto-resolve or abort without asking.
4. Show `git log --oneline -5` when done.
