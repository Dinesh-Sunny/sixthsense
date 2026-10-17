---
# ===== Every subagent frontmatter field. `name` and `description` are required. camelCase must match exactly; unknown fields are silently ignored. =====
name: my-agent                  # Unique id (no ":"). Hooks receive it as agent_type.
description: >-                 # When Claude should delegate. Add "Use PROACTIVELY" to encourage auto-delegation.
  Expert in X. Use PROACTIVELY when Y.
tools: Read, Grep, Glob, Bash   # Allowlist (string or YAML list). Omit = inherit all tools. Use `skills` to preload skills, not "Skill".
disallowedTools: Edit, Write    # Denylist applied to inherited/listed tools. A specifier like Bash(git push *) removes the whole tool.
model: sonnet                   # sonnet | opus | haiku | fable | full ID (e.g. claude-opus-5-5) | inherit
permissionMode: default         # default | acceptEdits | auto | dontAsk | bypassPermissions | plan | manual (alias of default)
maxTurns: 30                    # Stop after N agentic turns (output marked partial, resumable).
skills:                         # Preloaded in full at startup.
  - project-conventions
mcpServers:                     # Server names from config, or inline definitions.
  - github
  # - my-inline:
  #     type: http
  #     url: https://mcp.example.com/mcp
hooks:                          # Active only while this subagent runs. A Stop hook here becomes SubagentStop.
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-bash.sh"
memory: project                 # user (~/.claude/agent-memory/<name>/) | project (.claude/agent-memory/<name>/) | local (.claude/agent-memory-local/<name>/)
background: false               # true = always run in the background.
omitClaudeMd: false             # true = skip user/project/local CLAUDE.md (agent gets everything from the delegation prompt).
effort: medium                  # low | medium | high | xhigh | max
isolation: worktree             # Run in a temporary git worktree; auto-cleaned if no changes.
color: blue                     # red | blue | green | yellow | purple | orange | pink | cyan
initialPrompt: "/onboard"       # First user turn when run as the MAIN agent (--agent / "agent" setting).
experimental:
  cacheTtl: 5m                  # 5m | 1h prompt-cache lifetime for this agent's requests.
---

<!-- Body = the subagent's system prompt. It does NOT see the main conversation, only the delegation prompt (+ CLAUDE.md unless omitClaudeMd). -->

You are {{role}} for this project.

## When invoked
1. {{first action}}
2. {{process}}

## Constraints
- {{e.g. Read-only. Never modify files.}}

## Output format
{{exact structure the main agent should get back: concise, with path:line references}}

## Memory
{{If memory is set: what to read from and write to MEMORY.md (first 200 lines / 25KB are auto-loaded).}}
