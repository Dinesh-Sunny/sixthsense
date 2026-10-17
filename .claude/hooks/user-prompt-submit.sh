#!/usr/bin/env bash
# UserPromptSubmit (no matcher). Runs before Claude sees each prompt.
# Options: exit 0 to pass through, add_context to inject text, or block with
#   {"decision":"block","reason":"..."} to reject the prompt.
source "$(dirname "$0")/_lib.sh"
prompt="$(json_get '.prompt')"
log "prompt_chars=${#prompt}"

# Example guard: stop pasted secrets from reaching the model.
if printf '%s' "$prompt" | grep -Eq '(sk-ant-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'; then
  jq -n '{decision:"block",reason:"Prompt appears to contain a secret (API key or private key). Remove it and resubmit."}'
  exit 0
fi

# TODO(stub): inject per-prompt context, e.g. add_context "UserPromptSubmit" "Current sprint goal: ..."
exit 0
