---
name: test
description: Write or run tests for a file, module, or the current changes. Use when the user asks for tests, coverage, or "make sure this works".
argument-hint: "[path | 'changed']"
paths:
  - "src/**"
  - "tests/**"
effort: medium
---

# Test: $ARGUMENTS

1. Find the target: the path in the heading or, if empty, the changed files: !`git diff --name-only HEAD 2>/dev/null | head -50`
2. Read the existing tests nearby; copy their structure, helpers, and fixtures.
3. Cover: happy path, edge cases, error paths, and regressions for any bug fixed.
4. Run `{{TEST_FILE_CMD}} <file>`, then iterate until green. Don't weaken assertions to pass.
5. Report what is covered and any gaps left on purpose.
Follow .claude/rules/testing.md.
