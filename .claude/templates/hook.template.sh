#!/usr/bin/env bash
# Hook template. Wire it in settings.json:
#   "hooks": { "<Event>": [ { "matcher": "<pattern>", "hooks": [ { "type": "command",
#       "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/<name>.sh", "timeout": 30 } ] } ] }
#
# INPUT (stdin JSON), common fields: session_id, transcript_path, cwd, permission_mode, hook_event_name,
#   agent_id/agent_type (inside subagents) + event-specific fields (tool_name, tool_input, tool_response, prompt, source, ...)
# ENV: CLAUDE_PROJECT_DIR, plus everything in settings "env"; CLAUDE_CODE_REMOTE="true" in web sessions.
#
# OUTPUT
#   exit 0  → success. stdout JSON is parsed (plain stdout becomes context for SessionStart/UserPromptSubmit).
#   exit 2  → BLOCK (for blockable events); stderr goes to Claude.
#   other   → non-blocking error.
# JSON fields (any event):   {"continue": false, "stopReason": "...", "suppressOutput": true, "systemMessage": "..."}
# PreToolUse:                {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow|deny|ask","permissionDecisionReason":"...","updatedInput":{...}}}
# PermissionRequest:         {"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow|deny", ...}}}
# PostToolUse/Stop/SubagentStop/UserPromptSubmit/PostToolBatch: {"decision":"block","reason":"..."}
# Context injection:         {"hookSpecificOutput":{"hookEventName":"<Event>","additionalContext":"..."}}
# PermissionDenied:          {"hookSpecificOutput":{"hookEventName":"PermissionDenied","retry":true}}
source "$(dirname "$0")/_lib.sh"     # gives: $HOOK_INPUT, json_get, log, block, pretool_decision, add_context

event="$(json_get '.hook_event_name')"
log "fired"

# TODO(stub): your logic
exit 0
