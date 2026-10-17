---
name: vast-database-vastdb-read
description: >-
  Read the team's VastDB store with the vastdb Python SDK — list catalog
  (databases/schemas/tables) and select rows. Connect to the data VIP from
  S3_ENDPOINT in /config/<team>.config; optionally use the Query Engine VIP from
  the backend K8s secret. Use for raw DB inspection that bypasses the JWT API.
---

# Vast Database: read (vss2)

Direct access to VastDB with the `vastdb` Python SDK (**not** the JWT backend). Use for
catalog listing and `select` — e.g. “what tables exist?” / “did this row land?”.

This skips the VSS HTTP API. **Identity policy still applies**: other teams’ buckets
return `403 Forbidden`. Stay in `VASTDB_BUCKET`.

## Endpoints (important)

| Role | Where to get it | Use for |
|------|-----------------|--------|
| **Data VIP** | `S3_ENDPOINT` in `/config/<team>.config` | Default SDK connect — catalog, select |
| **Query Engine VIP** | Backend secret `vdb_endpoint` (file or K8s) | When you specifically need QE reads |

Prefer the **data VIP** (`S3_ENDPOINT`) unless the user asks for the Query Engine.

### Data VIP from team config

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
# Do not `source` on zsh (USERNAME is reserved). Parse keys:
S3_ENDPOINT=$(grep '^S3_ENDPOINT=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
ACCESS_KEY=$(grep '^ACCESS_KEY=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
SECRET_KEY=$(grep '^SECRET_KEY=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
VASTDB_BUCKET=$(grep '^VASTDB_BUCKET=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
VDB_SCHEMA=$(grep '^VDB_SCHEMA=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
VDB_COLLECTION=$(grep '^VDB_COLLECTION=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)
DATA_VIP="$S3_ENDPOINT"
```

Never search the repo's `team-configs/` or echo credentials.

### Query Engine VIP from K8s (optional)

```bash
NS=$(grep '^USERNAME=' "${TEAM_CONFIGS[0]}" | cut -d= -f2-)   # team namespace, e.g. team-11
export KUBECONFIG=/config/${NS}-k8s.yaml                     # e.g. /config/team-11-k8s.yaml

# 1) Prefer file if present:
#    /config/backend-secret.yaml → stringData.config.yaml → vdb_endpoint

# 2) Else from the live secret:
kubectl get secret video-backend-secret -n "$NS" -o jsonpath='{.data.config\.yaml}' \
  | base64 -d | python3 -c "
import sys,yaml
c=yaml.safe_load(sys.stdin)
print(c.get('vdb_endpoint') or '')
"
```

If `/config/backend-secret.yaml` exists, read `vdb_endpoint` from its embedded `config.yaml` the same way. Do not invent the QE host.

To force QE for a script: `VDB_ENDPOINT=<qe-url> python …/query.py`

**Note:** Data VIP (`S3_ENDPOINT` / ingest `vdbendpoint`) and QE (`vdb_endpoint`) are **different by design** — see `deployment/build-yamls`.

## VSS defaults (from team config)

| Thing | Config key | Typical value |
|-------|------------|---------------|
| Database (bucket) | `VASTDB_BUCKET` | `team-<N>-vss-db` |
| Schema | `VDB_SCHEMA` | `vss-schema` |
| Main table | `VDB_COLLECTION` | `vss-collection` |
| Prompts table | `VDB_PROMPTS_COLLECTION` | `vss-prompts-events` |

## Prereqs

```bash
pip install vastdb pyarrow pyyaml
```

On the hackathon VM the data VIP is usually reachable directly — **no SSH tunnel required**.
Only tunnel if connect fails from your network.

## List the catalog

[list_catalog.py](list_catalog.py) lists **this team’s** `VASTDB_BUCKET` by default:

```bash
python .cursor/skills/vast-database/vastdb-read/list_catalog.py
python .cursor/skills/vast-database/vastdb-read/list_catalog.py --bucket "$VASTDB_BUCKET"
python .cursor/skills/vast-database/vastdb-read/list_catalog.py --all   # every DB in catalog
```

## Select rows

Prefer [query.py](query.py) (do not name a file `select.py` — it shadows stdlib `select` and breaks `vastdb`). It **omits `vectors` / `vectors_visual`** unless `--include-vectors`.

```bash
python .cursor/skills/vast-database/vastdb-read/query.py
python .cursor/skills/vast-database/vastdb-read/query.py --table vss-prompts-events --limit 5
python .cursor/skills/vast-database/vastdb-read/query.py --columns pk,filename,source --limit 20
```

Never call `table.select()` with no columns on `vss-collection` — vector types can crash the SDK.

```python
import vastdb

session = vastdb.connect(
    endpoint=DATA_VIP,   # or QE VIP if requested
    access=ACCESS_KEY,
    secret=SECRET_KEY,
    ssl_verify=False,
)
VECTOR = ("vectors", "vectors_visual")
with session.transaction() as tx:
    table = tx.bucket(VASTDB_BUCKET).schema(VDB_SCHEMA).table(VDB_COLLECTION)
    cols = [c.name for c in table.columns() if c.name not in VECTOR]
    batch = table.select(columns=cols).read_all()
    rows = batch.to_pylist()
    print(len(rows), rows[0] if rows else "empty")
```

## Common checks

- **Row count / recent writes**: sort by `timestamp` / `upload_timestamp`.
- **Missing segment**: filter by `original_video` or `source`.
- **Dims**: `vectors` length must be **256** for the VSS collection.

## Agent instructions

1. Resolve **data VIP** from `S3_ENDPOINT` in the single `/config/*.config`. For QE, use `/config/backend-secret.yaml` or `kubectl … video-backend-secret` — never guess.
2. Use team `VASTDB_BUCKET` / `VDB_SCHEMA` / `VDB_COLLECTION` — don’t hardcode `vss-db` unless the config says so.
3. Never copy credentials into the repo or print secrets/tokens.
4. Exclude vector columns unless explicitly needed.
5. A 403 on another team’s bucket is identity policy, not a skill bug.
6. For **create schema/table / insert**, use `vast-database/vastdb-write` (always data VIP).
7. User-scoped VSS UI data should still go through `retrieval/dashboard` / `retrieval/videos` when that is the product path.
