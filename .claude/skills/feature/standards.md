# Engineering standards (single source; read by feature-architect, stack-expert, feature-reviewer, advocate, judge)

## Library-first
0. Check the stack registry (`.claude/stacks/README.md`) and grep every stack's outline for
   entries that solve or enhance the task, not only the stacks being edited.
1. Reuse codebase code. 2. Use an installed dependency's most advanced first-class API. 3. Else
   scout a new dependency (gates below). 4. Hand-write only uncovered business logic; justify it.
Every API/signature comes from docs fetched this session for the installed version, never memory.
Docs order: the stack's official MCP → its official skill → its llms.txt → context7 → web via
`agent-browser`. Outlines are indexes: fetch an entry's ref before coding against it; entries in
a stale outline (version ≠ installed, `verified` >90 days) are unverified.

Lenses: best-practice · perf · composability · reuse · typing-dx · testing · observability · security · cost · ux-a11y · reliability

## Scouting gates (all must pass; 0 suggestions is the normal outcome, ≤2 per task)
1. Real need: a named capability no installed lib can do, citing the outline entries checked.
2. Worth a dependency: hard or solved problems only; small stable logic is hand-written.
3. Health: `lib_check.sh` verdict PASS (REVIEW → a human decides; thresholds in `stacks.py`).
4. Cost: lockfile diff and bundle size stated; no forced moves of existing pins.
5. Exit plan: one importer (ruff banned-api + per-file allowance / ESLint `no-restricted-imports`),
   recorded as the registry row's choke point [guard: N7].
Official AI tooling is a plus, never a bypass. Scouting may propose removing a dep. Rejected or
deferred candidates go to architect `decisions.md` and the registry watchlist.
AI tooling (MCP servers, skills): official sources only, version-pinned or locked, a skill's text
diff reviewed before re-locking; a new MCP or skill only through the approval gate.

## Placement
Sources in order: framework's current structure/file-convention docs → language packaging
and style standards → existing repo layout (if repo deviates from docs, stay consistent and
flag it; never reorganize unasked). Extend the owning module before adding a file. One
concern per module. No catch-all utils/helpers unless docs prescribe them. Shared code,
constants, types, config: one home, imported not copied. No stray files.

## Senior checklist (apply what's relevant)
correctness & edge cases · library-native retries/timeouts · security (secrets from config,
validation, injection incl. prompt injection, least privilege) · typed interfaces & backward
compat · native logging/tracing · cost/perf (redundant calls, N+1) · deps (bounds, runtime vs
dev, license) · deterministic tests at the right level, no network · remove dead code.

## Enforcement (every practice, every concept)
A new concept starts from its current docs' best-practices/production pages. Each practice
adopted ships with: 1. a choke point when possible; 2. an executable guard: a lint ban (ruff banned-api,
ESLint `no-restricted-imports`) or a convention test, proven to bite (break it, guard
fails); 3. a `.claude/rules/<topic>.md` entry naming its guard, `paths:` broad enough for new
dirs. Prose-only rules are for judgment calls; mark them `(unenforced: <why>)`. Stack guards:
N1-N5 via `stacks.sh guards` (CI); N6/N7 are per-project convention tests (`.claude/rules/stacks.md`).

## Docs
Concise, repo style; comments say why, not what. README/CLAUDE.md only for changed commands,
setup or user-facing behavior. No boilerplate.

## Shared facts (`.claude/plans/<slug>.facts.md`)
Read it before researching; don't re-verify a listed fact (reviewers may, and strike wrong ones).
Append-only, re-read before writing: `- fact — ref (file:line or doc URL), version`.

## Memory hygiene (all agents with memory)
- `MEMORY.md` = index only, one line per topic file. Topic files: terse facts with version/date
  and doc ref or file:line; nothing derivable from code, git, or a stack outline.
- Check a note's version against the lockfile before trusting it; update, delete or merge stale
  notes. Rules that apply every time an area is edited → propose a path-scoped rule.
