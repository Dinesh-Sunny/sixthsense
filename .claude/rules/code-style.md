<!-- last-verified: 2026-10-01 -->
<!--
  Rule with no `paths:` frontmatter: loads at session start, like CLAUDE.md.
  Docs: https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/
-->
# Code style

- Match the style of the file you are editing before applying any rule below.
- Naming: n/a for this hackathon project
- Exports: n/a for this hackathon project
- Imports: n/a for this hackathon project; order: std/lib → external → internal → relative.
- Functions: small, single-purpose; early returns over nested conditionals.
- Types: n/a for this hackathon project
- Errors: raise on unexpected API errors; return `unknown` states for missing data. Never swallow errors silently.
- Constants and config live in `pipeline/modes.py`. No magic numbers or strings inline.
- Comments explain *why*. Delete commented-out code.
- Formatting is owned by no formatter (match the file). Don't hand-format; the PostToolUse hook runs it.
<!-- TODO(stub): replace  once the stack is chosen. -->
