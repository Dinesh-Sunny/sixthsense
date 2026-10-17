---
name: retrieval-login
description: >-
  Authenticate to the VSS retrieval backend and get a JWT via POST /api/v1/auth/login
  (VAST username/password → bearer token), verify it with GET /api/v1/auth/me, and pass
  it on later calls. Use first for any authenticated retrieval/ingest backend request.
---

# Retrieval: login (vss2)

The backend authenticates the user against VMS and returns a JWT. VMS host + tenant come from **backend config**, not the request — you only send username/password.

## Login

`POST /api/v1/auth/login`, body `{ "username", "password" }` → `{ access_token, token_type: "bearer", username }`.

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
TEAM_CONFIG="${TEAM_CONFIGS[0]}"
set -a && source "$TEAM_CONFIG" && set +a
BACKEND="$INGRESS_URL"
TOKEN=$(curl -s -X POST "$BACKEND/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

Only read team credentials from `/config/<team>.config`; never search the repo's
`team-configs/`, echo credentials, or copy them into the repo.

401 = bad credentials (or user not valid for the tenant configured in the backend).

## Use the token

- Most routes: header `Authorization: Bearer $TOKEN`.
- `/videos/stream`, `/videos/playback-url`: JWT as `?token=$TOKEN` query param (browser `<video>` limitation).

```bash
curl -s "$BACKEND/api/v1/auth/me" -H "Authorization: Bearer $TOKEN"   # {username,email,auth_type}
```

## Notes

- This is the backend-issued JWT (retrieval/ingest APIs). It is **separate** from raw VastDB SDK access (`vast-database/vastdb-read`).
- Token lifetime is set by backend config; on 401 during a session, re-login.
- Every result is ACL-filtered to this user (private rows + public rows they can see).

## Agent instructions

1. Ask for/confirm username + password; never log the password or token.
2. Cache the token for the session; re-login on 401.
3. Then proceed to `search`, `dashboard`, `videos`, `agent-qa`, etc.
