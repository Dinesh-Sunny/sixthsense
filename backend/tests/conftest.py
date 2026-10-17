import socket
from pathlib import Path

import pytest

from sixthsense.settings import Settings


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any real network connection fails the test (MockTransport never opens a socket)."""

    def guard(self, address, *args, **kwargs):
        if self.family == socket.AF_UNIX:
            return original(self, address, *args, **kwargs)
        raise RuntimeError(f"network access in tests: {address!r}")

    original = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket.socket, "connect_ex", guard)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        vss_url="https://vss.test",
        vss_username="team-test",
        vss_password="hunter2-secret",
        gpu_token="gpu-secret-token",
        store_backend="json",
        data_dir=tmp_path,
        web_dir=tmp_path / "no-web",
        run_cooldown_s=0,
        cosmos_model="cosmos-test",
        fleet_enabled=False,
    )
