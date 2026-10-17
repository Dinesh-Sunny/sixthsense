"""In-pod run jobs: single-flight, cooldown, status for polling. (arq on Redis is the 100k-DAU path.)"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta

from .contracts import RunStatus, RunSteps
from .modes import Mode
from .pipeline import Deps, execute_run
from .settings import Settings
from .store import IncidentStore

log = logging.getLogger("sixthsense.runner")


def _now() -> datetime:
    return datetime.now().astimezone()


class RunsDisabled(Exception):
    pass


class RunManager:
    def __init__(self, settings: Settings, deps: Deps, store: IncidentStore) -> None:
        self.settings = settings
        self.deps = deps
        self.store = store
        self.status = RunStatus(runs_enabled=settings.runs_enabled)
        self._task: asyncio.Task[None] | None = None  # strong ref: the loop only keeps weak ones
        self._cooldown_until: datetime | None = None

    @property
    def active(self) -> bool:
        return self._task is not None and not self._task.done()

    def current(self) -> RunStatus:
        return self.status

    def start(self, mode: Mode, limit: int) -> tuple[RunStatus, bool]:
        """Returns (status, started). A second POST while running returns the active run."""
        if self.active:  # no await between check and set: single-flight on one event loop
            return self.status, False
        if not self.settings.runs_enabled:
            raise RunsDisabled
        if self._cooldown_until and _now() < self._cooldown_until:
            return self.status, False
        run_id = f"{mode}-{_now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.status = RunStatus(
            run_id=run_id,
            mode=mode,
            limit=limit,
            state="running",
            started_at=_now().isoformat(timespec="seconds"),
            runs_enabled=True,
        )
        self._task = asyncio.create_task(self._run(mode, limit, run_id), name=f"run-{run_id}")
        self._task.add_done_callback(self._done)
        return self.status, True

    def _progress(self, steps: RunSteps) -> None:
        self.status = self.status.model_copy(update={"steps": steps})

    async def _run(self, mode: Mode, limit: int, run_id: str) -> None:
        await execute_run(self.deps, self.store, mode, limit, run_id, self._progress)

    def _done(self, task: asyncio.Task[None]) -> None:
        finished = _now()
        self._cooldown_until = finished + timedelta(seconds=self.settings.run_cooldown_s)
        update: dict[str, object] = {
            "finished_at": finished.isoformat(timespec="seconds"),
            "cooldown_until": self._cooldown_until.isoformat(timespec="seconds"),
        }
        if task.cancelled():
            update |= {"state": "error", "error": "Cancelled"}
        elif (exc := task.exception()) is not None:
            log.error("run failed (%s)", type(exc).__name__)
            update |= {"state": "error", "error": type(exc).__name__}
        else:
            update["state"] = "done"
        self.status = self.status.model_copy(update=update)

    async def shutdown(self) -> None:
        if self.active and self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
