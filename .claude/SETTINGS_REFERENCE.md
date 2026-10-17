# Settings reference

<!-- Generated from the official JSON schema (https://json.schemastore.org/claude-code-settings.json) on 2026-10-01.
     Regenerate when Claude Code updates: re-download the schema and re-run the generator, or ask Claude to "refresh SETTINGS_REFERENCE.md from the latest schema". -->

Docs: [settings](https://code.claude.com/docs/en/settings) · [permissions](https://code.claude.com/docs/en/permissions) · [hooks](https://code.claude.com/docs/en/hooks) · [env vars](https://code.claude.com/docs/en/env-vars) · [sandboxing](https://code.claude.com/docs/en/sandboxing)

## Where settings live (highest precedence first)

| # | Source | Scope | Committed |
| --- | --- | --- | --- |
| 1 | Managed settings (MDM / `/Library/Application Support/ClaudeCode/managed-settings.json` / server-managed) | Organization | admin |
| 2 | CLI flags (`--settings`, `--model`, `--permission-mode`, ...) | One session | n/a |
| 3 | `.claude/settings.local.json` | You, this project | no (gitignored) |
| 4 | `.claude/settings.json` | Team, this project | yes |
| 5 | `~/.claude/settings.json` | You, all projects | no |

Arrays (e.g. `permissions.allow`) **merge** across sources. Scalars (e.g. `model`) take the **most specific** value.
So a value set in project `settings.json` overrides your personal `~/.claude/settings.json`. Keep personal preferences out of it.

## Files in this setup

| File | Purpose |
| --- | --- |
| `.claude/settings.json` | **Live** team config: permissions, hooks, status line, MCP approvals, sandbox (off), worktree |
| `.claude/settings.local.json` | **Live** personal overrides (empty arrays to fill) |
| `.claude/templates/settings.full.json` | **Not loaded.** Every non-managed key with an example value |
| `.claude/templates/hooks.all-events.json` | **Not loaded.** All 33 hook events and all 5 handler types |
| `.mcp.json` | Project MCP servers (6 stub servers, all listed in `disabledMcpjsonServers`) |

## Permission rule syntax (cheat sheet)

| Rule | Matches |
| --- | --- |
| `Bash(npm test *)` | commands starting with `npm test` (each subcommand of `&&`/`;`/`\|` is checked) |
| `Read(./.env)` / `Edit(/src/**/*.ts)` | gitignore-style paths: `./` or `/` = relative to the settings file, `~/` = home, `//` = absolute |
| `WebFetch(domain:example.com)` | fetches to that domain |
| `mcp__github` / `mcp__github__*` / `mcp__github__create_issue` | a server's tools / one tool |
| `Agent(Explore)` / `Agent(model:opus)` / `Agent(isolation:worktree)` | subagent use |
| `Skill(name)` | a skill |

Evaluation order: **deny → ask → allow**. A `Read` deny also blocks Edit/Write on that path.
`defaultMode`: `default` · `acceptEdits` · `plan` · `auto` · `dontAsk` · `bypassPermissions`.

## Hook events (33)

`Setup`, `SessionStart`, `InstructionsLoaded`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `TeammateIdle`, `Notification`, `MessageDisplay`, `Stop`, `StopFailure`, `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove`, `Elicitation`, `ElicitationResult`, `SessionEnd`

Handler types: `command` · `http` · `mcp_tool` · `prompt` · `agent`. Common fields: `type`, `if`, `timeout`, `statusMessage`, `once` (skills only).
Command-only fields: `command`, `args` (exec form), `async`, `asyncRewake`, `shell`. HTTP: `url`, `headers`, `allowedEnvVars`. MCP: `server`, `tool`, `input`. Prompt/agent: `prompt`, `model`.

## All settings keys (user / project / local)

| Key | Type / values | Where to put it | Description |
| --- | --- | --- | --- |
| `apiKeyHelper` | string | personal → `settings.local.json` / `~/.claude` | Path to a script that outputs authentication values. |
| `autoMemoryEnabled` | boolean | project or personal | Enable automatic memory saves that capture useful context to ~/.claude/projects/<project>/memory/ (derived from the git repository, shared across worktrees). Also configurable via CLAUDE_CODE_DISABLE_AUTO_MEMORY environment variable (set to 1 to disable, 0 to enable). |
| `autoUpdatesChannel` | `stable` \| `latest` | personal → `settings.local.json` / `~/.claude` | Release channel to follow for updates. Use "stable" for a version that is typically about one week old and skips versions with major regressions, or "latest" (default) for the most recent release. Set DISABLE_AUTOUPDATER=1 to disable background auto-updates, or DISABLE_UPDATES=1 (added in v2.1.118) to block all update paths including manual `claude update`. |
| `awsCredentialExport` | string | personal → `settings.local.json` / `~/.claude` | Command that outputs AWS credentials as JSON (in the form {"Credentials": {"AccessKeyId": ..., "SecretAccessKey": ..., "SessionToken": ...}}). The output is captured silently. Use when you cannot modify the .aws directory and must return credentials directly. |
| `awsAuthRefresh` | string | personal → `settings.local.json` / `~/.claude` | Command to run when AWS credentials are expired or unavailable; its output is shown to the user but interactive input is not supported. Also drives the "Claude Platform on AWS · refresh credentials" option in /login when configured. |
| `claudeMdExcludes` | array | **live** in settings.json | Glob patterns for CLAUDE.md files to exclude from loading. Useful in monorepos to skip irrelevant instructions from other teams. Patterns match against absolute file paths. Arrays merge across settings layers. Managed policy CLAUDE.md files cannot be excluded. |
| `cleanupPeriodDays` | integer | personal → `settings.local.json` / `~/.claude` | Number of days to retain sessions, orphaned subagent worktrees, tasks, shell snapshots, and backups. Minimum is 1; setting 0 is rejected with a validation error. |
| `env` | object | **live** in settings.json | Environment variables to set for Claude Code sessions. Many environment variables provide settings dimensions not available as dedicated settings.json properties (e.g., thinking tokens, prompt caching, bash timeouts, shell configuration). for the full list. |
| &nbsp;&nbsp;`env.ANTHROPIC_API_KEY` | string | | API key for Anthropic API authentication |
| &nbsp;&nbsp;`env.ANTHROPIC_AUTH_TOKEN` | string | | Custom Authorization header bearer token for API requests |
| &nbsp;&nbsp;`env.ANTHROPIC_AWS_API_KEY` | string | | Workspace API key for Claude Platform on AWS; takes precedence over SigV4 authentication. |
| &nbsp;&nbsp;`env.ANTHROPIC_AWS_BASE_URL` | string | | Override the Claude Platform on AWS endpoint URL. Default is https://aws-external-anthropic.{region}.api.aws. |
| &nbsp;&nbsp;`env.ANTHROPIC_AWS_WORKSPACE_ID` | string | | Required workspace ID for Claude Platform on AWS; sent as the anthropic-workspace-id header on every request. |
| &nbsp;&nbsp;`env.ANTHROPIC_BASE_URL` | string | | Override API endpoint URL for proxy or gateway routing |
| &nbsp;&nbsp;`env.ANTHROPIC_BEDROCK_BASE_URL` | string | | Override Amazon Bedrock endpoint URL |
| &nbsp;&nbsp;`env.ANTHROPIC_BEDROCK_MANTLE_BASE_URL` | string | | Override Bedrock Mantle endpoint URL |
| &nbsp;&nbsp;`env.ANTHROPIC_BEDROCK_SERVICE_TIER` | `default` \| `flex` \| `priority` | | Select Bedrock service tier; sent as X-Amzn-Bedrock-Service-Tier header. |
| &nbsp;&nbsp;`env.ANTHROPIC_BETAS` | string | | Comma-separated beta header values to include in API requests |
| &nbsp;&nbsp;`env.ANTHROPIC_CUSTOM_HEADERS` | string | | Custom HTTP headers for API requests (newline-separated 'Name: Value' pairs) |
| &nbsp;&nbsp;`env.ANTHROPIC_CUSTOM_MODEL_OPTION` | string | | Custom model ID to add as an entry in the model picker |
| &nbsp;&nbsp;`env.ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION` | string | | Display description for the custom model in the model picker |
| &nbsp;&nbsp;`env.ANTHROPIC_CUSTOM_MODEL_OPTION_NAME` | string | | Display name for the custom model in the model picker |
| &nbsp;&nbsp;`env.ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES` | string | | JSON object specifying capability flags for the custom model |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_FABLE_MODEL` | string | | Override the default Fable-class model ID. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_FABLE_MODEL_DESCRIPTION` | string | | Display description shown for the Fable model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_FABLE_MODEL_NAME` | string | | Display name shown for the Fable model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_FABLE_MODEL_SUPPORTED_CAPABILITIES` | string | | Comma-separated list of capabilities the pinned Fable model supports. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_HAIKU_MODEL` | string | | Override default Haiku model ID |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_HAIKU_MODEL_DESCRIPTION` | string | | Display description shown for the Haiku model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME` | string | | Display name shown for the Haiku model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES` | string | | Comma-separated list of capabilities the pinned Haiku model supports. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_OPUS_MODEL` | string | | Override default Opus model ID |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION` | string | | Display description shown for the Opus model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_OPUS_MODEL_NAME` | string | | Display name shown for the Opus model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES` | string | | Comma-separated list of capabilities the pinned Opus model supports. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_SONNET_MODEL` | string | | Override default Sonnet model ID |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_SONNET_MODEL_DESCRIPTION` | string | | Display description shown for the Sonnet model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_SONNET_MODEL_NAME` | string | | Display name shown for the Sonnet model in the model picker. |
| &nbsp;&nbsp;`env.ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES` | string | | Comma-separated list of capabilities the pinned Sonnet model supports. |
| &nbsp;&nbsp;`env.ANTHROPIC_FOUNDRY_API_KEY` | string | | Microsoft Foundry authentication key |
| &nbsp;&nbsp;`env.ANTHROPIC_FOUNDRY_AUTH_TOKEN` | string | | Bearer token for Microsoft Foundry authentication, such as a Microsoft Entra access token. Claude Code sends it as the Authorization: Bearer header. Takes precedence over ANTHROPIC_FOUNDRY_API_KEY and over the Azure default credential chain. Requires Claude Code v2.1.203 or later. |
| &nbsp;&nbsp;`env.ANTHROPIC_FOUNDRY_BASE_URL` | string | | Microsoft Foundry resource URL |
| &nbsp;&nbsp;`env.ANTHROPIC_FOUNDRY_RESOURCE` | string | | Microsoft Foundry resource name |
| &nbsp;&nbsp;`env.ANTHROPIC_MODEL` | string | | Model to use (e.g., 'claude-opus-4-1', 'claude-sonnet-4-5-20250514', 'opus', 'sonnet', 'haiku') |
| &nbsp;&nbsp;`env.ANTHROPIC_SMALL_FAST_MODEL` | string | | DEPRECATED (prefer ANTHROPIC_DEFAULT_HAIKU_MODEL). Haiku-class model to use for background and low-complexity tasks (e.g., 'claude-3-5-haiku-latest') |
| &nbsp;&nbsp;`env.ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION` | string | | Override the AWS region for the Haiku-class model on Bedrock and Bedrock Mantle. Has no effect without ANTHROPIC_DEFAULT_HAIKU_MODEL (or the deprecated ANTHROPIC_SMALL_FAST_MODEL) set on Bedrock. |
| &nbsp;&nbsp;`env.ANTHROPIC_VERTEX_BASE_URL` | string | | Override Google Cloud's Agent Platform (formerly Vertex AI) endpoint URL. Use for custom endpoints or when routing through an LLM gateway |
| &nbsp;&nbsp;`env.ANTHROPIC_VERTEX_PROJECT_ID` | string | | GCP project ID for Google Cloud's Agent Platform (formerly Vertex AI) requests. Overridden by GCLOUD_PROJECT, GOOGLE_CLOUD_PROJECT, or the project in your GOOGLE_APPLICATION_CREDENTIALS credential file |
| &nbsp;&nbsp;`env.ANTHROPIC_WORKSPACE_ID` | string | | Workspace ID for workload identity federation. Scopes the minted token to a specific workspace when the federation rule covers more than one. |
| &nbsp;&nbsp;`env.API_FORCE_IDLE_TIMEOUT` | string | | Override the 5-minute idle timeout for streaming responses (0 disables it). |
| &nbsp;&nbsp;`env.API_TIMEOUT_MS` | string | | Timeout for API requests in milliseconds (default: 600000, or 10 minutes; maximum: 2147483647). Increase this when requests time out on slow networks or when routing through a proxy. Values above the maximum overflow the underlying timer and cause requests to fail immediately. |
| &nbsp;&nbsp;`env.AWS_BEARER_TOKEN_BEDROCK` | string | | Bearer token for Bedrock API authentication |
| &nbsp;&nbsp;`env.AWS_REGION` | string | | AWS region for Amazon Bedrock and Claude Platform on AWS requests (e.g. us-east-1). |
| &nbsp;&nbsp;`env.BASH_DEFAULT_TIMEOUT_MS` | string | | Default bash command timeout in milliseconds (default: 120000) |
| &nbsp;&nbsp;`env.BASH_MAX_OUTPUT_LENGTH` | string | | Maximum bash output characters before truncation |
| &nbsp;&nbsp;`env.BASH_MAX_TIMEOUT_MS` | string | | Maximum bash command timeout in milliseconds (default: 600000) |
| &nbsp;&nbsp;`env.BETA_TRACING_ENDPOINT` | string | | Endpoint that, together with ENABLE_BETA_TRACING_DETAILED=1, activates detailed beta tracing spans (e.g. claude_code.hook). |
| &nbsp;&nbsp;`env.CCR_FORCE_BUNDLE` | `0` \| `1` | | Force local repo bundling for --remote invocations |
| &nbsp;&nbsp;`env.CLAUDECODE` | `0` \| `1` | | Set to 1 in subprocesses Claude Code spawns (Bash and PowerShell tools, tmux sessions, hook commands, status line commands, stdio MCP server subprocesses). IDE extensions also set this in their integrated terminals. To distinguish a direct tool/hook subprocess from a stdio MCP server subprocess, use CLAUDE_CODE_CHILD_SESSION instead. |
| &nbsp;&nbsp;`env.CLAUDE_AFK_COUNTDOWN_MS` | string | | How many milliseconds before auto-continue the on-screen countdown appears on an unanswered AskUserQuestion dialog. Default 20000 (20 seconds). See CLAUDE_AFK_TIMEOUT_MS. Requires Claude Code v2.1.198 or later. |
| &nbsp;&nbsp;`env.CLAUDE_AFK_TIMEOUT_MS` | string | | How many milliseconds of idle time before an unanswered AskUserQuestion dialog auto-continues without you. Default 60000 (60 seconds). Requires Claude Code v2.1.198 or later. |
| &nbsp;&nbsp;`env.CLAUDE_AGENT_SDK_DISABLE_BUILTIN_AGENTS` | `0` \| `1` | | Disable built-in subagent types in Agent SDK |
| &nbsp;&nbsp;`env.CLAUDE_AGENT_SDK_MCP_NO_PREFIX` | `0` \| `1` | | Skip 'mcp__<server>__' prefix on MCP tool names in Agent SDK |
| &nbsp;&nbsp;`env.CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS` | string | | Stall timeout for background subagents in milliseconds (default 600000). The timer resets on each streaming progress event; if no progress arrives within the window the subagent is aborted and the task is marked failed, surfacing any partial result to the parent. |
| &nbsp;&nbsp;`env.CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | string | | Context capacity percentage threshold for auto-compaction (1-100) |
| &nbsp;&nbsp;`env.CLAUDE_AUTO_BACKGROUND_TASKS` | `0` \| `1` | | Force-enable automatic backgrounding of tasks |
| &nbsp;&nbsp;`env.CLAUDE_AX_SCREEN_READER` | `0` \| `1` | | Set to 1 to render screen-reader friendly output: flat text without decorative borders or animations. Set to 0 to force screen-reader mode off even when axScreenReader is true. The --ax-screen-reader flag takes precedence. Requires Claude Code v2.1.181 or later. |
| &nbsp;&nbsp;`env.CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | `0` \| `1` | | Return to original project directory after each bash command |
| &nbsp;&nbsp;`env.CLAUDE_CLIENT_PRESENCE_FILE` | string | | Path to a file whose existence marks the user as present; while it exists, mobile push notifications are skipped (v2.1.181+). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ACCESSIBILITY` | `0` \| `1` | | Keep native cursor visible for screen magnifiers and assistive tools |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | `0` \| `1` | | Load CLAUDE.md memory files from additional directories |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ALT_SCREEN_FULL_REPAINT` | `0` \| `1` | | Force a full-screen repaint on every frame in fullscreen mode. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | `0` \| `1` | | Send the effort parameter for all models, not just those with effort enabled by default. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_API_KEY_HELPER_TTL_MS` | string | | Credential helper refresh interval in milliseconds |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ARTIFACT_AUTO_OPEN` | `0` \| `1` | | Set to 0 to stop auto-opening the browser when a new artifact is created. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ATTRIBUTION_HEADER` | `0` \| `1` | | Include attribution block in the system prompt |
| &nbsp;&nbsp;`env.CLAUDE_CODE_AUTO_COMPACT_WINDOW` | string | | Context capacity for compaction calculations in tokens |
| &nbsp;&nbsp;`env.CLAUDE_CODE_AUTO_CONNECT_IDE` | `true` \| `false` | | Override automatic IDE connection behavior |
| &nbsp;&nbsp;`env.CLAUDE_CODE_AWS_CHAIN_RESOLVE_TIMEOUT_MS` | string | | Time in milliseconds Claude Code waits for the AWS default credential provider chain to produce credentials before the request fails with "AWS default-chain credential resolve timed out" (default: 60000). Raise it when a step in your chain legitimately needs longer, such as a browser-based SSO sign-in with MFA through a wrapper like aws-vault. Applies wherever Claude Code signs with the default chain. Requires Claude Code v2.1.207 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_BRIDGE_SESSION_ID` | string | | Set automatically in Bash tool and hook command subprocesses while the session has an active Remote Control connection, and removed when the connection ends. The value is the session's ID in session_ form, the same identifier that appears in the session's claude.ai/code URL, so a script can link back to the session that ran it. Requires Claude Code v2.1.199 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_CERT_STORE` | string | | CA certificate sources (comma-separated: 'bundled', 'system') |
| &nbsp;&nbsp;`env.CLAUDE_CODE_CHILD_SESSION` | `0` \| `1` | | Set by Claude Code to 1 in nested subprocesses (Bash, PowerShell, Monitor, hook commands, status-line commands) to distinguish nested sessions from a top-level claude launched in IDE terminals (v2.1.172+). A nested interactive claude TUI started this way is excluded from --resume, --continue, up-arrow history, and the claude agents list; non-interactive claude -p sessions still persist (override with CLAUDE_CODE_FORCE_SESSION_PERSISTENCE=1). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_CLIENT_CERT` | string | | Client certificate file path for mutual TLS |
| &nbsp;&nbsp;`env.CLAUDE_CODE_CLIENT_KEY` | string | | Client private key file path for mutual TLS |
| &nbsp;&nbsp;`env.CLAUDE_CODE_CLIENT_KEY_PASSPHRASE` | string | | Passphrase for encrypted client private key |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DEBUG_LOGS_DIR` | string | | Override the debug log file path. Despite the name, this is a file path, not a directory. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DEBUG_LOG_LEVEL` | `verbose` \| `debug` \| `info` \| `warn` \| `error` | | Debug log verbosity level |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_1M_CONTEXT` | `0` \| `1` | | Disable 1M context window models |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | `0` \| `1` | | Disable adaptive reasoning |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_ADVISOR_TOOL` | `0` \| `1` | | Disable the server-side advisor tool. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_AGENT_VIEW` | `0` \| `1` | | Turn off background agents and agent view (claude agents, --bg, /background, and the on-demand supervisor). Equivalent to the disableAgentView setting. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN` | `0` \| `1` | | Disable alternate screen buffer rendering. When set to 1, keeps conversation in native scrollback instead of fullscreen renderer |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_ARTIFACT` | `0` \| `1` | | Disable the Artifact tool. Equivalent to setting disableArtifact. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_ATTACHMENTS` | `0` \| `1` | | Disable attachment processing |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_AUTO_MEMORY` | `0` \| `1` | | Disable automatic memory feature |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | `0` \| `1` | | Disable all background task functionality |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_BEDROCK_CONTENT_TYPE_GUARD` | `0` \| `1` | | Set to 1 to skip the check that an Amazon Bedrock streaming response carries the application/vnd.amazon.eventstream content-type. Without this variable, a response with a different content-type fails with an error naming that content-type, which means a gateway or proxy is transforming the response. Set it only when the gateway rewrites the Content-Type header but passes the binary event-stream body through unmodified; if the body itself was transformed, requests fail with "Truncated event message received" instead. Requires Claude Code v2.1.208 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_BG_EXIT_HANDOFF` | `0` \| `1` | | Set to 1 to stop a background session's running background shell commands, dynamic workflows, and (as of v2.1.198) background subagents when the supervisor stops, restarts, or updates that session's process, instead of handing them off to the session's next process. Affects only that handoff; CLAUDE_DISABLE_ADOPT turns off both. Requires Claude Code v2.1.196 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP` | `0` \| `1` | | UNDOCUMENTED. Disable automatic memory-pressure reaping of idle background shell commands (added v2.1.193). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_BUNDLED_SKILLS` | `0` \| `1` | | Disable the skills and workflows bundled with Claude Code (plugins and project .claude/skills are unaffected). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_CLAUDE_MDS` | `0` \| `1` | | Prevent loading CLAUDE.md memory files |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_CRON` | `0` \| `1` | | Disable scheduled/cron tasks |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | `0` \| `1` | | Strip anthropic-beta headers from API requests. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_EXPLORE_PLAN_AGENTS` | `0` \| `1` | | Set to 1 to disable the built-in Explore and Plan subagents. Requires Claude Code v2.1.198 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_FAST_MODE` | `0` \| `1` | | Disable fast mode toggle |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY` | `0` \| `1` | | Disable session quality feedback surveys |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_FILE_CHECKPOINTING` | `0` \| `1` | | Disable file checkpointing for /rewind |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS` | `0` \| `1` | | Remove git commit and PR workflow instructions from the system prompt |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_LEGACY_MODEL_REMAP` | `0` \| `1` | | Prevent automatic remapping of legacy model names |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_MOUSE` | `0` \| `1` | | Disable mouse tracking in fullscreen mode. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_MOUSE_CLICKS` | `0` \| `1` | | Disable mouse click/drag/hover in fullscreen mode while keeping wheel scroll (requires v2.1.195+). CLAUDE_CODE_DISABLE_MOUSE takes precedence when both variables are set. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `0` \| `1` | | Disable auto-update checks, telemetry, and feedback in one setting |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK` | `0` \| `1` | | Disable fallback to non-streaming API mode |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_NOTIFICATION_PRESENCE_CHECK` | `0` \| `1` | | Set to 1 to send desktop notifications from the PushNotification tool even while focused on the terminal. Requires Claude Code v2.1.193 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_OFFICIAL_MARKETPLACE_AUTOINSTALL` | `0` \| `1` | | Skip automatic installation of official marketplace plugins. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_POLICY_SKILLS` | `0` \| `1` | | Skip loading system-wide policy skills. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_TERMINAL_TITLE` | `0` \| `1` | | Disable terminal title updates |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_THINKING` | `0` \| `1` | | Force-disable extended thinking |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_VIRTUAL_SCROLL` | `0` \| `1` | | Disable virtual scrolling in fullscreen mode |
| &nbsp;&nbsp;`env.CLAUDE_CODE_DISABLE_WORKFLOWS` | `0` \| `1` | | Set to 1 to disable workflows. Equivalent to the disableWorkflows setting. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_EFFORT_LEVEL` | `low` \| `medium` \| `high` \| `xhigh` \| `max` \| `auto` | | Reasoning effort level |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_APPEND_SUBAGENT_PROMPT` | `0` \| `1` | | Set to 1 to enable appending extra text to the end of every subagent's system prompt. The --append-subagent-system-prompt flag supplies the appended text and sets this variable automatically, so you do not need to set it yourself. Requires Claude Code v2.1.205 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_AUTO_MODE` | `0` \| `1` | | Set to 1 to make auto mode available on Amazon Bedrock, Google Cloud Vertex AI, and Microsoft Foundry (requires v2.1.158+; no effect on the Anthropic API where auto mode is available by default). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_AWAY_SUMMARY` | `0` \| `1` | | Override session recap/away summary availability |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH` | `0` \| `1` | | Refresh plugins at turn boundaries. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_FEEDBACK_SURVEY_FOR_OTEL` | `0` \| `1` | | Enable feedback survey collection via OpenTelemetry for enterprises |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING` | `0` \| `1` | | Force fine-grained tool output streaming |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` | `0` \| `1` | | Enable model discovery from LLM gateway /v1/models endpoint when ANTHROPIC_BASE_URL points at an Anthropic-compatible gateway |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION` | `true` \| `false` | | Enable prompt suggestions |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_SDK_FILE_CHECKPOINTING` | string | | Enable file checkpointing for a non-interactive CLI run, so `claude -p --resume <session-id> --rewind-files <checkpoint-uuid>` can rewind files. The Agent SDK sets this internally when enable_file_checkpointing (Python) or enableFileCheckpointing (TypeScript) is enabled; the bare CLI never sets it. Without it, a non-interactive rewind fails with "File rewinding is not enabled". |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_TASKS` | `0` \| `1` | | Enable task tracking in non-interactive mode |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENABLE_TELEMETRY` | `0` \| `1` | | Set to 1 to enable telemetry collection. Required for all OpenTelemetry integration. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_ENHANCED_TELEMETRY_BETA` | `0` \| `1` | | Enable the enhanced telemetry (tracing) beta. ENABLE_ENHANCED_TELEMETRY_BETA is also accepted. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | string | | Wait time in milliseconds before auto-exit after stop |
| &nbsp;&nbsp;`env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `0` \| `1` | | Enable experimental agent teams feature |
| &nbsp;&nbsp;`env.CLAUDE_CODE_EXTRA_BODY` | string | | JSON object to merge into every API request body |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | string | | Token limit for file read operations |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FORCE_SESSION_PERSISTENCE` | `0` \| `1` | | Set to 1 to override the automatic exclusion of nested interactive claude TUI sessions from --resume, --continue, up-arrow history, and the claude agents list (requires v2.1.172+). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FORCE_STRIKETHROUGH` | `0` \| `1` | | Set to 1 to force strikethrough rendering for ~~text~~ in Claude's responses when the terminal supports it but is not auto-detected, such as over SSH without TERM_PROGRAM forwarded. Without this, undetected terminals show the literal ~~ markers. Requires Claude Code v2.1.186 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FORCE_SYNC_OUTPUT` | `0` \| `1` | | Force synchronous output flushing. When set to 1, forces synchronized output on terminals that auto-detection misses (e.g., Emacs eat) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FORK_SUBAGENT` | `0` \| `1` | | Fork subagent processes in non-interactive sessions. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_FORWARD_SUBAGENT_TEXT` | `0` \| `1` | | Set to 1 to emit subagent text and thinking blocks in claude -p --output-format stream-json output, the same behavior as the --forward-subagent-text flag. Use the variable when a harness invokes claude and cannot pass the flag itself. Unlike the flag, which exits with an error outside non-interactive mode with stream-json output, the variable is ignored there so that nested invocations keep working when it is set process-wide. Requires Claude Code v2.1.211 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_GIT_BASH_PATH` | string | | Path to Git Bash executable (Windows only) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_GLOB_HIDDEN` | `true` \| `false` | | Include dotfiles/hidden files in Glob results |
| &nbsp;&nbsp;`env.CLAUDE_CODE_GLOB_NO_IGNORE` | `true` \| `false` | | Don't respect .gitignore rules in Glob results |
| &nbsp;&nbsp;`env.CLAUDE_CODE_GLOB_TIMEOUT_SECONDS` | string | | Glob tool timeout in seconds (default: 20-60) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_HIDE_CWD` | `0` \| `1` | | Hide the working directory in the startup logo. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_IDE_HOST_OVERRIDE` | string | | Override IDE connection address |
| &nbsp;&nbsp;`env.CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL` | `0` \| `1` | | Skip automatic IDE extension installation |
| &nbsp;&nbsp;`env.CLAUDE_CODE_IDE_SKIP_VALID_CHECK` | `0` \| `1` | | Skip IDE lockfile validation |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | string | | How many subagents can be running in one session before the Agent tool refuses to spawn another (default: 20). Accepts a positive whole number in plain digits; anything else is ignored, so the variable can adjust the cap but cannot disable it. Requires Claude Code v2.1.217 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_CONTEXT_TOKENS` | string | | Override context window size in tokens |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_OUTPUT_TOKENS` | string | | Maximum output tokens per API request |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_RETRIES` | string | | Maximum API request retry attempts (default: 10) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` | string | | Cap on the number of subagents one session can spawn with the Agent tool (default: 200). When Claude reaches the cap, spawning another subagent fails with an error telling Claude to finish the remaining work directly. Accepts a positive whole number in plain digits with no upper bound; this variable does not take the scientific notation or digit-separator spellings. Anything else is ignored and the default applies, so the cap can be raised but not turned off. Requires Claude Code v2.1.212 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | string | | Number of subagent layers allowed below the main conversation (default: 1). At the default, subagents cannot spawn their own subagents; set 2 or higher to allow it. Accepts a positive whole number in plain digits; anything else is ignored, so the limit can be raised but not turned off. Requires Claude Code v2.1.217 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | string | | Maximum parallel tool executions (default: 10) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_TURNS` | string | | Cap the number of agentic turns when no explicit limit is passed. Equivalent to --max-turns, which takes precedence. A non-positive integer is rejected at startup. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` | string | | Cap on the total number of WebSearch calls one session can make (default: 200). When Claude reaches the cap, further WebSearch calls return a notice telling it to continue with the information it already gathered. Accepts a positive whole number with no upper bound. Anything else is ignored and the default applies, so the cap can be raised but not turned off. Requires Claude Code v2.1.212 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MCP_ALLOWLIST_ENV` | `0` \| `1` | | Isolate MCP server environments to allowlisted variables |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS` | string | | Elapsed time in milliseconds before a still-running MCP tool call moves to a background task (default: 120000, or 2 minutes). Set to 0 to turn automatic backgrounding off. Requires Claude Code v2.1.212 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` | string | | Idle timeout in milliseconds for MCP tool calls. When a stdio, HTTP, SSE, WebSocket, or claude.ai connector MCP server sends no response and no progress notification for this long, the tool call aborts with an error instead of waiting for the overall MCP_TOOL_TIMEOUT. Overrides the per-transport defaults of 300000 (5 minutes) for network servers and 1800000 (30 minutes) for stdio servers. Set to 0 to disable the idle check. Values below 1000 are raised to one second, and the value is capped at the effective MCP_TOOL_TIMEOUT. A per-server timeout in .mcp.json of at least 1000 raises that server's idle window to at least the timeout value. Does not apply to IDE servers or SDK in-process servers. Requires Claude Code v2.1.187 or later. Before v2.1.203, stdio servers were exempt from the idle timeout. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_NATIVE_CURSOR` | `0` \| `1` | | Set to 1 to show the terminal's own cursor at the input caret instead of a drawn block. The cursor respects the terminal's blink, shape, and focus settings. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_NEW_INIT` | `0` \| `1` | | Use the interactive /init setup flow |
| &nbsp;&nbsp;`env.CLAUDE_CODE_NO_FLICKER` | `0` \| `1` | | Enable fullscreen rendering mode to reduce flicker |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OAUTH_REFRESH_TOKEN` | string | | OAuth refresh token |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OAUTH_SCOPES` | string | | OAuth scopes (space-separated) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OAUTH_TOKEN` | string | | OAuth access token |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH` | string | | Maximum length of content-bearing OpenTelemetry attributes (model responses, tool content, system prompts, raw API bodies), truncation marker included, in UTF-16 code units (default: 61440, i.e. 60 KB). Raise it only if your telemetry backend accepts attribute values larger than 64 KB, or lower it to cut telemetry volume. Requires Claude Code v2.1.214 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OTEL_DIAG_STDERR` | `0` \| `1` | | Set to 1 to write OpenTelemetry exporter diagnostic errors to stderr (otherwise shown only with --debug). Requires v2.1.179+. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OTEL_FLUSH_TIMEOUT_MS` | string | | OpenTelemetry span flush timeout in milliseconds (default: 5000) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS` | string | | OpenTelemetry header helper refresh interval in milliseconds |
| &nbsp;&nbsp;`env.CLAUDE_CODE_OTEL_SHUTDOWN_TIMEOUT_MS` | string | | OpenTelemetry shutdown timeout in milliseconds (default: 2000) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE` | `0` \| `1` | | Enable automatic package manager updates. When set, Claude Code runs the upgrade command in background on Homebrew/WinGet and prompts to restart |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PERFORCE_MODE` | `0` \| `1` | | Enable Perforce write protection mode |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PLUGIN_CACHE_DIR` | string | | Override the plugins root directory. Despite the name, this sets the parent directory, not the cache itself: marketplaces and the plugin cache live in subdirectories under this path. Defaults to ~/.claude/plugins. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PLUGIN_GIT_TIMEOUT_MS` | string | | Plugin marketplace git operations timeout in milliseconds (default: 120000). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE` | `0` \| `1` | | Keep plugin cache on update failure |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PLUGIN_PREFER_HTTPS` | `0` \| `1` | | Set to 1 to clone GitHub owner/repo plugin sources over HTTPS instead of SSH. Useful in CI runners, containers, or environments without a configured SSH key for github.com. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PLUGIN_SEED_DIR` | string | | Path(s) to pre-populated plugin directories. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_POWERSHELL_RESPECT_EXECUTION_POLICY` | `0` \| `1` | | Set to 1 to stop Claude Code from passing -ExecutionPolicy Bypass when spawning PowerShell for tool calls, hooks, and status line commands. By default Claude Code bypasses execution policy so .ps1 scripts work on default-Restricted Windows installs. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS` | string | | Cap, in milliseconds, on how long `claude -p` waits for background subagents at exit (default 10 minutes; set to 0 to wait without limit, added v2.1.182). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PROCESS_WRAPPER` | string | | Launch the processes Claude Code starts from its own binary, such as the background service that hosts agent view sessions, through a corporate launcher given as an argv prefix like /opt/corp/launcher. Set it in the env block of user or managed settings, not as a shell export, so the detached background service inherits it; project and local settings cannot set it. Equivalent to the processWrapper setting, which requires Claude Code v2.1.210 or later; this variable takes precedence when both are set. The VS Code extension configures its own launcher separately through its claudeProcessWrapper setting. Ignored on Windows. Requires Claude Code v2.1.208 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PROPAGATE_TRACEPARENT` | `0` \| `1` | | Propagate the W3C traceparent header on API requests when using a custom ANTHROPIC_BASE_URL. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST` | `0` \| `1` | | Indicate that the host application manages provider routing |
| &nbsp;&nbsp;`env.CLAUDE_CODE_PROXY_RESOLVES_HOSTS` | `0` \| `1` | | Allow proxy to handle DNS resolution |
| &nbsp;&nbsp;`env.CLAUDE_CODE_REMOTE` | `true` \| `false` | | Indicates a remote web environment session |
| &nbsp;&nbsp;`env.CLAUDE_CODE_REMOTE_SESSION_ID` | string | | Cloud session identifier for remote sessions |
| &nbsp;&nbsp;`env.CLAUDE_CODE_RESUME_INTERRUPTED_TURN` | `0` \| `1` | | Automatically resume from a mid-turn interruption |
| &nbsp;&nbsp;`env.CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | string | | Maximum age in milliseconds of the last transcript message for a session that ended mid-turn to continue automatically on resume. When the last message is older than this bound, Claude Code skips both the CLAUDE_CODE_RESUME_INTERRUPTED_TURN automatic resume and the injected CLAUDE_CODE_RESUME_PROMPT continuation message, and the session starts idle so you continue explicitly. Unset or 0 means no bound; a negative or non-numeric value applies a one-hour bound. Spawn scripts for long-running agents can set this so a restart against an old transcript does not re-run a stale prompt. Claude Code sets a one-hour bound itself when it restarts a crashed agent view session that inherited its conversation from an interactive session. Requires Claude Code v2.1.211 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_RESUME_PROMPT` | string | | Override the continuation message injected when resuming a session that ended mid-turn (default "Continue from where you left off."). An empty string uses the default. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_RETRY_WATCHDOG` | `0` \| `1` | | Set to 1 for unattended sessions (eval harnesses, CI, remote workers) to retry 429/529 capacity errors indefinitely, backing off up to 5 minutes, instead of failing after CLAUDE_CODE_MAX_RETRIES. Requires v2.1.186+. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SAFE_MODE` | `0` \| `1` | | Set to 1 to start in safe mode: CLAUDE.md, skills, plugins, hooks, MCP servers, custom commands and agents, output styles, workflows, custom themes, custom keybindings, status line and file-suggestion commands, LSP servers, and auto-memory do not load, for troubleshooting a broken configuration. Managed settings policy still applies. Equivalent to passing --safe-mode; directly spawned child processes inherit the variable. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SCRIPT_CAPS` | string | | Script invocation limits (JSON object) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SCROLL_SPEED` | string | | Set the mouse wheel scroll multiplier in fullscreen rendering. Accepts any positive value up to 20, including fractional values below 1 such as 0.5 to slow accelerated trackpad and wheel scrolling in terminals that already amplify wheel events. Set to 3 to match vim if your terminal sends one wheel event per notch without amplification. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` | string | | Override the time budget in milliseconds for SessionEnd hooks (default 1500, raised up to 60000 by the highest configured per-hook timeout). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SESSION_ID` | string | | Set automatically to the current session ID in Bash/PowerShell tool subprocesses, hook command subprocesses, and stdio MCP server subprocesses. Read-only. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SHELL` | string | | Override automatic shell detection (e.g., '/bin/zsh', '/bin/bash') |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SHELL_PREFIX` | string | | Command prefix wrapper for shell commands |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SIMPLE` | `0` \| `1` | | Minimal mode with core tools only |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SIMPLE_SYSTEM_PROMPT` | `0` \| `1` | | Use a shortened system prompt |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH` | `0` \| `1` | | Skip client-side SigV4 authentication for Claude Platform on AWS; use when a proxy or gateway adds authentication before forwarding. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_AWS_CRED_CACHE` | `0` \| `1` | | Set to 1 to turn off the in-process cache of credentials resolved from the AWS default credential provider chain, so Claude Code resolves the chain on every API request. With the cache off, an SSO-backed profile requests credentials from IAM Identity Center on every request. Requires Claude Code v2.1.207 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_BEDROCK_AUTH` | `0` \| `1` | | Skip AWS authentication for Bedrock |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_FAST_MODE_NETWORK_ERRORS` | `0` \| `1` | | Set to 1 to treat a failed fast mode availability check as available, for networks that block the check's direct request to api.anthropic.com. Claude Code still honors a "disabled by your organization" response. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_FAST_MODE_ORG_CHECK` | `0` \| `1` | | Set to 1 to skip the client-side fast mode availability check, for proxies that intercept the check's request rather than refuse it. The API still rejects fast mode requests when your organization has fast mode disabled. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_FOUNDRY_AUTH` | `0` \| `1` | | Skip Azure authentication for Foundry |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_MANTLE_AUTH` | `0` \| `1` | | Skip AWS authentication for Bedrock Mantle (for example, when using an LLM gateway). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_PROMPT_HISTORY` | `0` \| `1` | | Disable transcript writes entirely. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SKIP_VERTEX_AUTH` | `0` \| `1` | | Skip Google authentication for Google Cloud's Agent Platform |
| &nbsp;&nbsp;`env.CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` | string | | Override the default maximum consecutive Stop hook blocks (default: 8) before the turn ends with a warning. Raise this when a stop hook legitimately needs more than 8 iterations to converge. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SUBAGENT_MODEL` | string | | Override model used by subagents |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | `0` \| `1` | | Strip credentials from subprocess environments |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNC_PLUGIN_INSTALL` | `0` \| `1` | | Wait synchronously for plugin installation |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNC_PLUGIN_INSTALL_TIMEOUT_MS` | string | | Timeout in milliseconds for synchronous plugin installation |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNC_SKILLS` | `0` \| `1` | | Set to 1 to download enabled claude.ai skills into ~/.claude/skills/ before the first query and resync every 10 minutes (non-interactive -p mode only; requires claude.ai auth). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNC_SKILLS_INSTALL_TIMEOUT_MS` | string | | Timeout in milliseconds for a mid-session skills resync when CLAUDE_CODE_SYNC_SKILLS is set (default 30000). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS` | string | | Timeout in milliseconds for the first query to wait on the initial skills sync when CLAUDE_CODE_SYNC_SKILLS is set (default 5000). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_SYNTAX_HIGHLIGHT` | `true` \| `false` | | UNDOCUMENTED. Enable syntax highlighting in diffs |
| &nbsp;&nbsp;`env.CLAUDE_CODE_TASK_LIST_ID` | string | | Shared task list identifier for team collaboration |
| &nbsp;&nbsp;`env.CLAUDE_CODE_TEAM_NAME` | string | | Agent team membership name |
| &nbsp;&nbsp;`env.CLAUDE_CODE_TEAM_TEARDOWN_PARK_TIMEOUT_MS` | string | | Override, in milliseconds, how long a non-interactive session waits at exit for its agent team to finish tearing down. Accepts 1000 to 60000; an out-of-range value is ignored and the default of 10000 applies. Requires Claude Code v2.1.206 or later. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_TMPDIR` | string | | Override temp directory path |
| &nbsp;&nbsp;`env.CLAUDE_CODE_TMUX_TRUECOLOR` | `0` \| `1` | | Allow 24-bit truecolor rendering in tmux |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_ANTHROPIC_AWS` | `0` \| `1` | | Enable Claude Platform on AWS as the API provider. Bedrock and Foundry take precedence if also set. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_BEDROCK` | `0` \| `1` | | Enable Amazon Bedrock as the API provider. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_FOUNDRY` | `0` \| `1` | | Enable Microsoft Foundry as the API provider. |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_MANTLE` | `0` \| `1` | | Enable the Mantle endpoint (native Anthropic API shape on Bedrock). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_NATIVE_FILE_SEARCH` | `0` \| `1` | | Set to 1 to discover custom commands, subagents, and output styles using Node.js file APIs instead of ripgrep (for environments where the bundled ripgrep is unavailable). |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_POWERSHELL_TOOL` | `0` \| `1` | | Enable PowerShell as default shell for interactive commands (Windows) |
| &nbsp;&nbsp;`env.CLAUDE_CODE_USE_VERTEX` | `0` \| `1` | | Enable Google Cloud's Agent Platform as the API provider. |
| &nbsp;&nbsp;`env.CLAUDE_CONFIG_DIR` | string | | Override the configuration directory (default ~/.claude) where settings, credentials, session history, and plugins are stored. Useful for running multiple accounts side by side. |
| &nbsp;&nbsp;`env.CLAUDE_DISABLE_ADOPT` | `0` \| `1` | | Set to 1 to stop in-flight background work instead of carrying it over when you background a session by pressing ← or with /background. Claude Code asks you to confirm before backgrounding, then stops the tasks that would otherwise carry over. Requires Claude Code v2.1.195 or later. |
| &nbsp;&nbsp;`env.CLAUDE_EFFORT` | `low` \| `medium` \| `high` \| `xhigh` \| `max` | | Set automatically in Bash tool subprocesses and hook commands to the active effort level for the turn (low, medium, high, xhigh, or max; ultracode reports as xhigh). Read-only. |
| &nbsp;&nbsp;`env.CLAUDE_ENABLE_BYTE_WATCHDOG` | `0` \| `1` | | Set to 1 to force-enable, or 0 to force-disable, the byte-level streaming idle watchdog that aborts a connection when no bytes arrive within the configured timeout. Enabled by default on direct Anthropic API and Claude Platform on AWS connections. |
| &nbsp;&nbsp;`env.CLAUDE_ENABLE_BYTE_WATCHDOG_BEDROCK` | `0` \| `1` | | Set to 1 to enable the byte-level streaming idle watchdog on Amazon Bedrock eventstream responses (off by default). Configure the timeout with CLAUDE_STREAM_IDLE_TIMEOUT_MS. |
| &nbsp;&nbsp;`env.CLAUDE_ENABLE_STREAM_WATCHDOG` | `0` \| `1` | | Set to 1 to force-enable, or 0 to force-disable, the event-level streaming idle watchdog. When unset, the watchdog is on by default for all providers (as of v2.1.196; before that the unset default was server-controlled on the direct Anthropic API and off on other providers). |
| &nbsp;&nbsp;`env.CLAUDE_ENV_FILE` | string | | File path for persisting environment variables across Bash commands |
| &nbsp;&nbsp;`env.CLAUDE_PID` | string | | Claude Code sets this to its own process ID in the subprocesses it spawns: Bash and PowerShell tool commands and hook commands. On Linux, the Bash tool's shell integration uses it to refuse a pkill pattern that would match the Claude Code process itself. Read it from your own scripts to identify or signal the parent Claude Code process deliberately. Requires Claude Code v2.1.214 or later. |
| &nbsp;&nbsp;`env.CLAUDE_PROJECT_DIR` | string | | Project root directory path (also provided to hooks) |
| &nbsp;&nbsp;`env.CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX` | string | | Prefix for auto-generated Remote Control session names when no explicit name is set. Defaults to the machine hostname, producing names like myhost-graceful-unicorn. |
| &nbsp;&nbsp;`env.CLAUDE_STREAM_IDLE_TIMEOUT_MS` | string | | Timeout in milliseconds before the streaming idle watchdog closes a stalled connection. When set explicitly the minimum is 300000 (5 minutes); lower values are clamped. |
| &nbsp;&nbsp;`env.CLOUD_ML_REGION` | string | | Google Cloud's Agent Platform region: global, a multi-region location (eu, us), or a specific region (e.g. us-east5). |
| &nbsp;&nbsp;`env.DEBUG` | string | | Set to a truthy value (1, true, yes, or on) to enable debug mode, equivalent to --debug. Logs are written to ~/.claude/debug/<session-id>.txt. |
| &nbsp;&nbsp;`env.DISABLE_AUTOUPDATER` | `0` \| `1` | | Set to 1 to disable automatic background updates. Manual claude update still works; use DISABLE_UPDATES to block both. |
| &nbsp;&nbsp;`env.DISABLE_AUTO_COMPACT` | `0` \| `1` | | Set to 1 to disable automatic compaction when approaching the context limit. The manual /compact command remains available. Equivalent to autoCompactEnabled: false. |
| &nbsp;&nbsp;`env.DISABLE_COMPACT` | `0` \| `1` | | Set to 1 to disable all compaction: both automatic compaction and the manual /compact command. |
| &nbsp;&nbsp;`env.DISABLE_COST_WARNINGS` | `0` \| `1` | | Set to 1 to disable cost warning messages. |
| &nbsp;&nbsp;`env.DISABLE_DOCTOR_COMMAND` | `0` \| `1` | | Set to 1 to hide the /doctor command (useful for managed deployments). |
| &nbsp;&nbsp;`env.DISABLE_ERROR_REPORTING` | `0` \| `1` | | Disable Sentry error reporting |
| &nbsp;&nbsp;`env.DISABLE_EXTRA_USAGE_COMMAND` | `0` \| `1` | | Set to 1 to hide the /usage-credits command for purchasing additional usage beyond rate limits. |
| &nbsp;&nbsp;`env.DISABLE_FEEDBACK_COMMAND` | `0` \| `1` | | Set to 1 to disable the /feedback command. The older name DISABLE_BUG_COMMAND is also accepted. |
| &nbsp;&nbsp;`env.DISABLE_GROWTHBOOK` | `0` \| `1` | | Set to 1 to disable GrowthBook feature-flag fetching and use code defaults for every flag. Telemetry stays on unless DISABLE_TELEMETRY is also set. |
| &nbsp;&nbsp;`env.DISABLE_INSTALLATION_CHECKS` | `0` \| `1` | | Set to 1 to disable installation warnings (use only when manually managing the installation location). |
| &nbsp;&nbsp;`env.DISABLE_INSTALL_GITHUB_APP_COMMAND` | `0` \| `1` | | Set to 1 to hide the /install-github-app command (already hidden on Bedrock, Vertex, or Foundry). |
| &nbsp;&nbsp;`env.DISABLE_INTERLEAVED_THINKING` | `0` \| `1` | | Set to 1 to prevent sending the interleaved-thinking beta header (useful when a gateway or provider does not support interleaved thinking). |
| &nbsp;&nbsp;`env.DISABLE_LOGIN_COMMAND` | `0` \| `1` | | Set to 1 to hide the /login command (useful when authentication is handled externally via API keys or apiKeyHelper). |
| &nbsp;&nbsp;`env.DISABLE_LOGOUT_COMMAND` | `0` \| `1` | | Set to 1 to hide the /logout command. |
| &nbsp;&nbsp;`env.DISABLE_PROMPT_CACHING` | `0` \| `1` | | Disable prompt caching for all models. |
| &nbsp;&nbsp;`env.DISABLE_PROMPT_CACHING_FABLE` | `0` \| `1` | | Disable prompt caching for Fable models only. |
| &nbsp;&nbsp;`env.DISABLE_PROMPT_CACHING_HAIKU` | `0` \| `1` | | Disable prompt caching for Haiku models only. |
| &nbsp;&nbsp;`env.DISABLE_PROMPT_CACHING_OPUS` | `0` \| `1` | | Disable prompt caching for Opus models only. |
| &nbsp;&nbsp;`env.DISABLE_PROMPT_CACHING_SONNET` | `0` \| `1` | | Disable prompt caching for Sonnet models only. |
| &nbsp;&nbsp;`env.DISABLE_TELEMETRY` | `0` \| `1` | | Set to 1 to opt out of telemetry. Also disables feature-flag fetching (same effect as DISABLE_GROWTHBOOK). |
| &nbsp;&nbsp;`env.DISABLE_UPDATES` | `0` \| `1` | | Block all update paths including manual updates |
| &nbsp;&nbsp;`env.DISABLE_UPGRADE_COMMAND` | `0` \| `1` | | Set to 1 to hide the /upgrade command. |
| &nbsp;&nbsp;`env.DO_NOT_TRACK` | `0` \| `1` | | Set to 1 to opt out of telemetry (cross-tool convention; equivalent to DISABLE_TELEMETRY). |
| &nbsp;&nbsp;`env.ENABLE_BETA_TRACING_DETAILED` | `0` \| `1` | | Emit detailed spans including hook execution when the tracing beta is enabled. |
| &nbsp;&nbsp;`env.ENABLE_CLAUDEAI_MCP_SERVERS` | `true` \| `false` | | Opt in/out of claude.ai MCP servers. |
| &nbsp;&nbsp;`env.ENABLE_PROMPT_CACHING_1H` | `0` \| `1` | | Request a 1-hour prompt cache TTL instead of the 5-minute default (billed at a higher rate). |
| &nbsp;&nbsp;`env.ENABLE_TOOL_SEARCH` | string | | Control MCP tool search: "true" always defers and sends the beta header (requests fail on Google Cloud's Agent Platform models earlier than Sonnet 4.5/Opus 4.5 or on proxies that do not support tool_reference); "auto" loads tools upfront if they fit within 10% of context; "auto:N" sets a custom threshold percentage (e.g. auto:5); "false" loads all tools upfront. Also applies when ANTHROPIC_BASE_URL points to a non-first-party host. |
| &nbsp;&nbsp;`env.FALLBACK_FOR_ALL_PRIMARY_MODELS` | string | | Set to any non-empty value to make all models (not only Opus) stop retrying with a repeated-overload error when no fallback model is configured. |
| &nbsp;&nbsp;`env.FORCE_AUTOUPDATE_PLUGINS` | `0` \| `1` | | Keep plugin auto-updates enabled even when DISABLE_AUTOUPDATER=1 is set. |
| &nbsp;&nbsp;`env.FORCE_HYPERLINK` | `0` \| `1` | | Set to 1 to enable clickable OSC 8 hyperlinks when your terminal supports them but is not auto-detected, or 0 to disable them |
| &nbsp;&nbsp;`env.FORCE_PROMPT_CACHING_5M` | `0` \| `1` | | Force a 5-minute cache TTL regardless of authentication method; overrides ENABLE_PROMPT_CACHING_1H or a managed-settings TTL. |
| &nbsp;&nbsp;`env.GOOGLE_APPLICATION_CREDENTIALS` | string | | Path to a GCP credential configuration file (service account key or workload identity federation config) used for Google Cloud's Agent Platform authentication. |
| &nbsp;&nbsp;`env.HTTPS_PROXY` | string | | HTTPS proxy URL (recommended over HTTP_PROXY) |
| &nbsp;&nbsp;`env.HTTP_PROXY` | string | | HTTP proxy URL |
| &nbsp;&nbsp;`env.IS_DEMO` | `0` \| `1` | | Set to 1 to enable demo mode: hides email and organization name from the header and /status output and skips onboarding. |
| &nbsp;&nbsp;`env.MAX_MCP_OUTPUT_TOKENS` | string | | Maximum number of tokens allowed in MCP tool output before truncation (default: 25000). Claude Code displays a warning above 10000 tokens. For tools that declare anthropic/maxResultSizeChars, that character limit replaces this token limit for text content, but image content from those tools is still subject to this limit. |
| &nbsp;&nbsp;`env.MAX_STRUCTURED_OUTPUT_RETRIES` | string | | Number of times to retry when the model's response fails validation against --json-schema in non-interactive (-p) mode (default 5). |
| &nbsp;&nbsp;`env.MAX_THINKING_TOKENS` | string | | Override the extended thinking token budget; set to 0 to disable thinking on the Anthropic API. On adaptive reasoning models (Opus 4.7+, Opus 4.8, Fable 5) a nonzero budget is ignored unless CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING is set. |
| &nbsp;&nbsp;`env.MCP_CLIENT_SECRET` | string | | OAuth client secret for MCP servers that require pre-configured credentials (avoids the interactive prompt when adding a server with --client-secret). |
| &nbsp;&nbsp;`env.MCP_CONNECTION_NONBLOCKING` | `0` \| `1` | | Controls whether startup waits for MCP servers to connect before the first query. Non-blocking by default since v2.1.142; set to 0 to restore the blocking 5-second connection wait. |
| &nbsp;&nbsp;`env.MCP_CONNECT_TIMEOUT_MS` | string | | How long blocking MCP startup waits in milliseconds for the connection batch before snapshotting the tool list (default 5000). Applies when MCP_CONNECTION_NONBLOCKING=0 or for alwaysLoad servers. |
| &nbsp;&nbsp;`env.MCP_OAUTH_CALLBACK_PORT` | string | | Fixed port for the OAuth redirect callback, as an alternative to --callback-port when adding an MCP server with pre-configured credentials. |
| &nbsp;&nbsp;`env.MCP_REMOTE_SERVER_CONNECTION_BATCH_SIZE` | string | | Maximum number of remote MCP servers (HTTP/SSE) to connect in parallel during startup (default 20). |
| &nbsp;&nbsp;`env.MCP_SERVER_CONNECTION_BATCH_SIZE` | string | | Maximum number of local MCP servers (stdio) to connect in parallel during startup (default 3). |
| &nbsp;&nbsp;`env.MCP_TIMEOUT` | string | | Timeout in milliseconds for MCP server startup (default 30000). |
| &nbsp;&nbsp;`env.MCP_TOOL_TIMEOUT` | string | | Timeout in milliseconds for MCP tool execution (default: 100000000, about 28 hours). A per-server timeout field in .mcp.json overrides this for that server. Values below 1000 are floored to one second. |
| &nbsp;&nbsp;`env.NODE_EXTRA_CA_CERTS` | string | | Path to custom CA certificate file |
| &nbsp;&nbsp;`env.NO_PROXY` | string | | Domains to bypass proxy (space or comma-separated, or '*' for all) |
| &nbsp;&nbsp;`env.OTEL_ATTRIBUTE_VALUE_LENGTH_LIMIT` | string | | Standard OpenTelemetry SDK limit on attribute value length. Claude Code caps content-bearing telemetry attributes at the smaller of this and CLAUDE_CODE_OTEL_CONTENT_MAX_LENGTH, so the truncation marker stays within the SDK limit. Claude Code reads the OTEL_LOGRECORD_ATTRIBUTE_VALUE_LENGTH_LIMIT and OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT variants the same way, and the smallest set value applies to all signals. Requires Claude Code v2.1.214 or later. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_CERTIFICATE` | string | | Path to the CA certificate for gRPC OTLP mTLS. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE` | string | | Path to the client certificate for gRPC OTLP mTLS. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_CLIENT_KEY` | string | | Path to the client private key for gRPC OTLP mTLS. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_ENDPOINT` | string | | OTLP exporter endpoint for all signals (e.g. http://localhost:4317). |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_HEADERS` | string | | Headers sent with OTLP exporter requests (e.g. Authorization=Bearer token). |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_LOGS_CLIENT_CERTIFICATE` | string | | Path to the client certificate for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE for logs only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_LOGS_CLIENT_KEY` | string | | Path to the client private key for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_KEY for logs only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_LOGS_ENDPOINT` | string | | OTLP exporter endpoint override for logs. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_LOGS_PROTOCOL` | `grpc` \| `http/json` \| `http/protobuf` | | OTLP protocol override for logs: grpc, http/json, or http/protobuf. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE` | string | | Path to the client certificate for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE for metrics only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY` | string | | Path to the client private key for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_KEY for metrics only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` | string | | OTLP exporter endpoint override for metrics. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_METRICS_PROTOCOL` | `grpc` \| `http/json` \| `http/protobuf` | | OTLP protocol override for metrics: grpc, http/json, or http/protobuf. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` | `delta` \| `cumulative` | | Metrics temporality preference: delta (default) or cumulative. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_PROTOCOL` | `grpc` \| `http/json` \| `http/protobuf` | | OTLP exporter protocol for all signals: grpc, http/json, or http/protobuf. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_TRACES_CLIENT_CERTIFICATE` | string | | Path to the client certificate for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE for traces only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_TRACES_CLIENT_KEY` | string | | Path to the client private key for gRPC OTLP mTLS, overriding OTEL_EXPORTER_OTLP_CLIENT_KEY for traces only. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | string | | OTLP exporter endpoint override for traces. |
| &nbsp;&nbsp;`env.OTEL_EXPORTER_OTLP_TRACES_PROTOCOL` | `grpc` \| `http/json` \| `http/protobuf` | | OTLP protocol override for traces: grpc, http/json, or http/protobuf. |
| &nbsp;&nbsp;`env.OTEL_LOGS_EXPORTER` | string | | OpenTelemetry logs exporter(s) as a comma-separated list. Valid values: otlp, console, none. |
| &nbsp;&nbsp;`env.OTEL_LOGS_EXPORT_INTERVAL` | string | | Logs export interval in milliseconds (default 5000). |
| &nbsp;&nbsp;`env.OTEL_LOG_ASSISTANT_RESPONSES` | `0` \| `1` | | UNDOCUMENTED. Include assistant response text in the claude_code.assistant_response OpenTelemetry log event (added v2.1.193). When unset, follows OTEL_LOG_USER_PROMPTS; set to 0 to keep prompts-only. |
| &nbsp;&nbsp;`env.OTEL_LOG_RAW_API_BODIES` | string | | Log raw API request/response bodies. Set to 1, or to file:<dir> to write them to a directory. |
| &nbsp;&nbsp;`env.OTEL_LOG_TOOL_CONTENT` | `0` \| `1` | | Include full tool input/output content in OpenTelemetry log events (requires tracing; disabled by default). |
| &nbsp;&nbsp;`env.OTEL_LOG_TOOL_DETAILS` | `0` \| `1` | | Include tool name and parameters in OpenTelemetry log events (disabled by default). |
| &nbsp;&nbsp;`env.OTEL_LOG_USER_PROMPTS` | `0` \| `1` | | Include user prompt text in OpenTelemetry log events (disabled by default). |
| &nbsp;&nbsp;`env.OTEL_METRICS_EXPORTER` | string | | OpenTelemetry metrics exporter(s) as a comma-separated list. Valid values: otlp, prometheus, console, none. |
| &nbsp;&nbsp;`env.OTEL_METRICS_INCLUDE_ACCOUNT_UUID` | `true` \| `false` | | Include the user.account_uuid and user.account_id attributes on metrics (default true). |
| &nbsp;&nbsp;`env.OTEL_METRICS_INCLUDE_ENTRYPOINT` | `true` \| `false` | | Include the app.entrypoint attribute on metrics (default false). |
| &nbsp;&nbsp;`env.OTEL_METRICS_INCLUDE_RESOURCE_ATTRIBUTES` | `true` \| `false` | | Include configured OTEL_RESOURCE_ATTRIBUTES on metric data points (default true). |
| &nbsp;&nbsp;`env.OTEL_METRICS_INCLUDE_SESSION_ID` | `true` \| `false` | | Include the session.id attribute on metrics (default true). |
| &nbsp;&nbsp;`env.OTEL_METRICS_INCLUDE_VERSION` | `true` \| `false` | | Include the app.version attribute on metrics (default false). |
| &nbsp;&nbsp;`env.OTEL_METRIC_EXPORT_INTERVAL` | string | | Metrics export interval in milliseconds (default 60000). |
| &nbsp;&nbsp;`env.OTEL_RESOURCE_ATTRIBUTES` | string | | Comma-separated key=value resource attributes attached to all telemetry. |
| &nbsp;&nbsp;`env.OTEL_TRACES_EXPORTER` | string | | OpenTelemetry traces exporter(s) as a comma-separated list. Valid values: otlp, console, none. |
| &nbsp;&nbsp;`env.OTEL_TRACES_EXPORT_INTERVAL` | string | | Traces export interval in milliseconds (default 5000). |
| &nbsp;&nbsp;`env.SLASH_COMMAND_TOOL_CHAR_BUDGET` | string | | Override the character budget for skill metadata shown to the Skill tool. The budget scales dynamically at 1% of the context window, with a fallback of 8000 characters. Legacy name kept for backwards compatibility. |
| &nbsp;&nbsp;`env.TASK_MAX_OUTPUT_LENGTH` | string | | Maximum number of characters in subagent output before truncation (default 32000, maximum 160000). When truncated, the full output is saved to disk and the path is included in the response. |
| &nbsp;&nbsp;`env.USE_BUILTIN_RIPGREP` | `0` \| `1` | | Use the bundled ripgrep binary instead of system ripgrep |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_3_5_HAIKU` | string | | Override the Vertex AI region for Claude 3.5 Haiku (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_3_5_SONNET` | string | | Override the Vertex AI region for Claude 3.5 Sonnet (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_3_7_SONNET` | string | | Override the Vertex AI region for Claude 3.7 Sonnet (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_0_OPUS` | string | | Override the Vertex AI region for Claude 4.0 Opus (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_0_SONNET` | string | | Override the Vertex AI region for Claude 4.0 Sonnet (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_1_OPUS` | string | | Override the Vertex AI region for Claude 4.1 Opus (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_5_OPUS` | string | | Override the Vertex AI region for Claude Opus 4.5 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_5_SONNET` | string | | Override the Vertex AI region for Claude Sonnet 4.5 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_6_OPUS` | string | | Override the Vertex AI region for Claude Opus 4.6 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_6_SONNET` | string | | Override the Vertex AI region for Claude Sonnet 4.6 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_7_OPUS` | string | | Override the Vertex AI region for Claude Opus 4.7 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_4_8_OPUS` | string | | Override the Vertex AI region for Claude Opus 4.8 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_5_OPUS` | string | | Override region for Claude Opus 5 when using Google Cloud's Agent Platform (formerly Vertex AI). Added in v2.1.219. |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_5_SONNET` | string | | Override region for Claude Sonnet 5 when using Google Cloud's Agent Platform (formerly Vertex AI). Added in v2.1.197. |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_FABLE_5` | string | | Override the Vertex AI region for Claude Fable 5 (used when CLOUD_ML_REGION=global). |
| &nbsp;&nbsp;`env.VERTEX_REGION_CLAUDE_HAIKU_4_5` | string | | Override the Vertex AI region for Claude Haiku 4.5 (used when CLOUD_ML_REGION=global). |
| `attribution` | object | project or personal | Customize attribution for git commits and pull requests. |
| &nbsp;&nbsp;`attribution.commit` | string | | Attribution for git commits, including any trailers. Empty string hides commit attribution |
| &nbsp;&nbsp;`attribution.pr` | string | | Attribution for pull request descriptions. Empty string hides pull request attribution |
| &nbsp;&nbsp;`attribution.sessionUrl` | boolean | | Whether to append the claude.ai session link as a Claude-Session trailer on commits and a link in pull request descriptions when running from a web or Remote Control session. Defaults to true; set to false to omit the link. |
| `includeGitInstructions` | boolean | **live** in settings.json | Include built-in git commit and PR workflow instructions in Claude's system prompt. Also configurable via CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS environment variable (set to 1 to disable). |
| `includeCoAuthoredBy` | boolean | project or personal | DEPRECATED. Use 'attribution' instead. Whether to include the co-authored-by Claude byline in git commits and pull requests (default: true) |
| `plansDirectory` | string | project or personal | Customize where plan files are stored. Path is relative to project root (default: ~/.claude/plans) |
| `respectGitignore` | boolean | **live** in settings.json | Control whether the @ file picker respects .gitignore patterns. When true (default), files matching .gitignore patterns are excluded from suggestions |
| `permissions` | object | **live** in settings.json | Tool usage permissions configuration. and https://code.claude.com/docs/en/settings#permission-settings for full list of tools available to Claude. |
| &nbsp;&nbsp;`permissions.allow` | array | | List of permission rules for allowed operations |
| &nbsp;&nbsp;`permissions.deny` | array | | List of permission rules for denied operations |
| &nbsp;&nbsp;`permissions.ask` | array | | List of permission rules that should always prompt for confirmation |
| &nbsp;&nbsp;`permissions.defaultMode` | `acceptEdits` \| `bypassPermissions` \| `default` \| `delegate` \| `dontAsk` \| `plan` \| `auto` \| `manual` | | Default permission mode. "default": prompts on first use. UNDOCUMENTED. "manual": accepted alias for "default" (the CLI/VS Code/JetBrains UI now labels this mode "Manual" as of v2.1.200; permission-modes.md has not yet been updated to mention it). "acceptEdits": auto-accepts file edits. "plan": read-only, no modifications. UNDOCUMENTED. "delegate": coordination-only for agent team leads (agent teams are experimental; enable via CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS). "dontAsk": auto-denies unless pre-approved via permissions. "bypassPermissions": skips all prompts (use only in isolated environments). "auto": auto-approves tool calls with background safety checks that verify actions align with your request. |
| &nbsp;&nbsp;`permissions.disableBypassPermissionsMode` | `disable` | | Disable the ability to bypass permission prompts |
| &nbsp;&nbsp;`permissions.disableAutoMode` | `disable` | | Set to "disable" to prevent auto mode from being activated. Removes `auto` from the Shift+Tab cycle and rejects `--permission-mode auto` at startup. Most useful in managed settings where users cannot override it. |
| &nbsp;&nbsp;`permissions.additionalDirectories` | array | | Additional directories to include in the permission scope |
| `language` | string | personal → `settings.local.json` / `~/.claude` | Configure Claude's preferred response language (e.g., "japanese", "spanish", "french"). Claude will respond in this language by default. Also sets the voice dictation language and terminal tab session title generation. |
| `model` | string | personal → `settings.local.json` / `~/.claude` | Override the default model used by Claude Code. For finer control, use environment variables: ANTHROPIC_MODEL (runtime override), ANTHROPIC_DEFAULT_OPUS_MODEL, ANTHROPIC_DEFAULT_SONNET_MODEL, ANTHROPIC_DEFAULT_HAIKU_MODEL (per-class pinning), CLAUDE_CODE_SUBAGENT_MODEL (subagent model). |
| `availableModels` | array | project or personal | Restrict which models users can select. When defined at multiple settings levels (user, project, etc.), arrays are merged and deduplicated. |
| `modelOverrides` | object | project or personal | Map Anthropic model IDs to provider-specific model IDs such as Bedrock inference profile ARNs, Vertex AI version names, or Foundry deployment names. Each model picker entry uses its mapped value when calling the provider API. Unknown keys are ignored. |
| `effortLevel` | `low` \| `medium` \| `high` \| `xhigh` | personal → `settings.local.json` / `~/.claude` | Persist adaptive reasoning effort across sessions. Set to low, medium, high, or xhigh; max and ultracode are session-only and are not accepted in the settings file (use the CLAUDE_CODE_EFFORT_LEVEL environment variable or /effort for a session-only max). Effort is supported on Fable 5, Opus 4.8, Opus 4.7, Opus 4.6, and Sonnet 4.6, with xhigh sitting between high and max (added in v2.1.111). Defaults: Fable 5 and Opus 4.8 default to high; Opus 4.6 and Sonnet 4.6 default to high on all plans (Pro/Max raised from medium to high in v2.1.117); Opus 4.7 defaults to xhigh. Use /effort auto to reset to model default. Also configurable via CLAUDE_CODE_EFFORT_LEVEL environment variable. |
| `fastMode` | boolean | personal → `settings.local.json` / `~/.claude` | Enable fast mode, which uses Claude Opus 5 by default (since v2.1.219) for faster output at higher per-token cost without downgrading to a smaller model. Requires extra usage enabled. Toggle with the /fast command. Supported on Opus 5 and Opus 4.8; fast mode for Opus 4.7 was deprecated on June 25, 2026 and removed on July 24, 2026. Before v2.1.219 fast mode defaulted to Opus 4.8 (v2.1.154 through v2.1.218) and to Opus 4.7 (v2.1.142 through v2.1.153). |
| `fastModePerSessionOptIn` | boolean | project or personal | Require per-session opt-in for fast mode. When true, fast mode does not persist across sessions and users must enable it with /fast each session. Useful for controlling costs. |
| `feedbackSurveyRate` | number | personal → `settings.local.json` / `~/.claude` | Probability (0–1) that the session quality survey appears when eligible. A value of 0.05 means 5% of eligible sessions. |
| `enableAllProjectMcpServers` | boolean | **live** in settings.json | Whether to automatically approve all MCP servers in the project. |
| `enabledMcpjsonServers` | array | **live** in settings.json | List of approved MCP servers from .mcp.json. |
| `disabledMcpjsonServers` | array | **live** in settings.json | List of rejected MCP servers from .mcp.json. |
| `allowedMcpServers` | array | project or personal | Enterprise allowlist of MCP servers that can be used. Applies to all scopes including enterprise servers from managed-mcp.json. If undefined, all servers are allowed. If empty array, no servers are allowed. Denylist takes precedence - if a server is on both lists, it is denied. |
| `deniedMcpServers` | array | project or personal | Enterprise denylist of MCP servers that are explicitly blocked. If a server is on the denylist, it will be blocked across all scopes including enterprise. Denylist takes precedence over allowlist - if a server is on both lists, it is denied. |
| `httpHookAllowedEnvVars` | array | project or personal | Allowlist of environment variable names HTTP hooks may interpolate into headers. When set, each hook's effective allowedEnvVars is the intersection with this list. Undefined = no restriction. Arrays merge across settings sources. |
| `hooks` | object | **live** in settings.json | Lifecycle event hooks that run at configurable points during Claude Code operation (tool use, session start/end, notifications, prompt submit, message display, and more), not just before/after tool executions. |
| &nbsp;&nbsp;`hooks.PreToolUse` | array | | Hooks that run before tool calls |
| &nbsp;&nbsp;`hooks.PostToolUse` | array | | Hooks that run after tool completion |
| &nbsp;&nbsp;`hooks.PostToolUseFailure` | array | | Hooks that run after a tool fails |
| &nbsp;&nbsp;`hooks.PermissionRequest` | array | | Hooks that run when a permission dialog appears |
| &nbsp;&nbsp;`hooks.Notification` | array | | Hooks that trigger on notifications |
| &nbsp;&nbsp;`hooks.UserPromptSubmit` | array | | Hooks that run when a user submits a prompt |
| &nbsp;&nbsp;`hooks.Stop` | array | | Hooks that run when agents finish responding. Does not run on user interrupt |
| &nbsp;&nbsp;`hooks.StopFailure` | array | | Hooks that run when a turn ends due to an API error (e.g., rate_limit, authentication_failed, billing_error, invalid_request, server_error, max_output_tokens, unknown). Matcher can scope to specific error types. Hook output and exit code are ignored. |
| &nbsp;&nbsp;`hooks.SubagentStart` | array | | Hooks that run when a subagent is spawned |
| &nbsp;&nbsp;`hooks.SubagentStop` | array | | Hooks that run when subagents finish responding |
| &nbsp;&nbsp;`hooks.PreCompact` | array | | Hooks that run before the context is compacted |
| &nbsp;&nbsp;`hooks.PostCompact` | array | | Hooks that run after the context is compacted. |
| &nbsp;&nbsp;`hooks.Elicitation` | array | | Hooks that run when an MCP server requests user input during a tool call. |
| &nbsp;&nbsp;`hooks.ElicitationResult` | array | | Hooks that run after a user responds to an MCP elicitation, before the response is sent back to the server. |
| &nbsp;&nbsp;`hooks.TeammateIdle` | array | | Hooks that run when an agent team teammate is about to go idle. Exit code 2 sends feedback and keeps the teammate working. Does not support matchers. Agent teams are experimental. |
| &nbsp;&nbsp;`hooks.TaskCompleted` | array | | Hooks that run when a task is being marked as completed. Exit code 2 prevents completion and sends feedback. Does not support matchers. |
| &nbsp;&nbsp;`hooks.Setup` | array | | UNDOCUMENTED. Hooks that run during repository initialization (--init, --init-only) or maintenance (--maintenance) |
| &nbsp;&nbsp;`hooks.InstructionsLoaded` | array | | Hooks that run when a CLAUDE.md or .claude/rules/*.md file is loaded into context. Fires at session start and when files are lazily loaded (e.g., nested traversal, path glob match). No decision control; used for audit logging and observability. Does not support matchers. |
| &nbsp;&nbsp;`hooks.CwdChanged` | array | | Hooks that run when the working directory changes. Provides cwd (new directory) and previous_cwd. Matchers are ignored; fires on every directory change. |
| &nbsp;&nbsp;`hooks.FileChanged` | array | | Hooks that run when a watched file is created, modified, or deleted. Supports filename matchers. Provides file_path and file_event_type (created, modified, deleted). |
| &nbsp;&nbsp;`hooks.ConfigChange` | array | | Hooks that run when settings, managed settings, or skill files change during a session. Supports matchers: user_settings, project_settings, local_settings, policy_settings, skills. Command handlers only. Exit code 2 blocks the change (except policy_settings which is audit-only). |
| &nbsp;&nbsp;`hooks.WorktreeCreate` | array | | Hooks that run when a worktree is created via --worktree or isolation: "worktree" in subagents. Command handlers only, no matchers. Hook must print absolute path to created worktree on stdout; non-zero exit fails creation. |
| &nbsp;&nbsp;`hooks.WorktreeRemove` | array | | Hooks that run when a worktree is being removed at session exit or when a subagent finishes. Command handlers only, no matchers. Used for cleanup tasks; cannot block removal. |
| &nbsp;&nbsp;`hooks.SessionStart` | array | | Hooks that run when a new session starts |
| &nbsp;&nbsp;`hooks.SessionEnd` | array | | Hooks that run when a session ends |
| &nbsp;&nbsp;`hooks.PostToolBatch` | array | | Hooks that run after a full batch of parallel tool calls resolves, before the next model call. Exit code 2 blocks the agentic loop. Does not support matchers. |
| &nbsp;&nbsp;`hooks.TaskCreated` | array | | Hooks that run when a task is being created via TaskCreate. Exit code 2 rolls back task creation. Does not support matchers. |
| &nbsp;&nbsp;`hooks.PermissionDenied` | array | | Hooks that run when a tool call is denied by the auto mode classifier. Supports matchers on tool name. |
| &nbsp;&nbsp;`hooks.UserPromptExpansion` | array | | Hooks that run when a user-typed command expands into a prompt, before it reaches Claude. Exit code 2 blocks the expansion. Supports matchers on command name. |
| &nbsp;&nbsp;`hooks.MessageDisplay` | array | | Hooks that run while assistant message text is displayed |
| &nbsp;&nbsp;`hooks.DirectoryAdded` | array | | UNDOCUMENTED. Hooks that run after /add-dir or the SDK register_repo_root control request registers a new working directory mid-session (added v2.1.219) |
| `disableAllHooks` | boolean | project or personal | Disable all hooks and statusLine execution. When true in managed settings, user and project-level disableAllHooks cannot override it. |
| `allowedHttpHookUrls` | array | project or personal | Allowlist of URL patterns that HTTP hooks may target. Supports * as a wildcard. When set, hooks with non-matching URLs are blocked. Undefined = no restriction, empty array = block all HTTP hooks. Arrays merge across settings sources. |
| `statusLine` | object | **live** in settings.json | Custom status line display configuration. |
| &nbsp;&nbsp;`statusLine.type` | string | | The type of status line handler; must be set to "command" to run a custom shell script that receives JSON session data via stdin. |
| &nbsp;&nbsp;`statusLine.command` | string | | A shell command or path to a script that displays session information (context usage, costs, git status, etc.) by reading JSON data from stdin and writing output to stdout. |
| &nbsp;&nbsp;`statusLine.padding` | number | | Optional number of extra horizontal spacing characters added to the status line content; defaults to 0. |
| &nbsp;&nbsp;`statusLine.refreshInterval` | integer | | Re-run the status line command every N seconds in addition to event-driven updates. Leave unset to run only on events. Useful for time-based data like clocks, or when background subagents change git state while the main session is idle. |
| &nbsp;&nbsp;`statusLine.hideVimModeIndicator` | boolean | | Set to true when your status line script renders the vim mode indicator itself, to suppress the built-in vim mode display. |
| `fileSuggestion` | object | project or personal | Configure a custom script for @ file autocomplete. |
| &nbsp;&nbsp;`fileSuggestion.type` | string | | The type of file suggestion handler; must be set to "command" to execute a custom shell script that generates file suggestions for the @ file picker. |
| &nbsp;&nbsp;`fileSuggestion.command` | string | | Shell command to execute for file suggestions |
| `enabledPlugins` | object | **live** in settings.json | Enabled plugins using plugin-id@marketplace-id format. Example: { "formatter@anthropic-tools": true }. |
| `extraKnownMarketplaces` | object | **live** in settings.json | Additional marketplaces to make available for this repository. Typically used in repository .claude/settings.json to ensure team members have required plugin sources. |
| `skippedMarketplaces` | array | personal → `settings.local.json` / `~/.claude` | List of marketplace names the user has chosen not to install when prompted. |
| `skippedPlugins` | array | personal → `settings.local.json` / `~/.claude` | List of plugin IDs (plugin@marketplace format) the user has chosen not to install when prompted. |
| `forceLoginMethod` | `claudeai` \| `console` \| `gateway` | project or personal | Use "claudeai" to restrict login to Claude.ai accounts, "console" to restrict login to Claude Console accounts, or "gateway" to restrict login to a cloud gateway. On Claude Code v2.1.212 or later, every first-party login path enforces the restriction, including the VS Code extension, the Agent SDK, `claude setup-token`, and /install-github-app; before v2.1.212, only terminal logins enforced it. |
| `forceLoginOrgUUID` | any | project or personal | Organization UUID to use for OAuth login, or an array of UUIDs to allow several organizations. An empty array fails closed and blocks every login. |
| `otelHeadersHelper` | string | project or personal | Path to an executable, or a shell command line with arguments, that outputs OpenTelemetry headers as a JSON object. Runs at startup and re-runs on the interval set by CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS. Requires CLAUDE_CODE_ENABLE_TELEMETRY=1. |
| `outputStyle` | string | personal → `settings.local.json` / `~/.claude` | Controls the output style for assistant responses. Built-in styles: default, Proactive, Explanatory, Learning. Custom styles can be added in ~/.claude/output-styles/ or .claude/output-styles/. |
| `skipWebFetchPreflight` | boolean | project or personal | Skip the WebFetch blocklist check for enterprise environments with restrictive security policies. |
| `sandbox` | object | **live** in settings.json | Sandbox execution configuration. |
| &nbsp;&nbsp;`sandbox.network` | object | | Configures network isolation settings for the sandboxed bash environment, including domain restrictions, Unix socket access, and custom proxy configuration. |
| &nbsp;&nbsp;`sandbox.ignoreViolations` | object | | Map of command patterns to filesystem paths to ignore violations for. Use "*" to match all commands |
| &nbsp;&nbsp;`sandbox.excludedCommands` | array | | Commands that should never run in the sandbox (e.g., ["git", "docker"]). |
| &nbsp;&nbsp;`sandbox.autoAllowBashIfSandboxed` | boolean | | Automatically allow bash commands without prompting when they run in the sandbox. Only applies to commands that will run sandboxed. |
| &nbsp;&nbsp;`sandbox.enableWeakerNetworkIsolation` | boolean | | macOS only. Allow access to the system TLS trust service (com.apple.trustd.agent) in the sandbox. Required for Go-based tools like gh, gcloud, and terraform to verify TLS certificates when using httpProxyPort with a MITM proxy and custom CA. Reduces security by opening a potential data exfiltration path. Default: false. |
| &nbsp;&nbsp;`sandbox.enableWeakerNestedSandbox` | boolean | | Enable weaker sandbox mode for unprivileged docker environments where --proc mounting fails. This significantly reduces the strength of the sandbox and should only be used when this risk is acceptable. Default: false (secure). |
| &nbsp;&nbsp;`sandbox.allowUnsandboxedCommands` | boolean | | Allow commands to run outside the sandbox via the dangerouslyDisableSandbox parameter. When false, the dangerouslyDisableSandbox parameter is completely ignored and all commands must run sandboxed. Default: true. |
| &nbsp;&nbsp;`sandbox.enabled` | boolean | | Enable sandboxed bash. |
| &nbsp;&nbsp;`sandbox.filesystem` | object | | Filesystem access control for sandboxed commands. |
| &nbsp;&nbsp;`sandbox.ripgrep` | object | | Custom ripgrep configuration for Claude Code's bundled ripgrep support. Overrides the bundled binary and arguments. |
| &nbsp;&nbsp;`sandbox.bwrapPath` | string | | (Managed setting only) Path to custom bubblewrap (bwrap) binary for Linux/WSL sandbox. Overrides default. |
| &nbsp;&nbsp;`sandbox.socatPath` | string | | (Managed setting only) Path to custom socat binary for Linux/WSL network proxying. Overrides default. |
| &nbsp;&nbsp;`sandbox.failIfUnavailable` | boolean | | When true, make sandbox startup a hard failure if required sandbox dependencies are missing. Default: false (sandbox is skipped with a warning). |
| &nbsp;&nbsp;`sandbox.enabledPlatforms` | array | | Limit the entire sandbox configuration to the listed platforms. On platforms not in the list the sandbox config is inert: no sandbox, no auto-allow, no startup warning, and no failIfUnavailable exit. When omitted, all supported platforms are included. Only honored from managed (policy) settings. |
| &nbsp;&nbsp;`sandbox.credentials` | object | | Block sandboxed commands from reading credential files and secret environment variables (v2.1.187+). Entries merge across settings scopes. |
| &nbsp;&nbsp;`sandbox.allowAppleEvents` | boolean | | Allow sandboxed commands to send Apple Events on macOS (v2.1.181+). Honored only from user, managed, or CLI settings; project settings cannot enable it. |
| `spinnerVerbs` | object | personal → `settings.local.json` / `~/.claude` | Customize the verbs shown in spinner progress messages |
| &nbsp;&nbsp;`spinnerVerbs.mode` | `append` \| `replace` | | How to combine custom verbs with default spinner verbs: 'append' adds custom verbs to the default list, 'replace' uses only custom verbs |
| &nbsp;&nbsp;`spinnerVerbs.verbs` | array | | Custom verbs used in spinner progress text |
| `spinnerTipsEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Show tips in the spinner while Claude is working. Set to false to disable tips (default: true) |
| `spinnerTipsOverride` | object | personal → `settings.local.json` / `~/.claude` | Customize the tips displayed in the spinner while Claude is working. |
| &nbsp;&nbsp;`spinnerTipsOverride.excludeDefault` | boolean | | If true, only show custom tips. If false or absent, custom tips merge with built-in tips |
| &nbsp;&nbsp;`spinnerTipsOverride.tips` | array | | Custom tip strings to display in the spinner |
| `terminalProgressBarEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Enable the terminal progress bar that shows progress in supported terminals like Windows Terminal and iTerm2 (default: true) |
| `showTurnDuration` | boolean | personal → `settings.local.json` / `~/.claude` | Show turn duration messages after responses (e.g., "Cooked for 1m 6s"). Set to false to hide these messages (default: true) |
| `skillOverrides` | object | **live** in settings.json | Per-skill visibility overrides. Controls whether skills appear to Claude and in the / picker. Values: 'on' (name and description shown, default), 'name-only' (name only), 'user-invocable-only' (hidden from Claude, visible in /), 'off' (hidden everywhere). Plugin skills are not affected by this setting. |
| `prefersReducedMotion` | boolean | personal → `settings.local.json` / `~/.claude` | Reduce or disable UI animations (spinners, shimmer, flash effects) for accessibility |
| `prUrlTemplate` | string | project or personal | URL template for the PR badge shown in the footer and in tool-result summaries. Substitutes placeholders {host}, {owner}, {repo}, {number}, {url} from the gh-reported PR URL. Use this to point PR links at an internal code-review tool instead of github.com. Does not affect #123 autolinks in Claude's prose. |
| `alwaysThinkingEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Enable extended thinking by default for all sessions. Typically configured via the /config command rather than editing directly. |
| `companyAnnouncements` | array | project or personal | Company announcements to display at startup (one will be randomly selected if multiple are provided) |
| `teammateMode` | `auto` \| `in-process` \| `tmux` \| `iterm2` | project or personal | How agent team teammates display: "auto" picks split panes in tmux or iTerm2, in-process otherwise; "iterm2" (added in v2.1.186) forces iTerm2 native split panes and requires the it2 CLI (it shows an error with the install command if it2 is missing). The default is "in-process" (it was "auto" before v2.1.179). Agent teams are experimental and disabled by default. Enable them by adding CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS to your settings.json or environment. |
| `worktree` | object | **live** in settings.json | Configuration for --worktree sessions. |
| &nbsp;&nbsp;`worktree.sparsePaths` | array | | Directories to check out in each worktree via git sparse-checkout (cone mode). Only the listed paths are written to disk, which is faster in large monorepos. |
| &nbsp;&nbsp;`worktree.baseRef` | `fresh` \| `head` | | Whether to branch worktrees from origin/<default> (fresh) or local HEAD (head). Default: fresh. Set to 'head' to preserve unpushed commits in new worktrees. |
| &nbsp;&nbsp;`worktree.bgIsolation` | `worktree` \| `none` | | Isolation mode for background sessions. "worktree" blocks Edit/Write in main checkout until EnterWorktree is called; "none" lets background jobs edit the working copy directly without EnterWorktree, for repos where worktrees are impractical. |
| &nbsp;&nbsp;`worktree.symlinkDirectories` | array | | Directories to symlink from the main repository into each worktree to avoid duplicating large directories on disk. No directories are symlinked by default. |
| `pluginConfigs` | object | project or personal | Per-plugin configuration including MCP server user configs and plugin options, keyed by plugin ID (plugin@marketplace format). |
| `agent` | string | project or personal | Name of an agent (built-in or custom) to use for the main thread. Applies the agent's system prompt, tool restrictions, and model. |
| `autoMemoryDirectory` | string | personal → `settings.local.json` / `~/.claude` | Custom directory path for auto-memory storage. Supports ~/ prefix for home-directory expansion. Ignored if set in checked-in project settings (.claude/settings.json) for security. Defaults to ~/.claude/projects/<sanitized-cwd>/memory/ when unset. |
| `autoMode` | object | project or personal | Customization for the auto mode classifier prompt. Typically configured in managed settings to tune the allow/deny rules used when permissions.defaultMode is "auto". By default, allow, soft_deny, and environment REPLACE the corresponding built-in classifier section entirely. Include the literal string "$defaults" as an array entry (added in v2.1.118) to splice the built-in defaults in at that position alongside your custom rules. |
| &nbsp;&nbsp;`autoMode.allow` | array | | Rules for the auto mode classifier allow section. Replaces the built-in allow rules entirely unless the literal string "$defaults" is included as an entry, which splices the built-in defaults in at that position. |
| &nbsp;&nbsp;`autoMode.soft_deny` | array | | Rules for the auto mode classifier soft-deny section. Replaces the built-in soft-deny rules entirely unless the literal string "$defaults" is included as an entry, which splices the built-in defaults in at that position. |
| &nbsp;&nbsp;`autoMode.environment` | array | | Entries for the auto mode classifier environment section. Replaces the built-in environment context entirely unless the literal string "$defaults" is included as an entry, which splices the built-in defaults in at that position. |
| &nbsp;&nbsp;`autoMode.hard_deny` | array | | Rules for the auto mode classifier hard-deny section. Hard-deny rules block unconditionally regardless of user intent. Replaces the built-in hard-deny rules entirely unless the literal string "$defaults" is included as an entry, which splices the built-in defaults in at that position. |
| &nbsp;&nbsp;`autoMode.classifyAllShell` | boolean | | UNDOCUMENTED. Route all Bash/PowerShell commands through the auto mode classifier instead of only arbitrary-code-execution patterns (added in v2.1.193). |
| `defaultShell` | `bash` \| `powershell` | personal → `settings.local.json` / `~/.claude` | Default shell for input-box ! commands. Default: bash. Using "powershell" routes ! commands through PowerShell on Windows and requires CLAUDE_CODE_USE_POWERSHELL_TOOL=1 with pwsh on PATH. |
| `disableDeepLinkRegistration` | `disable` | project or personal | Set to "disable" to prevent Claude Code from registering the `claude-cli://` deep-link protocol handler on startup. Most useful in managed settings where users cannot override it. |
| `disableSkillShellExecution` | boolean | **live** in settings.json | Disable inline shell execution for `` !`...` `` and ` ```! ` blocks in skills and custom slash commands from user, project, plugin, or additional-directory sources. Commands are replaced with [shell command execution disabled by policy] instead of being run. Bundled and managed skills are not affected. Most useful in managed settings where users cannot override it. |
| `minimumVersion` | string | project or personal | Minimum Claude Code version to stay on. Prevents downgrades when switching release channels. |
| `showClearContextOnPlanAccept` | boolean | personal → `settings.local.json` / `~/.claude` | When true, the plan-approval dialog offers a "clear context" option. Defaults to false. |
| `showThinkingSummaries` | boolean | personal → `settings.local.json` / `~/.claude` | Show thinking summaries in the transcript view (Ctrl+O). Thinking summaries are not generated by default in interactive sessions; set to true to restore. |
| `skipDangerousModePermissionPrompt` | boolean | personal → `settings.local.json` / `~/.claude` | Whether the user has accepted the bypass permissions mode dialog. Typically managed by the CLI rather than set by hand. |
| `tui` | `fullscreen` \| `default` | personal → `settings.local.json` / `~/.claude` | TUI rendering mode. Use "fullscreen" for the flicker-free alt-screen renderer with virtualized scrollback; "default" for the classic main-screen renderer. Corresponds to the /tui command. |
| `viewMode` | `default` \| `verbose` \| `focus` | personal → `settings.local.json` / `~/.claude` | Transcript view mode. "default" shows standard interactive view; "verbose" shows expanded tool details; "focus" shows prompt, one-line tool summaries, and final response only (Ctrl+O toggle). |
| `useAutoModeDuringPlan` | boolean | project or personal | When true, apply the auto mode classifier during plan mode to auto-approve safe read-only tool calls while planning. Has no effect unless permissions.defaultMode allows auto. |
| `voiceEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Legacy alias for voice.enabled; prefer the voice object. Requires a Claude.ai account. |
| `subagentStatusLine` | object | project or personal | Status line configuration for subagent sessions. |
| &nbsp;&nbsp;`subagentStatusLine.type` | string | | Must be "command" |
| &nbsp;&nbsp;`subagentStatusLine.command` | string | | Shell command to run for the subagent status line |
| `advisorModel` | string | project or personal | Model for the server-side advisor tool. Accepts a model alias ("opus", "sonnet", or "fable" on v2.1.170+) or a full model ID. Overridden by the --advisor CLI flag for the session, and blocked when the model is outside the availableModels allowlist. |
| `autoCompactEnabled` | boolean | project or personal | Automatically compact the conversation when context approaches the limit. Also configurable via the DISABLE_AUTO_COMPACT environment variable. |
| `editorMode` | `normal` \| `vim` | personal → `settings.local.json` / `~/.claude` | Key binding mode for the input prompt: "normal" or "vim". Appears in /config as Editor mode. |
| `fallbackModel` | array | project or personal | Fallback model chain tried in order when the primary model is overloaded, unavailable, or returns a non-retryable server error. Capped at three entries after deduplication; accepts model names or aliases, and "default" expands to the account-type default. Overridden by the --fallback-model CLI flag for the session. |
| `fileCheckpointingEnabled` | boolean | project or personal | Snapshot edited files so /rewind can restore them. Also configurable via the CLAUDE_CODE_DISABLE_FILE_CHECKPOINTING environment variable (set to 1 to disable). |
| `gcpAuthRefresh` | string | personal → `settings.local.json` / `~/.claude` | Command to run when GCP credentials are expired or cannot be loaded. The command's output is displayed to the user but interactive input is not supported; it times out after three minutes. |
| `managedMcpServers` | array | project or personal | (Managed settings, third-party Desktop deployments only) MCP server configurations pushed to all users. Each entry specifies the transport and connection details, plus an optional toolPolicy map. Delivered through the managed settings file or MDM. |
| `skillListingMaxDescChars` | integer | project or personal | Per-skill character cap on the combined description and when_to_use text in the skill listing Claude sees each turn. Text longer than this is truncated. |
| `preferredNotifChannel` | `auto` \| `terminal_bell` \| `iterm2` \| `iterm2_with_bell` \| `kitty` \| `ghostty` \| `notifications_disabled` | personal → `settings.local.json` / `~/.claude` | Method for task-complete and permission-prompt notifications. "auto" (default) sends a desktop notification in iTerm2, Ghostty, and Kitty and does nothing in other terminals; "terminal_bell" rings the bell in any terminal; "notifications_disabled" turns them off. |
| `respondToBashCommands` | boolean | personal → `settings.local.json` / `~/.claude` | Whether Claude responds after an input-box ! shell command runs (v2.1.186+). Set to false to add the command output to context without a response. |
| `skillListingBudgetFraction` | number | project or personal | Fraction of the model context window reserved for the skill listing sent to Claude (default 0.01 = 1%). When the listing exceeds this, descriptions are shortened to fit. Also configurable via the SLASH_COMMAND_TOOL_CHAR_BUDGET environment variable (fixed character count). |
| `theme` | any | personal → `settings.local.json` / `~/.claude` | Color theme for the interface: auto, dark, light, the daltonized variants (deuteranopia-friendly), the ansi variants (16-color terminals), or a custom theme reference such as custom:<slug> or custom:<plugin-name>:<slug>. |
| `voice` | object | personal → `settings.local.json` / `~/.claude` | Voice dictation settings: enabled turns dictation on, mode selects "hold" or "tap", and autoSubmit sends the prompt on key release in hold mode. Written automatically when you run /voice. Requires a Claude.ai account. |
| &nbsp;&nbsp;`voice.enabled` | boolean | | Enable push-to-talk voice dictation input |
| &nbsp;&nbsp;`voice.mode` | `hold` \| `tap` | | Recording mode: "hold" (default) is push-to-talk; "tap" taps once to start and again to stop and submit |
| &nbsp;&nbsp;`voice.autoSubmit` | boolean | | In hold mode, auto-submit the prompt on key release when the transcript is at least three words long |
| `wheelScrollAccelerationEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | In fullscreen rendering, accelerate mouse-wheel scroll speed during fast scrolls (v2.1.174+). Set to false for a constant scroll rate per wheel notch. |
| `disableBundledSkills` | boolean | project or personal | Disable the skills and workflows that ship with Claude Code: bundled skills and workflows are removed entirely, while built-in slash commands like /init stay typable but are hidden from the model. Skills from plugins, .claude/skills/, and .claude/commands/ are unaffected. Also configurable via the CLAUDE_CODE_DISABLE_BUNDLED_SKILLS environment variable. |
| `awaySummaryEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Show a one-line session recap when you return to the terminal after a few minutes away. Set to false (or turn off Session recap in /config) to disable. |
| `autoScrollEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | In fullscreen rendering, follow new output to the bottom of the conversation. Appears in /config as Auto-scroll. Permission prompts still scroll into view when this is off. |
| `agentPushNotifEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | When Remote Control is connected, allow Claude to send proactive push notifications to your phone, for example when a long task finishes. Requires Claude Code v2.1.119 or later. |
| `axScreenReader` | boolean | personal → `settings.local.json` / `~/.claude` | Render screen-reader-friendly output: flat text without decorative borders or animations screen-reader mode always uses the classic renderer, so the tui setting has no effect while it is active. The CLAUDE_AX_SCREEN_READER environment variable and --ax-screen-reader flag take precedence. Requires Claude Code v2.1.181 or later. |
| `disableArtifact` | boolean | project or personal | Disable the Artifact tool, which publishes session output as a private web page on claude.ai. Also configurable via the CLAUDE_CODE_DISABLE_ARTIFACT environment variable. |
| `disableAutoMode` | `disable` | project or personal | Set to "disable" to prevent auto mode from being activated: removes auto from the Shift+Tab cycle and rejects --permission-mode auto at startup. |
| `disableClaudeAiConnectors` | boolean | project or personal | Disable claude.ai MCP connectors so they are not auto-fetched or connected. A value of true in any settings source takes precedence. Requires Claude Code v2.1.182 or later. |
| `disableRemoteControl` | boolean | project or personal | Disable Remote Control: blocks claude remote-control, the --remote-control flag, auto-start, and the in-session toggle. Requires Claude Code v2.1.128 or later. |
| `disableWorkflows` | boolean | project or personal | Disable dynamic workflows and bundled workflow commands. Also configurable via the CLAUDE_CODE_DISABLE_WORKFLOWS environment variable. |
| `footerLinksRegexes` | array | project or personal | Render extra clickable badges in the footer when a regex matches turn output (tool results and assistant responses). Read from user, --settings flag, and managed settings only; ignored in project and local settings. Requires Claude Code v2.1.176 or later. |
| `inputNeededNotifEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | When Remote Control is connected, send a push notification to your phone when a permission prompt or question is waiting for input. Requires Claude Code v2.1.119 or later. |
| `policyHelper` | object | project or personal | Admin-deployed executable that computes managed settings dynamically at startup. Honored only from MDM or the system managed-settings.json. Requires Claude Code v2.1.136 or later. |
| &nbsp;&nbsp;`policyHelper.path` | string | | Absolute path to the policy helper executable |
| &nbsp;&nbsp;`policyHelper.timeoutMs` | integer | | How long in milliseconds to wait for the helper before treating the run as failed |
| &nbsp;&nbsp;`policyHelper.refreshIntervalMs` | any | | How often in milliseconds to re-run the helper in the background; set to 0 to disable refresh, or to at least 60000 |
| `remoteControlAtStartup` | boolean | personal → `settings.local.json` / `~/.claude` | Connect Remote Control automatically when each interactive session starts. true = always, false = never, unset = organization default. Requires Claude Code v2.1.119 or later. |
| `syntaxHighlightingDisabled` | boolean | personal → `settings.local.json` / `~/.claude` | Disable syntax highlighting in diffs, code blocks, and file previews. |
| `verbose` | boolean | personal → `settings.local.json` / `~/.claude` | Show full tool output instead of truncated summaries. The --verbose flag overrides this for a single session. Requires Claude Code v2.1.119 or later. |
| `workflowKeywordTriggerEnabled` | boolean | project or personal | Whether including the keyword "ultracode" in a prompt triggers a dynamic workflow. Requires Claude Code v2.1.157 or later. |
| `askUserQuestionTimeout` | `60s` \| `5m` \| `10m` \| `never` | personal → `settings.local.json` / `~/.claude` | Idle time before an unanswered AskUserQuestion dialog auto-continues with whatever options you had already selected. Accepts "60s", "5m", "10m", or "never" (default: "never", which waits until you answer). Appears in /config as Question auto-continue timeout, which writes this key to user settings. Not read from project or local settings. Requires Claude Code v2.1.200 or later. |
| `teammateDefaultModel` | string/null | project or personal | Default model for agent team teammates when the spawn prompt does not specify one. Set to a model alias such as "sonnet", or null to inherit the lead's current /model selection. Appears in /config as Default teammate model. |
| `workflowSizeGuideline` | `unrestricted` \| `small` \| `medium` \| `large` | project or personal | Sets the agent count Claude aims for in the dynamic workflows it writes. Claude Code sends the value to Claude as advice, not an enforced cap. Accepts "unrestricted" (default, which sends no guideline), "small", "medium", or "large". Appears in /config as Dynamic workflow size, and can be set with /config workflowSizeGuideline=small. Requires Claude Code v2.1.202 or later. On v2.1.203 or later the guideline's agent count also replaces the default threshold for the Large workflow warning. |
| `enableArtifact` | boolean | personal → `settings.local.json` / `~/.claude` | Enable or disable the Artifact tool for this user. When unset, the default follows the feature's availability for your account. The Artifacts row in /config writes this key. A managed disableArtifact and your organization's admin setting take precedence, and the key is ignored in project and local settings (.claude/settings.json, .claude/settings.local.json), which a repository could otherwise commit. Requires Claude Code v2.1.196 or later. |
| `permissionExplainerEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Show a model-generated explanation of the command when you press Ctrl+E on a Bash or PowerShell permission prompt (default: true). Set to false to turn the shortcut off. |
| `diffTool` | `auto` \| `terminal` | personal → `settings.local.json` / `~/.claude` | Where to display file diffs when an IDE is connected: "auto" (default) opens diffs in the IDE's diff viewer, "terminal" keeps them in the terminal. Appears in /config as Diff tool only when Claude Code is connected to a VS Code or JetBrains IDE. |
| `externalEditorContext` | boolean | personal → `settings.local.json` / `~/.claude` | Prepend Claude's previous response as #-commented context when you open the external editor with Ctrl+G (default: false). Appears in /config as Show last response in external editor. |
| `autoConnectIde` | boolean | personal → `settings.local.json` / `~/.claude` | Automatically connect to a running IDE when Claude Code starts from an external terminal (default: false). Appears in /config as Auto-connect to IDE (external terminal) when running outside a VS Code or JetBrains terminal. Also configurable via the CLAUDE_CODE_AUTO_CONNECT_IDE environment variable, which overrides this when set. |
| `autoInstallIdeExtension` | boolean | personal → `settings.local.json` / `~/.claude` | Automatically install the Claude Code IDE extension when running from a VS Code terminal (default: true). Appears in /config as Auto-install IDE extension when running inside a VS Code or JetBrains terminal. You can also set the CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL environment variable to 1. |
| `emojiCompletionEnabled` | boolean | personal → `settings.local.json` / `~/.claude` | Show emoji suggestions when you type : plus a shortcode in the prompt input, and replace a completed shortcode such as :heart: with its emoji (default: true). Set to false to disable both. Requires Claude Code v2.1.217 or later. |
| `vimInsertModeRemaps` | object | personal → `settings.local.json` / `~/.claude` | Map two-key INSERT-mode sequences to Escape in vim editor mode. Each key is exactly two printable characters typed in sequence, and "<Esc>" is the only supported target; other entries are ignored. Read from user, --settings flag, and managed settings only, so a repository's checked-in settings cannot remap your keystrokes. Has no effect unless editorMode is "vim". Requires Claude Code v2.1.208 or later. |
| `processWrapper` | string | project or personal | Corporate launcher command placed in front of the background processes Claude Code starts. Honored from managed settings, a --settings file, and user settings only; the CLAUDE_CODE_PROCESS_WRAPPER environment variable takes precedence when both are set. Requires Claude Code v2.1.210 or later. |
| `forceLoginGatewayUrl` | string | project or personal | Pre-fills and locks the gateway URL on the /login Cloud gateway screen. Either this key or forceLoginMethod: "gateway" surfaces that screen; set both so the URL is filled in. Honored only at the managed policy tier; ignored in user and project settings. |

## Managed-only keys (26)

Honored only in managed (organization) settings. Listed for completeness; they have no effect in project or user files.

| Key | Type / values | Description |
| --- | --- | --- |
| `allowedChannelPlugins` | array | (Managed settings only) Allowlist of channel plugins that may run, each identified by its marketplace and plugin name. When set, only the listed plugins can push inbound channel messages while channelsEnabled is true. Replaces the default Anthropic allowlist when set; undefined falls back to the default and an empty array blocks all channel plugins. Requires channelsEnabled: true. |
| `allowManagedHooksOnly` | boolean | (Managed settings only) Prevent loading of user, project, and plugin hooks. Only allows managed hooks and SDK hooks. |
| `allowManagedPermissionRulesOnly` | boolean | (Managed settings only) Prevent user and project settings from defining allow, ask, or deny permission rules. Only rules in managed settings apply. |
| `strictKnownMarketplaces` | array | (Managed settings only) Allowlist of plugin marketplaces users can add. Undefined = no restrictions, empty array = lockdown. Uses exact matching for source specifications. |
| `parentSettingsBehavior` | `first-wins` \| `merge` | (Admin/managed settings only) Controls how SDK managedSettings (parent tier) merge with inherited settings. 'first-wins': first non-empty value applies (default). 'merge': merge arrays and objects. |
| `pluginTrustMessage` | string | (Managed settings only) Custom message appended to the plugin trust warning shown before installation. Use to provide organization-specific context about approved plugins. |
| `allowManagedMcpServersOnly` | boolean | (Managed settings only) When true, only allowedMcpServers from managed settings are respected; MCP servers defined in user, project, or local settings are ignored. deniedMcpServers still merges from all sources. |
| `blockedMarketplaces` | array | (Managed settings only) Blocklist of marketplace sources. These exact sources are blocked from being added as marketplaces. The check happens before downloading, so blocked sources never touch the filesystem. |
| `channelsEnabled` | boolean | (Managed settings only) Allow channels for the organization. On claude.ai Team and Enterprise plans, channels are blocked when this is unset or false. For Anthropic Console accounts using API key authentication, channels are allowed by default unless the organization deploys managed settings, in which case this key must be set to true. |
| `forceRemoteSettingsRefresh` | boolean | (Managed settings only) Block CLI startup until remote managed settings are freshly fetched from the server. If the fetch fails, the CLI exits (fail-closed) rather than continuing with cached settings. When not set, startup continues without waiting for remote settings. |
| `strictPluginOnlyCustomization` | any | (Managed settings) Block non-plugin customization sources for the listed surfaces. Array form locks specific surfaces (e.g., ["skills", "hooks"]); true locks all four; false is an explicit no-op. |
| `wslInheritsWindowsSettings` | boolean | (Windows managed settings only) When true, Claude Code on WSL reads managed settings from the Windows policy chain in addition to /etc/claude-code, with Windows sources taking priority. Only honored when set in the HKLM registry key or C:\Program Files\ClaudeCode\managed-settings.json, both of which require Windows admin to write. For HKCU policy to also apply on WSL, the flag must additionally be set in HKCU itself. Has no effect on native Windows. |
| `disableAgentView` | boolean | (Managed settings) Turn off background agents and the agent view: claude agents, --bg, /background, and the on-demand supervisor. Also configurable via the CLAUDE_CODE_DISABLE_AGENT_VIEW environment variable (set to 1 to disable). |
| `enforceAvailableModels` | boolean | (Managed settings) Extend the availableModels allowlist to the Default model option (requires v2.1.175+). Requires a non-empty availableModels list; when the account-type default is not in the allowlist, Default resolves to the first allowed entry instead. Has no effect when availableModels is unset or empty. |
| `pluginSuggestionMarketplaces` | array | (Managed settings only) Allowlist of marketplace names whose plugins may surface as contextual "suggested for this directory" tips in the /plugin Discover tab. No marketplace-declared suggestions surface without this allowlist. The built-in first-party frontend-design tip is unaffected. |
| `requiredMaximumVersion` | string | (Managed settings only) Maximum Claude Code version allowed to start. If the running version is newer, Claude Code exits at startup with instructions to install an approved version. |
| `requiredMinimumVersion` | string | (Managed settings only) Minimum Claude Code version required to start. If the running version is older, Claude Code exits at startup rather than only warning. |
| `sshConfigs` | array | (Managed settings) Pre-configured SSH connections distributed to Desktop users. |
| `sshHostAllowlist` | array | (Managed settings only) Allowlist restricting Desktop SSH sessions to approved hosts. Patterns are case-insensitive; * matches any host and *.example.com matches example.com and any subdomain. |
| `allowAllClaudeAiMcps` | boolean | (Managed settings only) Load claude.ai connectors alongside a deployed managed-mcp.json, which otherwise takes exclusive control and suppresses them. |
| `claudeMd` | string | (Managed settings only) CLAUDE.md-style instructions injected as organization-managed memory. Honored only from managed/policy settings. |
| `disableSideloadFlags` | boolean | (Managed settings only) Reject the --plugin-dir, --plugin-url, --agents, and --mcp-config CLI flags at startup, which users could otherwise pass to bypass strictKnownMarketplaces for a single run. Also rejects these flags from any surface that spawns the CLI with them internally, currently Cowork local sessions in the desktop app. A --mcp-config whose servers are all in-process type: "sdk" entries is still accepted, so the Agent SDK and VS Code extension keep working. Does not block claude mcp add, .mcp.json, or SDK setMcpServers(); pair with allowedMcpServers for per-server MCP control. Requires Claude Code v2.1.193 or later. |
| `browserExternalPageTools` | `disabled` | (Managed settings only) Set to "disabled" to prevent Claude from using tools to read or act on external pages in the desktop app's Browser pane. Users can still navigate to external sites themselves, and local dev server previews are unaffected. |
| `disableBrowserExternalNavigation` | boolean | (Managed settings only) Set to true to turn off external browsing in the desktop app's Browser pane. Neither users nor Claude can navigate to external sites, and localhost dev server previews are unaffected. The value must be the JSON boolean true; the string "true" is ignored. |
| `disableMobileSimulatorTools` | boolean | (Managed settings only) Set to true to block Claude's tools for the desktop app's iOS Simulator pane. Users keep manual use of the pane; only Claude's access is removed. The value must be the JSON boolean true; any other value is ignored, and a malformed value such as "true" or 1 logs a warning. |
| `requireCoworkFullVmSandbox` | boolean | (Managed settings only) Run Claude's tools inside an isolated virtual machine instead of on your Mac. Disables the desktop app's iOS Simulator pane and Claude's simulator tools entirely, so the pane cannot attach a device while it is set. |

## Environment variables

Many behaviors are set only through env vars, either in the shell or in the settings `env` block (see the [full list](https://code.claude.com/docs/en/env-vars)). Common ones:
`ANTHROPIC_MODEL`, `CLAUDE_CODE_SUBAGENT_MODEL`, `MAX_THINKING_TOKENS`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `BASH_DEFAULT_TIMEOUT_MS`, `BASH_MAX_TIMEOUT_MS`,
`MCP_TIMEOUT`, `MAX_MCP_OUTPUT_TOKENS`, `ENABLE_TOOL_SEARCH`, `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `DISABLE_TELEMETRY`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`.

Project hook config (read by `.claude/hooks/*.sh`, set in `settings.json` → `env`):

| Var | Effect |
| --- | --- |
| `CLAUDE_HOOK_FORMAT_MAP` | per-extension formatters run after each Edit/Write: `"py=uv run ruff format;ts,tsx=pnpm exec biome format --write"` (file path appended) |
| `CLAUDE_HOOK_FORMAT_CMD` | fallback formatter for extensions not in the map. Both empty = off |
| `CLAUDE_HOOK_STOP_CHECK_CMD` | command that must pass before Claude may finish a turn. Empty = off |
| `CLAUDE_HOOK_PROTECTED_GLOBS` | colon-separated globs that Edit/Write may not touch |
| `CLAUDE_HOOK_LOG` | `1` = log hook activity to `.claude/logs/hooks.log` |
