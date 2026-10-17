#!/usr/bin/env python3
"""Select rows from a VastDB table (skips vector columns by default)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

VECTOR_COLS = frozenset({"vectors", "vectors_visual"})


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


def column_names(table) -> list[str]:
    cols = table.columns
    if callable(cols):
        cols = cols()
    names = []
    for c in cols:
        names.append(c.name if hasattr(c, "name") else str(c))
    return names


def json_sanitize(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Select VastDB rows via vastdb SDK")
    parser.add_argument("--schema", help="Default VDB_SCHEMA")
    parser.add_argument("--table", help="Default VDB_COLLECTION")
    parser.add_argument("--bucket", help="Default VASTDB_BUCKET")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--columns",
        help="Comma-separated columns (default: all except vectors / vectors_visual)",
    )
    parser.add_argument(
        "--include-vectors",
        action="store_true",
        help="Include vectors / vectors_visual (often fails on SDK select)",
    )
    args = parser.parse_args()

    env = load_env(_config_path())
    access = env.get("VAST_ACCESS_KEY") or env.get("ACCESS_KEY", "")
    secret = env.get("VAST_SECRET_KEY") or env.get("SECRET_KEY", "")
    endpoint = os.environ.get("VDB_ENDPOINT") or env.get("VDB_ENDPOINT") or env.get("S3_ENDPOINT", "")
    if not access or not secret or not endpoint:
        print("Need ACCESS_KEY, SECRET_KEY, S3_ENDPOINT in /config/<team>.config", file=sys.stderr)
        sys.exit(1)

    bucket = args.bucket or env.get("VASTDB_BUCKET", "")
    schema_name = args.schema or env.get("VDB_SCHEMA", "vss-schema")
    table_name = args.table or env.get("VDB_COLLECTION", "vss-collection")
    if not bucket:
        print("Set VASTDB_BUCKET or --bucket", file=sys.stderr)
        sys.exit(1)

    import vastdb

    session = vastdb.connect(
        endpoint=normalize_endpoint(endpoint),
        access=access,
        secret=secret,
        ssl_verify=False,
    )
    with session.transaction() as tx:
        try:
            table = tx.bucket(bucket).schema(schema_name).table(table_name)
            names = column_names(table)
            if args.columns:
                cols = [c.strip() for c in args.columns.split(",") if c.strip()]
            else:
                cols = [n for n in names if args.include_vectors or n not in VECTOR_COLS]
            if not cols:
                print("No columns to select", file=sys.stderr)
                sys.exit(1)
            reader = table.select(columns=cols)
            rows = []
            for batch in reader:
                part = batch.to_pylist()
                rows.extend(part)
                if args.limit and len(rows) >= args.limit:
                    rows = rows[: args.limit]
                    break
        except Exception as e:
            msg = str(e)
            if "403" in msg or "Forbidden" in msg:
                print(
                    f"Denied on {bucket}/{schema_name}/{table_name}: {e}\n"
                    "Stay in this team's VASTDB_BUCKET (identity policy).",
                    file=sys.stderr,
                )
                sys.exit(1)
            raise

    clean = [{k: json_sanitize(v) for k, v in row.items()} for row in rows]
    print(json.dumps({"bucket": bucket, "schema": schema_name, "table": table_name, "n": len(clean), "rows": clean}, indent=2))


if __name__ == "__main__":
    main()
