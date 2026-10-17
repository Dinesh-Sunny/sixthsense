<!-- last-verified: 2026-10-01 -->
# Knowledge base (cold tier)

Deep, task-specific knowledge. Nothing here loads automatically: Claude reads a doc when a task needs it, and hot files point here with one-line pointers.

## Rules
- One topic per file: `docs/knowledge/<topic>.md`, kebab-case.
- Start each file with `# Title`, a one-line summary, and `last-verified:`.
- Prose is allowed here; size budget only (see `.claude/context.config.json`).
- Outdated docs move to `docs/knowledge/archive/` with the date; they are never silently deleted.

## Index
<!-- /docs-garden keeps this list in sync with the registry. -->
- (empty)
