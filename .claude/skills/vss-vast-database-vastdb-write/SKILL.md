---
name: vast-database-vastdb-write
description: >-
  Write to the team's VastDB with the vastdb Python SDK — create schemas/tables
  and insert rows on the existing database (bucket). Always connect to the data
  VIP from S3_ENDPOINT in /config/<team>.config. Use when hackathon apps need
  custom tables alongside vss-collection (not for editing DataEngine pipelines).
---

# Vast Database: write (vss2)

Create schemas/tables and insert rows with the `vastdb` Python SDK on the team's
existing VastDB **bucket**. Always use the **data VIP** — never the Query Engine VIP
for DDL/DML.

Identity policy still applies: only this team's `VASTDB_BUCKET`. Other buckets → 403.

## Endpoint (data VIP only)

```bash
mapfile -t TEAM_CONFIGS < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
(( ${#TEAM_CONFIGS[@]} == 1 )) || { echo "expected exactly one /config/*.config"; exit 1; }
CFG="${TEAM_CONFIGS[0]}"
# Do not `source` on zsh (USERNAME is reserved).
S3_ENDPOINT=$(grep '^S3_ENDPOINT=' "$CFG" | cut -d= -f2-)
ACCESS_KEY=$(grep '^ACCESS_KEY=' "$CFG" | cut -d= -f2-)
SECRET_KEY=$(grep '^SECRET_KEY=' "$CFG" | cut -d= -f2-)
VASTDB_BUCKET=$(grep '^VASTDB_BUCKET=' "$CFG" | cut -d= -f2-)
VDB_SCHEMA=$(grep '^VDB_SCHEMA=' "$CFG" | cut -d= -f2-)
DATA_VIP="$S3_ENDPOINT"   # must include http:// or https://
```

| Role | Source | Write? |
|------|--------|--------|
| **Data VIP** | `S3_ENDPOINT` in team config | **Yes** — create / insert |
| Query Engine VIP | K8s `video-backend-secret` → `vdb_endpoint` | **No** — use data VIP |

Never search `team-configs/`, invent endpoints, or print credentials.

## Safety

- Prefer **new** schema/table names for demos (e.g. `hackathon`, `demo_events`).
- Do **not** drop or recreate `vss-collection` / `vss-prompts-events` unless the user explicitly insists — that breaks VSS search.
- Stay in **this team's** `VASTDB_BUCKET` only.

## Prereqs

```bash
pip install vastdb pyarrow
```

## Insert (script)

[insert.py](insert.py) creates `hackathon.demo_events` if needed and inserts rows:

```bash
python .cursor/skills/vast-database/vastdb-write/insert.py --example
python .cursor/skills/vast-database/vastdb-write/insert.py --schema hackathon --table demo_events --json rows.json
echo '[{"id":3,"label":"ok","score":0.5,"note":"x"}]' | python .cursor/skills/vast-database/vastdb-write/insert.py
```

Verify with `vast-database/vastdb-read` (`list_catalog.py` / `query.py --schema hackathon --table demo_events`).

## Create schema + table + insert (inline)

```python
import pyarrow as pa
import vastdb

session = vastdb.connect(
    endpoint=DATA_VIP,
    access=ACCESS_KEY,
    secret=SECRET_KEY,
    ssl_verify=False,
)

columns = pa.schema([
    ("id", pa.int64()),
    ("label", pa.utf8()),
    ("score", pa.float32()),
    ("note", pa.utf8()),
])

with session.transaction() as tx:
    bucket = tx.bucket(VASTDB_BUCKET)
    schema = bucket.schema("hackathon", fail_if_missing=False)
    if schema is None:
        schema = bucket.create_schema("hackathon", fail_if_exists=False)

    table = schema.table("demo_events", fail_if_missing=False)
    if table is None:
        table = schema.create_table("demo_events", columns=columns, fail_if_exists=False)

    arrow = pa.table(
        {
            "id": [1, 2],
            "label": ["near_miss", "clear"],
            "score": [0.91, 0.12],
            "note": ["forklift close to person", "aisle empty"],
        },
        schema=columns,
    )
    table.insert(arrow)
```

## Create table under the existing VSS schema

Allowed if the user wants a sibling table next to `vss-collection`:

```python
with session.transaction() as tx:
    schema = tx.bucket(VASTDB_BUCKET).schema(VDB_SCHEMA)  # e.g. vss-schema
    table = schema.table("my_app_results", fail_if_missing=False)
    if table is None:
        table = schema.create_table("my_app_results", columns=columns, fail_if_exists=False)
    table.insert(arrow)
```

## Agent instructions

1. Confirm the target **schema / table** and column schema with the user before creating.
2. Connect only to **`S3_ENDPOINT` (data VIP)**. Do not use QE for writes.
3. Never copy `/config/` credentials into the repo.
4. Refuse casual recreate/drop of `vss-collection` or `vss-prompts-events`.
5. After writes, prove with `query.py` or `list_catalog.py`.
6. Do not write other teams’ buckets (identity policy + `insert.py` refuses a mismatched `--bucket`).
