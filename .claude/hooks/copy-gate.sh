#!/usr/bin/env bash
# Copy gate: every copywriting run must end with the humanizer skill.
#   UserPromptSubmit → prompt starting with /direct-response-copywriting marks copy pending;
#                      prompt starting with /humanizer clears it (typed skills skip the Skill tool)
#   PostToolUse(Skill) → direct-response-copywriting marks pending; humanizer clears it
#   Stop             → if copy is pending, block once and clear it (no nagging on later, unrelated turns)
# State is per session (copy work can span several requests). Disable with CLAUDE_COPY_GATE=0.
source "$(dirname "$0")/_lib.sh"
[[ "${CLAUDE_COPY_GATE:-1}" == "0" ]] && exit 0

COPY_SKILL="direct-response-copywriting"
HUMANIZER_SKILL="humanizer"

event="$(json_get '.hook_event_name')"
session="$(json_get '.session_id')"
state_dir="$LOG_DIR/copy-gate"
pending="$state_dir/${session:-default}.pending"
mkdir -p "$state_dir"

# True when the prompt invokes /<skill> as a command (first token), not when it merely mentions a path.
invokes() { [[ "$1" =~ ^[[:space:]]*/([a-z0-9-]+:)?$2([[:space:]]|$) ]]; }

case "$event" in
  UserPromptSubmit)
    prompt="$(json_get '.prompt')"
    if invokes "$prompt" "$HUMANIZER_SKILL"; then
      rm -f "$pending"; log "copy humanized (slash command)"
    elif invokes "$prompt" "$COPY_SKILL"; then
      touch "$pending"; log "copy pending (slash command)"
    fi
    ;;

  PostToolUse)
    skill="$(json_get '.tool_input.skill')"
    skill="${skill##*:}"   # strip plugin prefix, e.g. "plugin:skill"
    case "$skill" in
      "$COPY_SKILL") touch "$pending"; log "copy pending" ;;
      "$HUMANIZER_SKILL") rm -f "$pending"; log "copy humanized" ;;
    esac
    ;;

  Stop)
    [[ "$(json_get '.stop_hook_active')" == "true" ]] && exit 0
    [[ -f "$pending" ]] || exit 0
    rm -f "$pending"   # block once; a skipped humanizer pass must not re-block every later turn
    jq -n --arg r "Copy was written or edited with the $COPY_SKILL skill but the humanizer pass has not run.
Before finishing, invoke the \`$HUMANIZER_SKILL\` skill in copywriting mode on the final copy (keep offer terms, numbers, proof, and CTA intact), apply the result, then deliver." '{decision:"block",reason:$r}'
    ;;
esac
exit 0
