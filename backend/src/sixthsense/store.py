"""Incident store: VastDB (system of record) or a JSON file (fallback). The one vastdb/pyarrow importer.

Semantics (decisions d7): incidents carry run_id; list and metrics show only the latest finished
run per mode. A mode with no runs shows Sample fixtures, which never feed metrics.
"""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, TypeVar

import anyio
import anyio.to_thread
from pydantic import TypeAdapter

from .contracts import Alert, Incident, ModeMetrics
from .modes import ALERTS_MAX
from .settings import Settings

log = logging.getLogger("sixthsense.store")
T = TypeAdapter(list[Incident])
R = TypeVar("R")
READ_CACHE_S = 5.0
SEED_FILE = Path(__file__).with_name("seed_incidents.json")


def _risk_sort(items: list[Incident]) -> list[Incident]:
    return sorted(items, key=lambda i: (-i.risk, i.start_s))


def load_seed(path: Path | None) -> list[Incident]:
    p = path or SEED_FILE
    try:
        rows = T.validate_json(p.read_bytes())
    except (OSError, ValueError):
        return []
    return [i.model_copy(update={"fixture": True}) for i in rows]


class IncidentStore(Protocol):
    backend: str

    async def ping(self) -> None: ...
    async def list_incidents(self, mode: str | None) -> list[Incident]: ...
    async def get_incident(self, incident_id: str) -> Incident | None: ...
    async def save_run(self, metrics: ModeMetrics, incidents: list[Incident]) -> None: ...
    async def metrics(self) -> list[ModeMetrics]: ...
    async def add_alert(self, alert: Alert) -> None: ...
    async def alerts(self) -> list[Alert]: ...
    async def close(self) -> None: ...


class _Base:
    """Shared logic: latest run per mode, Sample fallback, serialized sync calls."""

    backend = "base"

    def __init__(self, seed: list[Incident]) -> None:
        self._seed = seed
        # The vastdb Session is not documented as thread-safe: every call goes through ONE thread slot.
        self._limiter = anyio.CapacityLimiter(1)

    async def _sync(self, fn: Callable[[], R]) -> R:
        return await anyio.to_thread.run_sync(fn, limiter=self._limiter)

    # --- primitives each backend implements (sync, called under the limiter) ---
    def _runs(self) -> list[ModeMetrics]:
        raise NotImplementedError

    def _incidents_for_runs(self, run_ids: set[str]) -> list[Incident]:
        raise NotImplementedError

    def _find_incident(self, incident_id: str) -> Incident | None:
        raise NotImplementedError

    # --- shared ---
    def _latest_runs(self) -> dict[str, ModeMetrics]:
        latest: dict[str, ModeMetrics] = {}
        for m in self._runs():
            if m.mode not in latest or m.generated_at > latest[m.mode].generated_at:
                latest[m.mode] = m
        return latest

    def _list_sync(self, mode: str | None) -> list[Incident]:
        latest = self._latest_runs()
        run_ids = {m.run_id for m in latest.values() if m.run_id}
        live = self._incidents_for_runs(run_ids) if run_ids else []
        out = [i for i in live if mode is None or i.mode == mode]
        # Sample rows only for modes that have never had a run.
        out += [s for s in self._seed if s.mode not in latest and (mode is None or s.mode == mode)]
        return _risk_sort(out)

    async def list_incidents(self, mode: str | None) -> list[Incident]:
        return await self._sync(lambda: self._list_sync(mode))

    async def get_incident(self, incident_id: str) -> Incident | None:
        found = await self._sync(lambda: self._find_incident(incident_id))
        return found or next((s for s in self._seed if s.id == incident_id), None)

    async def metrics(self) -> list[ModeMetrics]:
        latest = await self._sync(self._latest_runs)
        return sorted(latest.values(), key=lambda m: m.mode)

    async def close(self) -> None:
        return None


class JsonStore(_Base):
    """One JSON file. Fine for one replica; the emptyDir is lost on restart (Sample comes back)."""

    backend = "json"

    def __init__(self, path: Path, seed: list[Incident]) -> None:
        super().__init__(seed)
        self.path = path

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError):
            data = {}
        return {"incidents": {}, "runs": [], "alerts": [], **data}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1))
        tmp.replace(self.path)

    def _runs(self) -> list[ModeMetrics]:
        return [ModeMetrics.model_validate(r) for r in self._read()["runs"]]

    def _incidents_for_runs(self, run_ids: set[str]) -> list[Incident]:
        rows = self._read()["incidents"].values()
        return [Incident.model_validate(r) for r in rows if r.get("run_id") in run_ids]

    def _find_incident(self, incident_id: str) -> Incident | None:
        row = self._read()["incidents"].get(incident_id)
        return Incident.model_validate(row) if row else None

    async def ping(self) -> None:
        await self._sync(self._read)

    async def save_run(self, metrics: ModeMetrics, incidents: list[Incident]) -> None:
        def do() -> None:
            data = self._read()
            for i in incidents:  # upsert by deterministic id
                data["incidents"][i.id] = i.model_dump(mode="json")
            data["runs"].append(metrics.model_dump(mode="json"))
            self._write(data)

        await self._sync(do)

    async def add_alert(self, alert: Alert) -> None:
        def do() -> None:
            data = self._read()
            data["alerts"] = [alert.model_dump(mode="json"), *data["alerts"]][:ALERTS_MAX]
            self._write(data)

        await self._sync(do)

    async def alerts(self) -> list[Alert]:
        data = await self._sync(self._read)
        return [Alert.model_validate(a) for a in data["alerts"]]


class VastStore(_Base):
    """VastDB tables in schema `sixthsense`: incidents (upsert), runs and alerts (insert-only).

    Scalar query columns + one `payload` utf8 holding the contract model, so contract changes
    never need DDL. VastDB 2.1 has no upsert/order_by: select $row_id then update/insert in one tx.
    """

    backend = "vast"

    def __init__(self, settings: Settings, seed: list[Incident]) -> None:
        super().__init__(seed)
        self.settings = settings
        self._session: Any = None
        self._cache: dict[str, tuple[float, Any]] = {}

    # pyarrow/vastdb are imported lazily: JSON-only runs and tests never load them.
    @staticmethod
    def _schemas() -> dict[str, Any]:
        import pyarrow as pa

        return {
            "incidents": pa.schema(
                [
                    ("id", pa.utf8()),
                    ("mode", pa.utf8()),
                    ("run_id", pa.utf8()),
                    ("risk", pa.float64()),
                    ("verified", pa.int64()),
                    ("came_true", pa.utf8()),
                    ("updated_ms", pa.int64()),
                    ("payload", pa.utf8()),
                ]
            ),
            "runs": pa.schema(
                [
                    ("run_id", pa.utf8()),
                    ("mode", pa.utf8()),
                    ("finished_ms", pa.int64()),
                    ("candidates", pa.int64()),
                    ("verified", pa.int64()),
                    ("checked", pa.int64()),
                    ("yes", pa.int64()),
                    ("partly", pa.int64()),
                    ("eval_url", pa.utf8()),
                    ("payload", pa.utf8()),
                ]
            ),
            "alerts": pa.schema(
                [
                    ("id", pa.utf8()),
                    ("incident_id", pa.utf8()),
                    ("created_ms", pa.int64()),
                    ("payload", pa.utf8()),
                ]
            ),
        }

    def _connect_sync(self) -> None:
        import vastdb
        from vastdb.config import BackoffConfig

        s = self.settings
        self._session = vastdb.connect(
            endpoint=s.s3_endpoint,
            access=s.access_key.get_secret_value(),
            secret=s.secret_key.get_secret_value(),
            ssl_verify=s.vast_ssl_verify,
            backoff_config=BackoffConfig(max_tries=3, max_time=15),
        )
        with self._session.transaction() as tx:
            bucket = tx.bucket(s.vastdb_bucket)
            schema = bucket.create_schema(s.vast_schema, fail_if_exists=False)
            for name, cols in self._schemas().items():
                schema.create_table(name, columns=cols, fail_if_exists=False)

    async def connect(self) -> None:
        await self._sync(self._connect_sync)

    def _table(self, tx: Any, name: str) -> Any:
        return tx.bucket(self.settings.vastdb_bucket).schema(self.settings.vast_schema).table(name)

    def _select(self, name: str, columns: list[str], predicate: Any = None) -> list[dict[str, Any]]:
        with self._session.transaction() as tx:
            reader = self._table(tx, name).select(columns=columns, predicate=predicate)
            return reader.read_all().to_pylist()  # materialise inside the tx

    def _cached(self, key: str, fn: Callable[[], R]) -> R:
        hit = self._cache.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        value = fn()
        self._cache[key] = (time.monotonic() + READ_CACHE_S, value)
        return value

    def _runs(self) -> list[ModeMetrics]:
        rows = self._cached("runs", lambda: self._select("runs", ["payload"]))
        return [ModeMetrics.model_validate_json(r["payload"]) for r in rows]

    def _incidents_for_runs(self, run_ids: set[str]) -> list[Incident]:
        from ibis import _

        key = "inc:" + ",".join(sorted(run_ids))
        rows = self._cached(
            key, lambda: self._select("incidents", ["payload"], _.run_id.isin(sorted(run_ids)))
        )
        return [Incident.model_validate_json(r["payload"]) for r in rows]

    def _find_incident(self, incident_id: str) -> Incident | None:
        from ibis import _

        rows = self._select("incidents", ["payload"], _.id == incident_id)
        return Incident.model_validate_json(rows[0]["payload"]) if rows else None

    async def ping(self) -> None:
        def do() -> None:
            with self._session.transaction() as tx:
                self._table(tx, "runs").select(columns=["run_id"], limit_rows=1).read_all()

        await self._sync(do)

    async def save_run(self, metrics: ModeMetrics, incidents: list[Incident]) -> None:
        import pyarrow as pa
        from ibis import _

        schemas = self._schemas()
        now = int(time.time() * 1000)

        def inc_row(i: Incident) -> dict[str, Any]:
            return {
                "id": i.id,
                "mode": i.mode,
                "run_id": i.run_id or "",
                "risk": float(i.risk),
                "verified": int(i.verified),
                "came_true": i.came_true,
                "updated_ms": now,
                "payload": i.model_dump_json(),
            }

        def do() -> None:
            with self._session.transaction() as tx:
                table = self._table(tx, "incidents")
                if incidents:
                    existing = (
                        table.select(
                            columns=["id"], predicate=_.mode == metrics.mode, internal_row_id=True
                        )
                        .read_all()
                        .to_pylist()
                    )
                    row_ids = {r["id"]: r["$row_id"] for r in existing}
                    updates = [i for i in incidents if i.id in row_ids]
                    inserts = [i for i in incidents if i.id not in row_ids]
                    if updates:
                        cols = [f.name for f in schemas["incidents"] if f.name != "id"]
                        data = {c: [inc_row(i)[c] for i in updates] for c in cols}
                        upd = pa.table(
                            {"$row_id": pa.array([row_ids[i.id] for i in updates], pa.uint64()), **data}
                        )
                        table.update(upd, columns=cols)
                    if inserts:
                        table.insert(pa.Table.from_pylist([inc_row(i) for i in inserts], schemas["incidents"]))
                run_row = {
                    "run_id": metrics.run_id or "",
                    "mode": metrics.mode,
                    "finished_ms": now,
                    "candidates": metrics.candidates,
                    "verified": metrics.verified,
                    "checked": metrics.checked,
                    "yes": metrics.came_true_yes,
                    "partly": metrics.came_true_partly,
                    "eval_url": metrics.eval_url or "",
                    "payload": metrics.model_dump_json(),
                }
                self._table(tx, "runs").insert(pa.Table.from_pylist([run_row], schemas["runs"]))
            self._cache.clear()

        await self._sync(do)

    async def add_alert(self, alert: Alert) -> None:
        import pyarrow as pa

        row = {
            "id": alert.id,
            "incident_id": alert.incident_id,
            "created_ms": int(time.time() * 1000),
            "payload": alert.model_dump_json(),
        }

        def do() -> None:
            with self._session.transaction() as tx:
                self._table(tx, "alerts").insert(pa.Table.from_pylist([row], self._schemas()["alerts"]))
            self._cache.pop("alerts", None)

        await self._sync(do)

    async def alerts(self) -> list[Alert]:
        def do() -> list[Alert]:
            rows = self._cached("alerts", lambda: self._select("alerts", ["payload"]))
            items = [Alert.model_validate_json(r["payload"]) for r in rows]
            return sorted(items, key=lambda a: a.sent_at, reverse=True)[:ALERTS_MAX]

        return await self._sync(do)

    def probe_types_sync(self) -> dict[str, bool]:
        """`sixthsense probe`: create _probe with the chosen types, insert/read/update, drop it."""
        import pyarrow as pa

        results: dict[str, bool] = {}
        cols = self._schemas()["incidents"]
        name = "_probe"
        with self._session.transaction() as tx:
            schema = tx.bucket(self.settings.vastdb_bucket).schema(self.settings.vast_schema)
            table = schema.create_table(name, columns=cols, fail_if_exists=False)
            row = {
                "id": "p1",
                "mode": "road",
                "run_id": "r",
                "risk": 1.0,
                "verified": 1,
                "came_true": "yes",
                "updated_ms": 1,
                "payload": "{}",
            }
            table.insert(pa.Table.from_pylist([row], cols))
            results["insert"] = True
            got = table.select(columns=["id"], internal_row_id=True).read_all().to_pylist()
            results["select"] = bool(got)
            upd = pa.table({"$row_id": pa.array([got[0]["$row_id"]], pa.uint64()), "risk": [2.0]})
            table.update(upd, columns=["risk"])
            results["update"] = True
            table.drop()
            results["drop"] = True
        return results


async def open_store(settings: Settings) -> IncidentStore:
    """VastDB when configured and reachable; otherwise JSON (logs the error class only)."""
    seed = load_seed(settings.seed_file)
    json_store = JsonStore(settings.data_dir / "store.json", seed)
    if settings.store_backend != "vast":
        return json_store
    if not (settings.s3_endpoint and settings.vastdb_bucket):
        log.warning("store: VastDB not configured, using JSON")
        return json_store
    vast = VastStore(settings, seed)
    try:
        with anyio.fail_after(30):
            await vast.connect()
    except Exception as e:  # noqa: BLE001 - fall back, never log endpoint or keys
        log.warning("store: VastDB unavailable (%s), using JSON", type(e).__name__)
        return json_store
    return vast
