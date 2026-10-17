#!/usr/bin/env python3
"""Create a schema/table if needed and insert JSON rows into this team's VastDB bucket."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROTECTED = frozenset({"vss-collection", "vss-prompts-events"})


def _team_config() -> Path:
    configs = sorted(Path("/config").glob("*.config"))
    if len(configs) != 1:
        print(
            f"Expected exactly one /config/*.config team file; found {len(configs)}",
            file=sys.stderr,
        )
        sys.exit(1)
    return configs[0]


def _config_path() -> Path:
    override = os.environ.get("VAST_ENV_FILE")
    if override:
        return Path(override)
    return _team_config()


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def normalize_endpoint(url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"http://{url}"


def arrow_schema_from_rows(rows: list[dict]):
    import pyarrow as pa

    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    fields = []
    for k in keys:
        sample = next((r[k] for r in rows if r.get(k) is not None), None)
        if isinstance(sample, bool):
            fields.append((k, pa.bool_()))
        elif isinstance(sample, int):
            fields.append((k, pa.int64()))
        elif isinstance(sample, float):
            fields.append((k, pa.float32()))
        else:
            fields.append((k, pa.utf8()))
    return pa.schema(fields)


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert JSON rows into VastDB (data VIP)")
    parser.add_argument("--schema", default="hackathon")
    parser.add_argument("--table", default="demo_events")
    parser.add_argument("--bucket", help="Default VASTDB_BUCKET (must be this team)")
    parser.add_argument("--json", help="JSON file: object or array of objects (stdin if omitted)")
    parser.add_argument(
        "--example",
        action="store_true",
        help="Insert two demo rows (near_miss / clear) instead of --json",
    )
    args = parser.parse_args()

    env = load_env(_config_path())
    access = env.get("VAST_ACCESS_KEY") or env.get("ACCESS_KEY", "")
    secret = env.get("VAST_SECRET_KEY") or env.get("SECRET_KEY", "")
    endpoint = env.get("S3_ENDPOINT", "")
    own = env.get("VASTDB_BUCKET", "")
    bucket = args.bucket or own
    if not access or not secret or not endpoint:
        print("Need ACCESS_KEY, SECRET_KEY, S3_ENDPOINT in /config/<team>.config", file=sys.stderr)
        sys.exit(1)
    if not bucket:
        print("Set VASTDB_BUCKET or --bucket", file=sys.stderr)
        sys.exit(1)
    if own and bucket != own:
        print(
            f"Refusing to write {bucket!r}; team bucket is {own!r}. "
            "Identity policy only allows this team's DB.",
            file=sys.stderr,
        )
        sys.exit(1)
    if args.table in PROTECTED:
        print(
            f"Refusing to insert into protected table {args.table}. "
            "Use a new table unless the user explicitly insists.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.example:
        rows = [
            {"id": 1, "label": "near_miss", "score": 0.91, "note": "forklift close to person"},
            {"id": 2, "label": "clear", "score": 0.12, "note": "aisle empty"},
        ]
    else:
        raw = Path(args.json).read_text() if args.json else sys.stdin.read()
        data = json.loads(raw)
        rows = data if isinstance(data, list) else [data]
    if not rows:
        print("No rows to insert", file=sys.stderr)
        sys.exit(1)

    import pyarrow as pa
    import vastdb

    schema_pa = arrow_schema_from_rows(rows)
    table_arrow = pa.Table.from_pylist(rows, schema=schema_pa)

    session = vastdb.connect(
        endpoint=normalize_endpoint(endpoint),
        access=access,
        secret=secret,
        ssl_verify=False,
    )
    with session.transaction() as tx:
        try:
            bkt = tx.bucket(bucket)
            schema = bkt.schema(args.schema, fail_if_missing=False)
            if schema is None:
                schema = bkt.create_schema(args.schema, fail_if_exists=False)
            table = schema.table(args.table, fail_if_missing=False)
            if table is None:
                table = schema.create_table(args.table, columns=schema_pa, fail_if_exists=False)
            table.insert(table_arrow)
        except Exception as e:
            msg = str(e)
            if "403" in msg or "Forbidden" in msg:
                print(
                    f"Denied writing {bucket}/{args.schema}/{args.table}: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)
            raise

    print(json.dumps({"ok": True, "bucket": bucket, "schema": args.schema, "table": args.table, "n": len(rows)}))


if __name__ == "__main__":
    main()
