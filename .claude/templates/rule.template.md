---
# Optional. Without `paths`, the rule loads at session start like CLAUDE.md.
# With `paths`, it loads only when Claude reads a matching file. Globs support ** and brace expansion {a,b}.
paths:
  - "src/{{area}}/**/*.{ts,tsx}"
  - "**/*.{{ext}}"
---
<!-- Block-level HTML comments are stripped before Claude sees the file. Subfolders are discovered (rules/frontend/react.md). -->

# {{Topic}} rules

- {{Imperative, specific, verifiable rule}}
- {{Prefer "Use X for Y" over vague "write clean code"}}
- {{Link to examples: see `path/to/canonical-example.ts`}}
