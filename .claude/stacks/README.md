# Stack registry
One row per stack (closely coupled packages share a row). Grammar, guards and staleness:
`.claude/rules/stacks.md`. Outlines are concept indexes built from live docs: portable
`lib/<stack>.yaml` + this repo's `usage/<stack>.yaml`, read via generated `view/<stack>.md`;
grep by lens or id, then fetch only the entries' refs. Run everything through
`.claude/skills/feature/scripts/stacks.sh` (`guards`, `view`, `drift`, `validate`).
Health of installed deps: `stacks_check.sh`; vetting candidates: `lib_check.sh`.

`lib/` ships with outlines shared across projects (synced by playbook-sync); `catalog.md` holds
researched rows. Fill this table with `stacks.sh bootstrap --write` (new-project.sh does it), then
`stacks.sh view`. Rows marked `bootstrap …: assess` still need a decision: outline-build or utility.
Wire each row's `mcp:` servers in `.mcp.json` and add them to the `tools:` of the /feature agents.

## Stacks
| stack | packages | version | docs | outline | ai_tooling | choke point | health |
|---|---|---|---|---|---|---|---|

## Watchlist
| candidate | for | failed gate | reason | date |
|---|---|---|---|---|
