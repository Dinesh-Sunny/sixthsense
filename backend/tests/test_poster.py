import os
import tempfile

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from fakes import FakeModels, FakeVSS
from sixthsense.main import Transports, create_app
from sixthsense.media import PosterCache, poster_jpeg


def tiny_mp4(seconds: int = 3, fps: int = 10, size=(320, 180)) -> bytes:
    """Frames get brighter each second, so the decoded still shows which second we seeked to."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for i in range(seconds * fps):
        w.write(np.full((size[1], size[0], 3), 40 + 80 * (i // fps), np.uint8))
    w.release()
    with open(path, "rb") as f:
        data = f.read()
    os.unlink(path)
    return data


VIDEO = tiny_mp4()


def decode(jpeg: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)


def test_poster_seeks_and_resizes_to_960():
    early, later = decode(poster_jpeg(VIDEO, 0.2)), decode(poster_jpeg(VIDEO, 2.2))
    assert early.shape == (540, 960, 3)
    assert later.mean() > early.mean() + 60  # second 2 is brighter than second 0
    assert decode(poster_jpeg(VIDEO, 99)).shape == (540, 960, 3)  # past the end -> first frame


def test_unreadable_clip_is_none():
    assert poster_jpeg(b"not a video", 1) is None
    assert poster_jpeg(b"", 1) is None


async def test_lru_evicts_oldest():
    c = PosterCache(max_items=2)
    c.put(("a", 1.0), b"A")
    c.put(("b", 1.0), b"B")
    assert c.get(("a", 1.0)) == b"A"  # a is now most recent
    c.put(("c", 1.0), b"C")
    assert c.get(("b", 1.0)) is None and c.get(("a", 1.0)) == b"A"


class VideoVSS(FakeVSS):
    def __init__(self):
        super().__init__()
        self.streams = 0

    async def __call__(self, request):
        if request.url.path.endswith("/videos/stream") and request.headers.get("authorization"):
            src = request.url.params["source"]
            self.streams += 1
            if src.endswith("missing.mp4"):
                return httpx.Response(404)
            if src.endswith("real.mp4"):
                return httpx.Response(200, headers={"content-type": "video/mp4"}, content=VIDEO)
        return await super().__call__(request)


@pytest.fixture
def vss():
    return VideoVSS()


@pytest.fixture
def client(settings, vss):
    with TestClient(create_app(settings, Transports(vss=httpx.MockTransport(vss)), FakeModels())) as c:
        yield c


def test_poster_endpoint_jpeg_cached_and_validated(client, vss):
    r = client.get("/api/poster", params={"source": "s3://b/real.mp4"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"] == "public, max-age=86400"
    assert decode(r.content).shape[1] == 960
    n = vss.streams
    assert client.get("/api/poster", params={"source": "s3://b/real.mp4", "t": 1.04}).content == r.content
    assert vss.streams == n  # same (source, t to 0.1 s): served from the LRU
    assert client.get("/api/poster", params={"source": "s3://b/real.mp4", "t": 2}).content != r.content


def test_poster_errors(client):
    assert client.get("/api/poster", params={"source": "s3://b/missing.mp4"}).status_code == 404
    assert client.get("/api/poster", params={"source": "s3://b/v1_chunk_0000.mp4"}).status_code == 404  # junk
    assert client.get("/api/poster", params={"source": "https://evil/x.mp4"}).status_code == 400
    assert client.get("/api/poster", params={"source": "s3://b/../x.mp4"}).status_code == 400
    assert client.get("/api/poster", params={"source": "s3://b/real.mp4", "t": -1}).status_code == 422
