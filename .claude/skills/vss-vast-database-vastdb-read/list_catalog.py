#!/usr/bin/env python3
"""List VastDB schemas/tables via the vastdb Python SDK (this team's bucket by default)."""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path


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


ENV_PATH = _config_path()

INTERNAL_TABLES = frozenset({"tabular_schema_table"})


def load_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        print(f"Missing team config: {path}", file=sys.stderr)
        sys.exit(1)

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


def resolve_endpoint(env: dict[str, str]) -> str:
    endpoint = (
        os.environ.get("VDB_ENDPOINT")
        or env.get("VDB_ENDPOINT")
        or env.get("S3_ENDPOINT", "")
    )
    if not endpoint:
        print(
            "Set S3_ENDPOINT (data VIP) in /config/<team>.config "
            "(or VDB_ENDPOINT / env override)",
            file=sys.stderr,
        )
        sys.exit(1)
    return normalize_endpoint(endpoint)


def parse_path_parts(parent_path: str) -> list[str]:
    return [p for p in parent_path.strip("/").split("/") if p]


def die_forbidden(bucket: str, err: BaseException) -> None:
    print(
        f"403/denied on bucket {bucket!r}: {err}\n"
        "Identity policy still applies (JWT API is not the ACL). "
        "Use this team's VASTDB_BUCKET only.",
        file=sys.stderr,
    )
    sys.exit(1)


def catalog_tree(endpoint: str, access: str, secret: str) -> dict[str, dict[str, list[str]]]:
    """Build database → schema → [tables] from tx.catalog() SCHEMA/TABLE rows."""
    import vastdb

    tree: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    session = vastdb.connect(endpoint=endpoint, access=access, secret=secret, ssl_verify=False)
    with session.transaction() as tx:
        catalog = tx.catalog(fail_if_missing=False)
        if catalog is None:
            return {}
        rows = catalog.select(columns=["element_type", "name", "parent_path"]).read_all().to_pylist()

    for row in rows:
        if row.get("element_type") != "SCHEMA":
            continue
        parts = parse_path_parts(row.get("parent_path") or "")
        if len(parts) != 1:
            continue
        tree[parts[0]][row["name"]]

    for row in rows:
        if row.get("element_type") != "TABLE":
            continue
        if row.get("name") in INTERNAL_TABLES:
            continue
        parts = parse_path_parts(row.get("parent_path") or "")
        if len(parts) != 2:
            continue
        bucket, schema = parts
        tables = tree[bucket][schema]
        if row["name"] not in tables:
            tables.append(row["name"])

    return {
        db: {sch: sorted(tables) for sch, tables in sorted(schemas.items())}
        for db, schemas in sorted(tree.items())
    }


def live_bucket_tree(
    endpoint: str, access: str, secret: str, bucket: str
) -> dict[str, dict[str, list[str]]]:
    """Live drill-down via bucket.schemas() / schema.tables()."""
    import vastdb
    from vastdb.errors import Conflict

    tree: dict[str, dict[str, list[str]]] = {bucket: {}}
    session = vastdb.connect(endpoint=endpoint, access=access, secret=secret, ssl_verify=False)
    with session.transaction() as tx:
        try:
            schemas = list(tx.bucket(bucket).schemas())
        except Conflict:
            return {}
        except Exception as e:
            msg = str(e)
            if "403" in msg or "Forbidden" in msg or "AccessDenied" in msg:
                die_forbidden(bucket, e)
            raise

        for schema in schemas:
            tables = []
            for table in schema.tables():
                if table.name not in INTERNAL_TABLES:
                    tables.append(table.name)
            tree[bucket][schema.name] = sorted(tables)
    return tree


def print_tree(tree: dict[str, dict[str, list[str]]]) -> None:
    if not tree:
        print("No VastDB databases/schemas found.")
        return

    print(f"{'DATABASE (bucket)':<40} {'SCHEMA':<30} TABLES")
    print("-" * 100)
    for bucket, schemas in tree.items():
        if not schemas:
            print(f"{bucket:<40} (no schemas)")
            continue
        for i, (schema, tables) in enumerate(sorted(schemas.items())):
            table_str = ", ".join(tables) if tables else "(no tables)"
            if i == 0:
                print(f"{bucket:<40} {schema:<30} {table_str}")
            else:
                print(f"{'':<40} {schema:<30} {table_str}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List VastDB catalog via vastdb SDK")
    parser.add_argument(
        "--bucket",
        help="Bucket to list (default: VASTDB_BUCKET from team config)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="List every database in tx.catalog() (other teams may 403)",
    )
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    access = env.get("VAST_ACCESS_KEY") or env.get("ACCESS_KEY", "")
    secret = env.get("VAST_SECRET_KEY") or env.get("SECRET_KEY", "")
    if not access or not secret:
        print("Set ACCESS_KEY/SECRET_KEY in /config/<team>.config", file=sys.stderr)
        sys.exit(1)

    endpoint = resolve_endpoint(env)
    print(f"VastDB endpoint: {endpoint}\n")

    own_bucket = env.get("VASTDB_BUCKET", "")
    bucket = args.bucket or own_bucket

    if args.all:
        tree = catalog_tree(endpoint, access, secret)
        print_tree(tree)
        return

    if not bucket:
        print("Set VASTDB_BUCKET in team config, or pass --bucket / --all", file=sys.stderr)
        sys.exit(1)

    print_tree(live_bucket_tree(endpoint, access, secret, bucket))


if __name__ == "__main__":
    main()
