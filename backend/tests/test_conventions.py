"""Guards from the plan's enforcement table, each proven to bite."""

import subprocess
import sys
from pathlib import Path

import pytest

from sixthsense import pipeline
from sixthsense.clients.http import VSSAuth
from sixthsense.main import create_app
from sixthsense.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_settings_ignore_stray_env_and_hide_secrets(settings):
    assert Settings.model_config["extra"] == "ignore"
    text = repr(settings) + str(settings)
    for secret in ("hunter2-secret", "gpu-secret-token"):
        assert secret not in text
    # the lab VM names work too
    s = Settings(_env_file=None, INGRESS_URL="https://x", USERNAME="u", PASSWORD="p", stray_key=1)
    assert (s.vss_url, s.vss_username, s.vss_password.get_secret_value()) == ("https://x", "u", "p")


def test_lockfile_has_only_headless_opencv():
    lock = (ROOT / "uv.lock").read_text()
    assert 'name = "opencv-python-headless"' in lock
    assert 'name = "opencv-python"\n' not in lock


def test_vss_auth_does_not_buffer_bodies():
    # requires_response_body=True would make httpx read whole video streams into RAM.
    assert VSSAuth.requires_response_body is False


def test_every_api_route_declares_a_response_model(settings, tmp_path):
    exempt = {"/api/clip", "/readyz"}
    (tmp_path / "web").mkdir()
    app = create_app(settings.model_copy(update={"web_dir": tmp_path / "web"}))
    paths = app.openapi()["paths"]
    assert "/api/incidents" in paths
    for path, ops in paths.items():
        for method, spec in ops.items():
            if path in exempt:
                continue
            ok = next(v for k, v in spec["responses"].items() if k.startswith("2"))
            assert "schema" in ok.get("content", {}).get("application/json", {}), (method, path)
    # static export is mounted last, so it can never shadow /api or health
    assert type(app.routes[-1]).__name__ == "Mount"


def test_pipeline_steps_are_ops():
    for fn in (pipeline.watch, pipeline.verify, pipeline.foresee, pipeline.selfcheck, pipeline.run_mode):
        assert hasattr(fn, "resolve_fn") and fn.kind, fn


def _ruff(path: str, code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--select", "TID251", "--stdin-filename", path, "-"],
        input=code,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("src/sixthsense/pipeline.py", "import vastdb\n"),
        ("src/sixthsense/pipeline.py", "import httpx\nc = httpx.AsyncClient()\n"),
        ("src/sixthsense/main.py", "from openai import AsyncOpenAI\n"),
        ("src/sixthsense/main.py", "import weave\n"),
        ("src/sixthsense/pipeline.py", "import supervision as sv\n"),
        ("src/sixthsense/pipeline.py", "import cv2\n"),
        ("src/sixthsense/main.py", "import os\nx = os.environ['X']\n"),
        ("src/sixthsense/main.py", "import urllib.request\n"),
    ],
)
def test_banned_imports_bite(path, code):
    r = _ruff(path, code)
    assert r.returncode != 0 and "TID251" in r.stdout, r.stdout + r.stderr


@pytest.mark.parametrize(
    ("path", "code"),
    [
        ("src/sixthsense/store.py", "import vastdb\n"),
        ("src/sixthsense/clients/models.py", "from openai import AsyncOpenAI\n"),
        ("src/sixthsense/tracking.py", "import supervision as sv\n"),
        ("src/sixthsense/settings.py", "import os\nx = os.environ\n"),
    ],
)
def test_sanctioned_importers_pass(path, code):
    assert _ruff(path, code).returncode == 0
