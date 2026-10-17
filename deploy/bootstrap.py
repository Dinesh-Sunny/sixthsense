"""Pod bootstrap for sixthsense-v1 (stdlib only: python:3.12-slim has no curl and no uv).

    python bootstrap.py install   # initContainer: fetch dist commit, install uv, uv sync -> /srv
    python bootstrap.py serve     # app container: exec uvicorn from /srv/venv

Env: DIST_SHA (40-hex commit on the `dist` branch, required), REPO (owner/name), SRV (/srv),
PORT (8080), ROOT_PATH (optional, see below), UV_VERSION.
The commit SHA pins the content (integrity); codeload archives are not byte-stable, so no sha256.
"""

import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPO = os.environ.get("REPO", "Dinesh-Sunny/sixthsense")
SRV = Path(os.environ.get("SRV", "/srv"))
# Same uv that wrote backend/uv.lock, so `--locked` never sees a format change.
UV_VERSION = os.environ.get("UV_VERSION", "0.11.32")
APP_DIR = SRV / "app"  # unpacked dist commit: backend/ + web/out
VENV = SRV / "venv"
TOOLS = SRV / "tools"
DOWNLOAD_TIMEOUT_S = 120
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def fetch_dist(sha: str) -> None:
    url = f"https://codeload.github.com/{REPO}/tar.gz/{sha}"
    log(f"downloading {REPO}@{sha[:12]}")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "dist.tar.gz"
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as r, archive.open("wb") as f:
            shutil.copyfileobj(r, f)
        out = Path(tmp) / "x"
        with tarfile.open(archive) as tar:
            tar.extractall(out, filter="data")  # rejects absolute paths, links out of tree
        (top,) = list(out.iterdir())  # codeload wraps everything in <repo>-<sha>/
        if APP_DIR.exists():
            shutil.rmtree(APP_DIR)
        shutil.move(str(top), APP_DIR)
    log(f"unpacked to {APP_DIR}")


def install_uv() -> Path:
    uv = TOOLS / "bin" / "uv"
    if not uv.exists():
        log(f"installing uv=={UV_VERSION}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "--quiet",
             f"uv=={UV_VERSION}", "--target", str(TOOLS)],
            check=True,
        )
    return uv


def uv_env() -> dict[str, str]:
    return {
        **os.environ,
        "UV_PROJECT_ENVIRONMENT": str(VENV),
        "UV_CACHE_DIR": str(SRV / "cache"),
        "UV_LINK_MODE": "copy",
        "UV_PYTHON_DOWNLOADS": "never",  # use the image's python3.12
        "UV_PYTHON": sys.executable,
        "PYTHONPATH": str(TOOLS),
    }


def install() -> None:
    sha = os.environ.get("DIST_SHA", "")
    if not SHA_RE.match(sha):
        sys.exit("DIST_SHA must be a full 40-hex commit SHA of the dist branch")
    fetch_dist(sha)
    uv = install_uv()
    log("uv sync --locked --no-dev --no-editable")
    subprocess.run(
        [str(uv), "sync", "--locked", "--no-dev", "--no-editable"],
        cwd=APP_DIR / "backend",
        env=uv_env(),
        check=True,
    )
    shutil.rmtree(SRV / "cache", ignore_errors=True)
    (SRV / "data").mkdir(exist_ok=True)
    log("install done")


def serve() -> None:
    port = os.environ.get("PORT", "8080")
    args = [
        str(VENV / "bin" / "uvicorn"),
        "--factory", "sixthsense.main:create_app",
        "--host", "0.0.0.0",
        "--port", port,
        "--proxy-headers",
        "--forwarded-allow-ips", "*",
    ]
    # The Ingress rewrite strips /app (or /v1) before requests reach us, so routes need no prefix.
    # ROOT_PATH only changes generated URLs (OpenAPI docs); leave it unset unless that is wanted.
    if root := os.environ.get("ROOT_PATH"):
        args += ["--root-path", root]
    env = {
        **os.environ,
        "WEB_DIR": os.environ.get("WEB_DIR", str(APP_DIR / "web" / "out")),
        "DATA_DIR": os.environ.get("DATA_DIR", str(SRV / "data")),
    }
    log(f"starting uvicorn on :{port}")
    os.chdir(SRV)
    os.execve(args[0], args, env)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "install":
        install()
    elif cmd == "serve":
        serve()
    else:
        sys.exit("usage: bootstrap.py install|serve")
