# .claude/templates/

Blank, fully annotated templates. Claude Code does NOT read this folder, so nothing here is active.
Copy a template into the right place to use it:

| Template | Copy to | Docs |
| --- | --- | --- |
| `SKILL.template.md` | `.claude/skills/<name>/SKILL.md` | https://code.claude.com/docs/en/skills |
| `agent.template.md` | `.claude/agents/<name>.md` | https://code.claude.com/docs/en/sub-agents |
| `rule.template.md` | `.claude/rules/<topic>.md` (subfolders OK) | https://code.claude.com/docs/en/memory |
| `output-style.template.md` | `.claude/output-styles/<name>.md` | https://code.claude.com/docs/en/output-styles |
| `command.template.md` | `.claude/commands/<name>.md` (legacy; prefer skills) | https://code.claude.com/docs/en/skills |
| `hook.template.sh` | `.claude/hooks/<name>.sh` + wire it in settings.json | https://code.claude.com/docs/en/hooks |
| `hooks.all-events.json` | merge the parts you need into `settings.json` → `hooks` | https://code.claude.com/docs/en/hooks |
| `workflow.template.js` | `.claude/workflows/<name>.js` | https://code.claude.com/docs/en/workflows |
| `knowledge.template.md` | `docs/knowledge/<topic>.md` (cold tier) | `.claude/context.config.json` |
| `settings.full.json` | pick keys into `settings.json` / `settings.local.json` | https://code.claude.com/docs/en/settings |

Every settings key is explained in `../SETTINGS_REFERENCE.md`.
