import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

from fakes import CLIP, FakeModels, FakeVSS
from sixthsense.main import Transports, create_app


class SlowModels(FakeModels):
    async def cosmos_json(self, prompt, video, model, max_tokens):
        await asyncio.sleep(0.3)
        return await super().cosmos_json(prompt, video, model, max_tokens)


def weather_ok(request: httpx.Request) -> httpx.Response:
    if "open-meteo" in request.url.host:
        return httpx.Response(200, json={"current": {"temperature_2m": 9.0, "weather_code": 61, "is_day": 1}})
    return httpx.Response(204)


@pytest.fixture
def fake_vss():
    return FakeVSS()


@pytest.fixture
def client(settings, fake_vss):
    t = Transports(vss=httpx.MockTransport(fake_vss), public=httpx.MockTransport(weather_ok))
    with TestClient(create_app(settings, t, FakeModels())) as c:
        yield c


def test_health_and_ready(client):
    assert client.get("/healthz").json() == {"ok": True, "store": None, "vss": None}
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["store"] == "json" and r.json()["vss"] is True


def test_incidents_are_sample_before_any_run(client):
    road = client.get("/api/incidents", params={"mode": "road"}).json()
    assert road and all(i["fixture"] for i in road)
    assert road[0]["risk"] >= road[-1]["risk"]
    assert client.get("/api/incidents/fixture-1").json()["id"] == "fixture-1"
    assert client.get("/api/incidents/nope").status_code == 404
    assert client.get("/api/incidents", params={"mode": "moon"}).status_code == 422
    assert client.get("/api/metrics").json() == []


def test_clip_proxy_forwards_range_and_returns_206(client):
    r = client.get("/api/clip", params={"source": "s3://b/v1_chunk_0000.mp4"}, headers={"Range": "bytes=0-99"})
    assert r.status_code == 206
    assert r.headers["content-range"] == f"bytes 0-99/{len(CLIP)}"
    assert r.content == CLIP[:100]
    assert client.get("/api/clip", params={"source": "s3://b/v1.mp4"}).content == CLIP
    assert client.get("/api/clip", params={"source": "https://evil/x"}).status_code == 400
    assert client.get("/api/clip", params={"source": "s3://b/../x"}).status_code == 400


def test_ask_proxies_and_validates(client):
    r = client.post("/api/ask", json={"question": "what happened?"})
    assert r.json() == {"answer": "about what happened?", "evidence": [{"text": "e1"}, {"k": 1}]}
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 501}).status_code == 422
    assert client.post("/api/ask", json={"question": "x", "admin": True}).status_code == 422


def test_alert_is_built_server_side_and_idempotent(client):
    r = client.post("/api/alerts", json={"incident_id": "fixture-1"})
    a = r.json()
    assert r.status_code == 200 and a["incident_id"] == "fixture-1" and a["risk"] == 4
    assert a["delivered"] is False  # no webhook configured
    assert client.post("/api/alerts", json={"incident_id": "fixture-1"}).json()["id"] == a["id"]
    assert len(client.get("/api/alerts").json()) == 1
    assert client.post("/api/alerts", json={"incident_id": "fixture-1", "risk": 5}).status_code == 422
    assert client.post("/api/alerts", json={"incident_id": "missing"}).status_code == 404


def test_weather_has_cache_header(client):
    r = client.get("/api/weather")
    assert r.json() == {"city": "London", "temp_c": 9.0, "label": "Rain", "wx": "rain", "source": "open-meteo"}
    assert r.headers["cache-control"] == "public, max-age=600"


def test_run_is_single_flight_and_stores_results(settings, fake_vss):
    t = Transports(vss=httpx.MockTransport(fake_vss))
    with TestClient(create_app(settings, t, SlowModels())) as c:
        first = c.post("/api/runs", json={"mode": "road", "limit": 2})
        assert first.status_code == 202 and first.json()["state"] == "running"
        second = c.post("/api/runs", json={"mode": "city", "limit": 1}).json()
        assert second["run_id"] == first.json()["run_id"] and second["mode"] == "road"
        for _ in range(100):
            status = c.get("/api/runs/current").json()
            if status["state"] != "running":
                break
            c.portal.call(asyncio.sleep, 0.05)
        assert status["state"] == "done", status
        assert status["steps"]["rule_out"] == {"done": 2, "total": 2, "state": "done"}
        road = c.get("/api/incidents", params={"mode": "road"}).json()
        assert road and not any(i["fixture"] for i in road)
        assert road[0]["gap_series"] and road[0]["run_id"] == first.json()["run_id"]
        m = c.get("/api/metrics").json()
        assert m[0]["mode"] == "road" and m[0]["checked"] == 2 and m[0]["accuracy"] == 1.0
        assert c.post("/api/runs", json={"mode": "road", "limit": 11}).status_code == 422


def test_runs_disabled(settings, fake_vss):
    s = settings.model_copy(update={"runs_enabled": False})
    with TestClient(create_app(s, Transports(vss=httpx.MockTransport(fake_vss)), FakeModels())) as c:
        assert c.post("/api/runs", json={"mode": "road"}).status_code == 403


def test_upstream_errors_are_502_without_echo(settings):
    async def broken(request):
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(400, text="secret upstream detail")

    with TestClient(create_app(settings, Transports(vss=httpx.MockTransport(broken)), FakeModels())) as c:
        r = c.post("/api/ask", json={"question": "q"})
        assert r.status_code == 502 and "secret" not in r.text
