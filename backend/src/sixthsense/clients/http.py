"""The one place httpx clients are built: VSS (auth + lab TLS), GPU, public internet.

Also owns the retry policy and VSSAuth (token login + one re-login on 401).
"""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator, Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from sixthsense.settings import Settings

log = logging.getLogger("sixthsense.http")

# Annotation-only alias for other modules: constructing clients stays in this file.
HttpClient = httpx.AsyncClient

LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
VSS_TIMEOUT = httpx.Timeout(10.0, read=120.0)
GPU_TIMEOUT = httpx.Timeout(10.0, read=120.0)
PUBLIC_TIMEOUT = httpx.Timeout(3.0)
STREAM_PATH_SUFFIX = "/videos/stream"


def is_transient(exc: BaseException) -> bool:
    """Retry transport errors, 429 and 5xx only. 4xx are our bug or a real 'no'."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def retrying(attempts: int = 4, max_wait: float = 8.0) -> AsyncRetrying:
    return AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=0.5, max=max_wait),
        retry=retry_if_exception(is_transient),
        reraise=True,
        before_sleep=before_sleep_log(log, logging.WARNING),
    )


async def with_retry[T](fn: Callable[[], Awaitable[T]], policy: AsyncRetrying | None = None) -> T:
    """Run an idempotent call under the retry policy."""
    async for attempt in policy or retrying():
        with attempt:
            return await fn()
    raise AssertionError("unreachable: reraise=True")  # pragma: no cover


async def _log_request(request: httpx.Request) -> None:
    request.extensions["t0"] = time.perf_counter()


async def _log_response(response: httpx.Response) -> None:
    # Method, host, path and status only: never headers, query strings or bodies (tokens live there).
    t0 = response.request.extensions.get("t0", time.perf_counter())
    ms = (time.perf_counter() - t0) * 1000
    req = response.request
    log.info("%s %s%s -> %s (%.0f ms)", req.method, req.url.host, req.url.path, response.status_code, ms)


EVENT_HOOKS = {"request": [_log_request], "response": [_log_response]}


class VSSAuth(httpx.Auth):
    """Bearer token from POST /auth/login; re-login once on 401.

    Overrides async_auth_flow instead of setting requires_response_body, which would make
    httpx buffer every response body (the clip proxy streams whole videos).
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        self._login_url = base_url.rstrip("/") + "/auth/login"
        self._username = username
        self._password = password
        self._token: str | None = None
        self._lock = asyncio.Lock()

    @property
    def has_token(self) -> bool:
        return self._token is not None

    @property
    def token(self) -> str | None:
        return self._token

    def _login_request(self) -> httpx.Request:
        return httpx.Request(
            "POST", self._login_url, json={"username": self._username, "password": self._password}
        )

    async def _store_token(self, response: httpx.Response) -> None:
        await response.aread()
        response.raise_for_status()
        self._token = str(response.json()["access_token"])

    def _apply(self, request: httpx.Request) -> None:
        request.headers["Authorization"] = f"Bearer {self._token}"
        if request.url.path.endswith(STREAM_PATH_SUFFIX):
            # <video> playback endpoint takes the token as a query param.
            request.url = request.url.copy_merge_params({"token": self._token or ""})

    def sync_auth_flow(self, request: httpx.Request):  # pragma: no cover - async only
        raise RuntimeError("VSSAuth is async-only")

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        async with self._lock:
            if self._token is None:
                await self._store_token((yield self._login_request()))
        self._apply(request)
        response = yield request
        if response.status_code == 401:
            await response.aclose()
            self._token = None
            await self._store_token((yield self._login_request()))
            self._apply(request)
            yield request


def vss_client(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    base = settings.vss_url.rstrip("/") + "/api/v1"
    auth = VSSAuth(base, settings.vss_username, settings.vss_password.get_secret_value())
    return httpx.AsyncClient(
        base_url=base,
        auth=auth,
        timeout=VSS_TIMEOUT,
        limits=LIMITS,
        verify=settings.vss_verify_tls,
        event_hooks=EVENT_HOOKS,
        transport=transport,
    )


def gpu_client(settings: Settings, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """YOLO endpoint (plain JSON POST); Cosmos goes through the openai SDK instead."""
    token = settings.gpu_token.get_secret_value()
    return httpx.AsyncClient(
        base_url=settings.resolved_yolo_url,
        headers={"Authorization": f"Bearer {token}"} if token else None,
        timeout=GPU_TIMEOUT,
        limits=LIMITS,
        verify=settings.vss_verify_tls,
        event_hooks=EVENT_HOOKS,
        transport=transport,
    )


def public_client(transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """Open-Meteo and Discord: real CAs, short timeouts."""
    return httpx.AsyncClient(
        timeout=PUBLIC_TIMEOUT, limits=LIMITS, event_hooks=EVENT_HOOKS, transport=transport
    )
