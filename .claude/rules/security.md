<!-- last-verified: 2026-10-01 -->
# Security

- Never read, print, log, or commit secrets. Use env vars; reference `.env.example` for names only.
- Validate and parse all external input at the boundary (plain type checks at the HTTP boundary).
- Parameterized queries only. No string-built SQL, shell, or HTML.
- AuthN/AuthZ checks go on the server, on every protected route/action. Never trust the client.
- Escape output by default. No `dangerouslySetInnerHTML` / `eval` / `exec` with user data.
- New dependency → check maintenance, license, and known CVEs; ask before adding.
- Least privilege for tokens, DB roles, and cloud IAM.
- When in doubt, stop and flag it to the user instead of guessing.
