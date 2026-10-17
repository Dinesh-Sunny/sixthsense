---
name: deploy
description: Deploy the app to an environment after preflight checks.
disable-model-invocation: true
argument-hint: <staging|production>
arguments: [env]
model: inherit
effort: medium
shell: bash
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/preflight.sh *)
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'deploy skill active' >&2"
          once: true
---

# Deploy to $env

## Preflight
```!
"${CLAUDE_SKILL_DIR}/scripts/preflight.sh" "$env" || true
```

## Steps
1. Stop if preflight reported failures. Show them to the user.
2. `production` requires the user to explicitly type "yes, deploy production" in this conversation.
3. Deploy: `{{DEPLOY_CMD}} $env`   <!-- TODO(stub): e.g. vercel deploy --prod, fly deploy, ... -->
4. Smoke-test: `{{SMOKE_TEST_CMD}}` and report the URL and status.
5. If the smoke test fails: report and offer `{{ROLLBACK_CMD}}`. Do not roll back automatically.
