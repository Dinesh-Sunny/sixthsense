---
# ===== Every SKILL.md frontmatter field (Claude Code). All are optional; `description` is recommended. =====
# Booleans accept true/false/yes/no/on/off/1/0.
name: my-skill                      # /command name. Default: directory name. Lowercase, hyphens.
description: >-                     # WHAT it does + WHEN to use it. Key use case first. Max 1,536 chars combined with when_to_use.
  Does X. Use when the user asks for Y or mentions Z.
when_to_use: >-                     # Extra trigger phrases or examples. Appended to description in the listing.
  "do X", "run Y on Z"
argument-hint: "<required> [optional]"   # Shown in / autocomplete.
arguments: [first, second]          # Named positional args → $first, $second. Also: $ARGUMENTS, $ARGUMENTS[0], $0, $1
disable-model-invocation: false     # true = only the user can run it via /name (deploys, commits). Also blocks preloading into subagents.
user-invocable: true                # false = hidden from the / menu; only Claude invokes it (background knowledge).
allowed-tools: Read Grep Glob Bash(git diff *)   # Pre-approved for the invoking turn. Space/comma string or YAML list.
disallowed-tools: AskUserQuestion   # Removed while the skill is active (until your next message).
model: inherit                      # inherit | sonnet | opus | haiku | fable | full model ID. Applies for the current turn.
effort: medium                      # low | medium | high | xhigh | max (depends on model). Overrides session effort.
context: fork                       # fork = run in an isolated subagent context (omit to run inline).
agent: general-purpose              # Subagent type used with context: fork (built-in or .claude/agents/<name>).
background: true                    # With context: fork. false = wait for the result in the same turn.
paths:                              # Auto-load only when working with matching files (same globs as rules).
  - "src/**/*.{ts,tsx}"
shell: bash                         # bash | powershell for !`cmd` and ```! blocks.
hooks:                              # Registered when the skill is invoked; persist for the session. once: true = remove after first success.
  PostToolUse:
    - matcher: "Edit|Write"
      hooks:
        - type: command
          command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-edit-format.sh"
          once: false
metadata:                           # Free-form map for your own tooling. Claude Code ignores it.
  owner: "{{TEAM}}"
  version: "0.1.0"
license: MIT                        # Agent Skills spec field. Accepted, not acted on.
compatibility: "Requires gh CLI and Node 22+"   # Agent Skills spec field (≤500 chars).
---

# {{Skill title}}

<!--
  Body = the prompt Claude follows when the skill runs.
  String substitutions: $ARGUMENTS · $ARGUMENTS[N] · $N · $<named-arg> · ${CLAUDE_SESSION_ID} · ${CLAUDE_EFFORT}
                        ${CLAUDE_SKILL_DIR} · ${CLAUDE_PROJECT_DIR}
  Dynamic context (runs BEFORE Claude sees the prompt; output is inlined):
    inline:  !`git status --short`
    block:   ```! ... ```
  Add the word "ultrathink" anywhere in the body to request deeper reasoning.
  Reference bundled files by relative link, e.g. [reference.md](reference.md). Claude reads them on demand.
  Only upload-safe fields (name, description, license, compatibility, metadata, allowed-tools) work on claude.ai or the Skills API.
-->

## Context
- Branch: !`git branch --show-current 2>/dev/null`

## Steps
1. {{step}}
2. {{step}}

## Output
{{expected output format}}

## Supporting files
- [reference.md](reference.md): {{detailed docs}}
- `scripts/{{helper}}.sh`: run via `${CLAUDE_SKILL_DIR}/scripts/{{helper}}.sh`
