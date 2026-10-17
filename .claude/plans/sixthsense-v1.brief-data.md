# sixthsense-v1 data brief: vastdb 2.1.0 + pyarrow (store.py)
Sources: vastdb_sdk raw main (bucket.py, session.py, table.py, config.py) fetched 2026-10-17; skills vastdb-read/-write; lib/vastdb.yaml.

## vastdb brief (v2.1.0) - APIs to use
- `vastdb.connect(endpoint=S3_ENDPOINT, access=, secret=, ssl_verify=settings.vast_ssl_verify, timeout=, backoff_config=BackoffConfig(max_tries=3, max_time=15))` (session.py; BackoffConfig from `vastdb.config`: wait_gen, max_value, max_tries=10, max_time=60). Session.__init__ queries the cluster version, so connect hits the network: build it lazily in lifespan inside try/except, not at import.
- DDL, once at startup in one tx: `tx.bucket(VASTDB_BUCKET)` -> `bucket.schema(name, fail_if_missing=False)` or `bucket.create_schema(name, fail_if_exists=False)` (Bucket.create_schema confirmed in bucket.py) -> `schema.table(name, fail_if_missing=False)` or `schema.create_table(name, columns=pa.schema(...), fail_if_exists=False)`.
- Read: `table.select(columns=[...], predicate=(_.mode == m), limit_rows=n, internal_row_id=False).read_all()` with `from ibis import _`; `.to_pylist()` INSIDE the tx; sort in Python (no order_by exists).
- Write: `table.insert(pa.Table, schema-matching)`; `table.update(pa.table({"$row_id": uint64, ...cols}), columns=[...])`; update raises `errors.MissingRowIdColumn` if `$row_id` is absent.

## Table design [must]
- Two tables in own schema `sixthsense` (never touch vss-collection / vss-prompts-events): `incidents`, `alerts`.
- `incidents` = few scalar query columns + one `payload` utf8 = `Incident.model_dump_json()`. Columns: `id` utf8 (key = sha1 of source+mode, deterministic), `mode` utf8, `risk` float64, `verified` int64 0/1 (avoid bool until proven), `updated_ms` int64 epoch ms. No nested/list/struct/timestamp types: `gap_series` lives inside payload. Why: one contract (Incident in contracts.py) so a schema change never needs DDL; list/mode filtering still server-side.
- `alerts`: `id`, `incident_id`, `created_ms`, `payload`. Insert-only, no upsert needed.
- No vector columns anywhere (vdb-vectors).

## Plan corrections
- [must] Library table, store row: "sync SDK via anyio.to_thread.run_sync" is unsafe unbounded; the Session/RPC thread-safety is undocumented -> run every store call through ONE `anyio.CapacityLimiter(1)` (or single-thread executor) so calls serialize; keeps upsert select+write consistent too.
- [must] Upsert in ONE tx per batch, not per row: select `columns=["id"], internal_row_id=True, predicate=_.mode==mode`, map id->$row_id, `update` the matches (one pa.Table), `insert` the rest (one pa.Table). Per-row tx x N incidents is slow on a shared cluster.
- [must] Type-probe in step 1 (`sixthsense probe`): create `sixthsense._probe` with exactly the chosen types, insert, read back, update, drop only that table (`table.drop()`), print ok/fail per type. Fallback is `STORE_BACKEND=json` (already planned); never start a demo run before this passes.
- [should] `/readyz`: a VastDB blip must not take the single replica out of Service. Return 200 + `{store:"degraded"}`; gate only on VSS token. Store routes return 503 with error state (UI States wireframe).
- [should] Read cache: 5 s TTL dict keyed by mode, invalidated on upsert (vdb-many-reads). Add single-flight so concurrent page loads share one select.
- [should] Lifespan failure policy: if connect/DDL fails and `STORE_BACKEND=vast`, log the error class (never endpoint/keys), switch to JsonStore and set `store_backend` in /readyz so the UI can show Sample/fallback honestly.
- [should] `ssl_verify` is a Settings field (default True, set false via env for the lab VIP, skill requires False); keys as SecretStr, `.get_secret_value()` only in store.py.

## Opportunities
- [adopt] vdb-upsert-pattern + vdb-row-id: encapsulate as `IncidentStore.upsert_many(list[Incident])` (Protocol with VastStore/JsonStore); same tests run against both via a fake in-memory VastStore built on pa.Table (no network, iso-network-block).
- [adopt] vdb-select columns: list view reads `payload` only for the mode; `/readyz` ping = `select(columns=["id"], limit_rows=1)`.
- [later] `tx.table_from_metadata` (lazy table loads, avoids eager stats per tx); `QueryConfig(data_endpoints=...)`; `sorting_key` Elysium table for time-ordered reads. 100k-DAU: reads served from Redis/cache, VastDB written only by workers; DataEngine triggers replace polling.
- [later] delete/retire: use a `status` column rather than `table.delete`.

## Anti-patterns
- `select()` with no columns; any select on vss-collection without excluding `vectors`, `vectors_visual`.
- Naming a file `select.py` (shadows stdlib, breaks vastdb). Hyphenated schema names are fine but avoid; use `sixthsense`.
- `insert` of an existing id (duplicates; no uniqueness). Using `limit_rows` as "newest N" (first found, not newest).
- Reading the reader after the tx ends (MissingTransaction). Writing through the QE VIP. Printing endpoint/keys in logs or `repr(Settings)`.
- Building predicates from strings; use ibis `_` expressions only.

## Proposed rules (each with guard)
- vastdb/pyarrow imported only in `store.py`: ruff TID251 ban + per-file-ignore (planned); bite fixture in test_conventions.
- Store tests never open a socket: autouse socket guard + `VastStore` test double via a `_Backend` seam (select/insert/update callables) injected in ctor.
- Convention test: `store.py` contains no bare `.select()` (regex requires `columns=`) and no `vss-collection` string write path.
- Contract test: `Incident.model_validate_json(row["payload"])` round-trips for every fixture (drift guard on payload).

## Outline updates
- lib vastdb: vdb-create-schema: Bucket.create_schema(name, fail_if_exists=True) and Bucket.schema(name, fail_if_missing=True) CONFIRMED (bucket.py main) -> drop the "not in fetched files" note.
- lib vastdb: vdb-connect-fn: Session.__init__ queries cluster version at construction (network at connect); kwargs: max_entities_per_page=10000, ssl_verify, timeout, backoff_config, adbc_driver_path, end_user.
- lib vastdb: vdb-backoff: BackoffConfig(wait_gen=backoff.expo, max_value=None, max_tries=10, max_time=60.0, backoff_log_level) from vastdb.config.
- lib vastdb: vdb-update: update(rows, columns=None) takes pa.Table/RecordBatch with "$row_id" uint64; raises MissingRowIdColumn; sorts ids itself; delete same.
- lib vastdb: vdb-insert: returns pa.ChunkedArray of row ids (empty input returns empty array, no call).
- usage vastdb: statuses -> adopt (vdb-connect-fn, vdb-transaction, vdb-create-schema/table, vdb-insert, vdb-upsert-pattern, vdb-row-id, vdb-update, vdb-select, vdb-predicate, vdb-limit, vdb-sort-client, vdb-many-reads), later (vdb-backoff tuning only if demo slow, vdb-query-config); paths -> backend/src/sixthsense/store.py.
