# Review checklist

## Correctness
- [ ] Logic matches the stated intent; edge cases (empty, null, large, concurrent) handled
- [ ] Error paths handled and surfaced; no swallowed errors
- [ ] No regressions to existing callers (search usages)

## Security
- [ ] Input validated at boundaries; no injection (SQL/shell/HTML)
- [ ] AuthZ enforced server-side; no secrets in code/logs
- [ ] New deps vetted

## Design & reuse
- [ ] Reuses existing utilities/components; no duplicated logic
- [ ] Follows project conventions (.claude/rules/*)
- [ ] Single source of truth for constants/types

## Tests
- [ ] New behavior covered; bug fixes have a regression test
- [ ] Tests are deterministic

## Performance
- [ ] No N+1 queries, unbounded loops/lists, or needless re-renders

## Docs
- [ ] Public APIs/config changes documented; CLAUDE.md updated if commands/structure changed
