"""The one place weave is imported. Tracing is on only when WANDB_API_KEY is set.

Without a client, weave ops are plain function calls, so tests and offline runs need no network.
"""

import asyncio
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import weave
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from .settings import Settings

log = logging.getLogger("sixthsense.tracing")

op = weave.op
_enabled = False


def _scrub(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, str) and value.startswith("data:"):
        return f"<media {len(value)} chars>"
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_scrub(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseModel) and not isinstance(value, BaseSettings):
        return _scrub(value.model_dump(mode="json"))
    # Objects (e.g. `self` of a client holding Settings) are logged by type name only.
    return f"<{type(value).__name__}>"


def drop_media(inputs: dict[str, Any]) -> dict[str, Any]:
    """Client-level postprocess_inputs: base64 video and raw bytes never reach a trace.

    Runs for every op, including the autopatched openai spans (op-level hooks alone miss those).
    """
    return {k: _scrub(v) for k, v in inputs.items()}


def _init_sync(settings: Settings) -> None:
    # weave reads the key from the environment or netrc only (no constructor arg).
    os.environ.setdefault("WANDB_API_KEY", settings.wandb_api_key.get_secret_value())
    weave.init(
        settings.wandb_project_path or settings.wandb_project,
        postprocess_inputs=drop_media,
        settings={"print_call_link": False},
        attributes={"app": "sixthsense"},
    )


async def init_tracing(settings: Settings) -> bool:
    """Start Weave if a key is set. Never raises: a tracing failure must not stop the app."""
    global _enabled
    if not settings.wandb_api_key.get_secret_value():
        return False
    try:
        # Without a key weave.init calls an interactive login; with one it still does network I/O.
        await asyncio.to_thread(_init_sync, settings)
    except Exception as e:  # noqa: BLE001 - run untraced on any init failure
        log.warning("weave init failed (%s); running untraced", type(e).__name__)
        return False
    _enabled = True
    return True


async def finish_tracing() -> None:
    if _enabled:
        await asyncio.to_thread(weave.finish)


def enabled() -> bool:
    return _enabled


@contextmanager
def run_context(mode: str, run_id: str) -> Iterator[None]:
    """Tag every op in a run, and group them as one thread in the Weave UI."""
    if not _enabled:
        yield
        return
    with weave.attributes({"mode": mode, "run_id": run_id}), weave.thread(run_id):
        yield


def current_call_url() -> str | None:
    """Deep link to the op that is running now, for 'See how it decided'."""
    if not _enabled:
        return None
    try:
        call = weave.get_current_call()
        return call.ui_url if call else None
    except Exception:  # noqa: BLE001 - a missing link is fine
        return None
