<!--
  CLAUDE.md: thin Claude Code layer. Shared project instructions live in AGENTS.md (imported below).
  Put ONLY Claude Code-specific guidance here. Budget: ≤60 lines (enforced by .claude/scripts/ctx.py).
  last-verified: 2026-10-01
-->

@AGENTS.md

## Claude Code specifics

- Work in the main session; skills load procedures on demand: `/plan`, `/data-model`, `/test`. Review with `/review` before PRs.
- Big or risky change (new dep, auth/money/data, migration)? `/feature <request>`: sized S/M/L, per-stack experts, plan debate, approval gate.
- Subagents only for isolation: each re-reads context and spends tokens. `test-runner` runs automatically on haiku.
- Other subagents run only by command or name: `/review`, `/data-review`, `architect`, `security-auditor`, `debugger` (log-heavy hunts), `docs-writer`.
- Side task needing this conversation: fork with `/subtask`, not a fresh subagent. Question about the chat so far: `/btw`.
- Multi-file sweeps: workflows `/review-branch`, `/audit-codebase`.
- Learned something reusable? Run `/learn "<one-line lesson>"`. Never edit AGENTS.md, CLAUDE.md, or rules directly for lessons.
- Context files are linted on save (size, style, references). Fix reported violations immediately.
- Pasting into another AI chat? Run `/context-pack` and share `context-pack.md`.

## Map of Claude Code files

- `.claude/rules/`: always-loaded rules (no `paths:`) and path-scoped rules (`paths:`)
- `.claude/skills/`: feature, plan, review, data-model, data-review, commit, fix-issue, test, deploy, onboard, learn, docs-garden, context-pack, playbook-sync, project-conventions, direct-response-copywriting, humanizer
- `.claude/agents/`: feature-architect, feature-reviewer, stack-expert, advocate, judge (/feature only), code-reviewer, debugger, test-runner, architect, data-architect, security-auditor, docs-writer, context-curator
- `.claude/hooks/`: guard rails, formatter, session context, context lint, copy gate (humanizer after copywriting)
- `.claude/scripts/ctx.py`: context lint, budgets, refs, registry, adapter sync, packs, promote
- `.claude/stacks/`: stack registry + doc outlines (`lib/` shared across projects); run via `.claude/skills/feature/scripts/stacks.sh`
- `.claude/context.config.json`: budgets and style limits (single source of truth)
- `.claude/inbox.md`: staging for new lessons · `.claude/registry.json`: generated index of every context item
- `.claude/templates/`: blank templates · `SETTINGS_REFERENCE.md`: every settings key
