import httpx
import pytest

from fakes import FakeVSS
from sixthsense.clients.http import is_transient, retrying, vss_client, with_retry
from sixthsense.clients.models import extract_json, parse_reply
from sixthsense.clients.vss import DetectionsResp, SearchResp, SegmentsResp, VSSClient
from sixthsense.pipeline import Forecast
from sixthsense.tracing import drop_media


async def test_vss_auth_logs_in_then_relogs_once_on_401(settings):
    fake = FakeVSS()
    async with vss_client(settings, httpx.MockTransport(fake)) as http:
        v = VSSClient(http)
        assert not v.has_token
        await v.search("q", "cam", 5, 0.1)
        assert fake.logins == 1 and v.has_token
        fake.expire_token = True
        res = await v.search("q", "cam", 5, 0.1)
        assert fake.logins == 2 and len(res.results) == 2


async def test_detections_404_is_none(settings):
    async def h(request):
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(404)

    async with vss_client(settings, httpx.MockTransport(h)) as http:
        assert await VSSClient(http).detections("s3://b/x.mp4") is None


@pytest.mark.parametrize(
    ("status", "transient"), [(429, True), (500, True), (503, True), (400, False), (401, False), (404, False)]
)
def test_retry_only_429_and_5xx(status, transient):
    req = httpx.Request("GET", "https://x")
    exc = httpx.HTTPStatusError("e", request=req, response=httpx.Response(status, request=req))
    assert is_transient(exc) is transient
    assert is_transient(httpx.ConnectError("x", request=req))
    assert not is_transient(ValueError())


async def test_with_retry_retries_then_succeeds():
    calls = {"n": 0}
    req = httpx.Request("GET", "https://x")

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.HTTPStatusError("e", request=req, response=httpx.Response(503, request=req))
        return "ok"

    policy = retrying(attempts=4, max_wait=0.01)
    assert await with_retry(flaky, policy) == "ok" and calls["n"] == 3

    calls["n"] = 0

    async def bad():
        calls["n"] += 1
        raise httpx.HTTPStatusError("e", request=req, response=httpx.Response(400, request=req))

    with pytest.raises(httpx.HTTPStatusError):
        await with_retry(bad, retrying(attempts=4, max_wait=0.01))
    assert calls["n"] == 1


def test_vss_models_parse_probe_shapes():
    s = SearchResp.model_validate(
        {"results": [{"source": "s3://b/a.mp4", "segment_start_sec": 5, "segment_end_sec": None,
                      "reasoning_content": "desc", "similarity_score": 0.21, "extra": 1}]}
    )
    h = s.results[0]
    assert (h.start_s, h.end, h.description, h.similarity) == (5.0, 10.0, "desc", 0.21)
    segs = SegmentsResp.model_validate([{"source": "b", "segment_number": 2}, {"source": "a", "segment_number": 1}])
    assert [x.source for x in segs.ordered()] == ["a", "b"]
    d = DetectionsResp.model_validate({"perception_json": {"frames": [{"frame_index": 0, "detections": []}]}})
    assert len(d.frames) == 1


def test_extract_json_strips_think_and_fences():
    text = '<think>{"no": 1}</think>```json\n{"type": "cut-in", "risk": "9"}\n```'
    assert extract_json(text) == '{"type": "cut-in", "risk": "9"}'
    f = parse_reply(text, Forecast)
    assert f is not None and f.type == "cut-in" and f.risk == 5
    assert parse_reply("no json here", Forecast) == Forecast()


def test_drop_media_removes_video_and_bytes():
    inputs = {
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "hi"},
            {"type": "video_url", "video_url": {"url": "data:video/mp4;base64," + "A" * 5000}},
        ]}],
        "video": b"\x00" * 100,
        "self": object(),
    }
    out = drop_media(inputs)
    flat = repr(out)
    assert "AAAA" not in flat and "\\x00" not in flat
    assert out["video"] == "<100 bytes>"
    assert out["messages"][0]["content"][0]["text"] == "hi"
    assert out["self"] == "<object>"
