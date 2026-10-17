#!/usr/bin/env bash
# Stop: tell the user once per drift set when stack outlines lag the installed version or
# are stale (stacks.py drift); at most weekly, launch the unattended refresh
# (stacks_refresh.sh) in the background and surface its last result once. stdout carries
# ONLY the JSON systemMessage: plain stdout on exit 0 would become Claude context and
# continue the turn.
exec 3>&1 1>/dev/null
input=$(cat)
[ "$(jq -r '.stop_hook_active' <<<"$input")" = "true" ] && exit 0
[ -n "${STACKS_REFRESH:-}" ] && exit 0  # inside the refresh's own headless session
cd "$CLAUDE_PROJECT_DIR" || exit 0
marker="$(git rev-parse --git-dir)/stack-drift-seen"
state="$(git rev-parse --path-format=absolute --git-common-dir)/stacks-refresh"
msgs=()

# Weekly gate on the launch stamp, so a failing run is not retried every turn. Close fd 3 in
# the child: Claude Code waits for EOF on the hook's stdout.
mkdir -p "$state"
if [ -z "$(find "$state/last" -mtime -7 2>/dev/null)" ]; then
  touch "$state/last"
  nohup .claude/skills/feature/scripts/stacks_refresh.sh </dev/null >>"$state/log" 2>&1 3>&- &
  msgs+=("Weekly stack refresh started in the background (log: $state/log).")
fi
if [ -s "$state/result" ]; then
  msgs+=("Last stack refresh: $(cat "$state/result")")
  mv "$state/result" "$state/result.seen"
fi

# stacks.sh runs outside the project env, so it never races other Stop hooks on .venv.
[ -f .claude/stacks/README.md ] || exit 0
if out=$(.claude/skills/feature/scripts/stacks.sh drift 2>&1); then
  drift="Stack outlines drifted (unverified until the weekly refresh lands): $(head -10 <<<"$out" | tr '\n' ';')"
else
  drift="stack drift check failed; run: .claude/skills/feature/scripts/stacks.sh drift"
  out="failed"  # stable signature: tracebacks vary
fi
if [ -z "$out" ]; then
  rm -f "$marker"
else
  sig=$(shasum <<<"$out" | cut -d' ' -f1)
  if ! { [ -f "$marker" ] && [ "$(cat "$marker")" = "$sig" ]; }; then
    echo "$sig" >"$marker"
    msgs+=("$drift")
  fi
fi

[ ${#msgs[@]} -eq 0 ] && exit 0
jq -n --arg m "${msgs[*]}" '{systemMessage: $m}' >&3
