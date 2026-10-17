---
name: feature
description: Senior-engineer pipeline for any non-trivial code change. Design with doc-verified libraries and per-stack experts, debate the plan, approval gate, implement, verify, review, then learn. Use for features, refactors, anything beyond a one-line fix.
argument-hint: <what to build or change> [--tier S|M|L] [--no-debate]
---

Request: $ARGUMENTS

Quality per token: spend an agent only where it can change the outcome. Keep main context lean:
subagents explore and review; carry forward only their outputs. Standards: `standards.md` (this dir).
Token economy: subagents start without this thread, so briefs carry only what they need; pass
file paths plus the sections to read (e.g. "plan § Library & API decisions"), never paste plans.
Plans/briefs live in `.claude/plans/`; caps: plan ≤150 lines, brief ≤60, decisions ≤80. Every
agent prompt says: write your output file by half your maxTurns, then refine it.

0. **Size**: classify the domain (app code | web | harness `.claude/` | docs | deps/infra |
   auth/money/data) and the intent (fix | refactor | feature | integration | migration), then
   pick the tier; state domain, intent, tier and a one-line why first (`--tier` overrides).
   Domain and intent decide who runs; any match for a higher tier wins; file count breaks ties.
   S = fix/refactor with no new API or dep, or harness/docs edits already scoped: plan in main
   thread (≤10 lines), skip steps 1-4 (keep step 4 when it edits hooks or settings), implement, verify, one narrow `feature-reviewer` if >50 lines.
   M = feature or integration with one new dep/concept: steps 1-2 with experts only for the
   domains touched (≤2), debate R1 only, review = `feature-reviewer` + experts for stacks changed.
   L = migration, auth/money/data, cross-cutting, or ≥2 new deps: every step below.
1. **Design**: a new dep named in the request, once `lib_check.sh [--npm] <pkg>` passes, is added first (package manager command from AGENTS.md › Commands) so every agent reads installed source (a failing check: don't install); give the architect the lock diff (version moves = conflicts); revert it if not approved. Launch `feature-architect` with the request (minus flags), a plan slug, and only the decisions/facts from this thread it can't find in the repo. Don't explore yourself first.
2. **Per-stack**: launch `stack-expert` in design mode per ecosystem, not per package (langchain + langgraph + langsmith + Agent Server = one; next + react = one), only for stacks the plan touches or whose capability it adopts, all in parallel (one message), with stack, version, plan path and the plan sections to read (Stacks involved, Library & API decisions, its stack's rows). A fresh `feature-architect` revises only for `[must]` items (plan + brief paths); the implementer applies `[should]` and `[adopt]` items from the briefs. Resume an agent only for a quick follow-up (it reloads its transcript).
3. **Debate** (S or `--no-debate`: skip): R1: `advocate` devil + angel in parallel (slug, round, plan + brief paths) → `judge` (`model: opus` on L) → `<slug>.decisions.md`. R2 (L only): devil + angel answer only points the judge marked `contested` → `judge` finalizes. Decisions are acceptance criteria; the implementer applies them directly, and a fresh `feature-architect` revises the plan only when they restructure it. A stack expert rechecks only an API that no brief verified. No user questions here.
4. **Approval gate**: read the plan file; show its summary, the decisions log (assumptions flagged), one line per stack brief plus its `[adopt]` opportunities, required new deps (an early install is reverted if declined), optional stack suggestions + `later` items, and judge escalations (product intent, money/credentials, irreversible or outward-facing) with their defaults. Wait. On feedback, revise as in step 2. Skip only if the user said to.
5. **Implement**: exactly the plan's APIs, placement, docs style. Fetch an outline entry's ref before coding against it. If the plan is wrong, stop and say so. Deps via the package manager commands in AGENTS.md; never hand-edit manifests.
6. **Verify**: the Verify command in AGENTS.md › Commands, plus `.claude/skills/feature/scripts/stacks.sh guards`, until green (`stop-check.sh` enforces).
7. **Review**: in parallel, per tier (step 0), given the plan, decisions and brief paths; stack experts in review mode run their stack's official AI checks. Fix blockers/majors, re-verify, re-run only reviewers that had them, narrowed to those findings (`model: haiku` for narrowed re-runs and rechecks). Minor: fix if cheap, else list.
8. **Learn**: collect every "Proposed rules" item and the plan's enforcement table. Each durable practice gets its guard per standards › Enforcement (lint ban or convention test, shown to fail when broken) plus a rule naming it. Create or extend `.claude/rules/<topic>.md` (with `paths:` frontmatter) only for rules that are durable, specific, and not already covered; merge rather than append; keep each rule file under ~40 lines. Update outlines (only here; experts list deltas under `## Outline updates`, one `stack-expert` in outline mode or the main thread applies them): adopted entries → `usage/<stack>.yaml` `status: used` + `paths`, new portable facts → `lib/`, then `stacks.sh view`; registry rows and watchlist. Update CLAUDE.md if commands, deps, conventions, or layout changed. Run `.claude/skills/feature/scripts/context_budget.sh`; if anything is over budget, condense it.
9. **Report**: files changed, API decisions per stack with doc refs, decisions adopted, leverage used, suggestions accepted/rejected, outline changes, verification result, rules + guards added, open minors.
