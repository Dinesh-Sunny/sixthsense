import json

import httpx
from fastapi.testclient import TestClient
from pydantic import SecretStr

from fakes import FakeModels, FakeVSS
from sixthsense.clients.http import TFL_USER_AGENT, tfl_client
from sixthsense.contracts import Incident, ModeMetrics
from sixthsense.main import Transports, create_app, create_asgi
from sixthsense.store import JsonStore
from sixthsense.tfl import Fleet, bearing_deg, vehicles_from_arrivals

STOPS = {
    "490A": (-0.10, 51.50, "Stop A"),
    "490B": (-0.10, 51.51, "Stop B"),  # due north of A
    "490C": (-0.09, 51.50, "Stop C"),
}


def pred(vid, stop, t, line="18", direction="outbound"):
    return {"vehicleId": vid, "naptanId": stop, "stationName": STOPS.get(stop, (0, 0, "?"))[2], "lineId": line,
            "direction": direction, "towards": "Euston", "timeToStation": t}


class FakeTfl:
    def __init__(self):
        self.requests: list[httpx.Request] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        p = request.url.path
        if p == "/Line/Mode/bus":
            return httpx.Response(200, json=[{"id": "18", "name": "18"}, {"id": "n29", "name": "N29"}])
        if p == "/StopPoint/Mode/bus":
            sp = [{"naptanId": k, "commonName": v[2], "lon": v[0], "lat": v[1]} for k, v in STOPS.items()]
            return httpx.Response(200, json={"stopPoints": sp, "pageSize": 1000, "total": 3, "page": 1})
        if p == "/Line/18,n29/Arrivals":
            return httpx.Response(200, json=[pred("LX1", "490B", 200), pred("LX1", "490A", 60),
                                             pred("LX2", "490C", 30, line="n29", direction="inbound"),
                                             pred("LX3", "490Z", 10)])
        if p == "/Line/18/Route/Sequence/outbound":
            return httpx.Response(200, json={
                "lineStrings": [json.dumps([[[-0.1, 51.5], [-0.1, 51.51]]])],
                "stopPointSequences": [{"stopPoint": [{"id": "490A", "name": "Stop A", "lat": 51.5, "lon": -0.1}]}],
            })
        return httpx.Response(404, json={})


def test_bearing_and_vehicle_estimate():
    assert bearing_deg(-0.1, 51.5, -0.1, 51.51) == 0.0
    assert 89 < bearing_deg(-0.1, 51.5, -0.09, 51.5) < 91
    vs = {v.id: v for v in vehicles_from_arrivals(
        [pred("LX1", "490B", 200), pred("LX1", "490A", 60), pred("LX9", "490Z", 5)], STOPS, "t")}
    assert set(vs) == {"LX1"}  # unknown stop -> no invented position
    v = vs["LX1"]
    assert (v.next_stop, v.eta_s, v.lon, v.lat, v.bearing, v.dir) == ("490A", 60, -0.10, 51.50, 0.0, "outbound")


async def test_fleet_poll_route_detail_and_user_agent(settings):
    fake = FakeTfl()
    s = settings.model_copy(update={"tfl_app_key": SecretStr("k-secret")})
    store = JsonStore(s.data_dir / "s.json", [])
    async with tfl_client(s, httpx.MockTransport(fake)) as http:
        fleet = Fleet(s, http, store)
        await fleet.load_routes()
        await fleet.load_stops()
        snap = await fleet.poll_once()
        assert [v.id for v in snap.vehicles] == ["LX1", "LX2"] and snap.routes == 2 and snap.source == "tfl"
        detail = await fleet.route_detail("18")
        assert detail.directions[0].dir == "outbound" and detail.directions[0].coords[1] == [-0.1, 51.51]
        assert detail.directions[0].stops[0].id == "490A"
        assert await fleet.route_detail("999") is None
        # stops come from the data-dir cache next time
        n = len(fake.requests)
        fresh = Fleet(s, http, store)
        await fresh.load_stops()
        assert fresh.stops.keys() == STOPS.keys() and len(fake.requests) == n
        # stand-in pairing: real incidents only, stable across calls
        assert await fleet.pairings() == []
        await store.save_run(ModeMetrics(mode="road", run_id="r0", generated_at="1"),
                             [Incident(id="i0", mode="road", run_id="r0", risk=5)])
        assert await fleet.pairings() == []  # road is not paired
        await store.save_run(ModeMetrics(mode="city", run_id="r1", generated_at="1"),
                             [Incident(id="i1", mode="city", run_id="r1", risk=4, came_true="yes")])
        first = await fleet.pairings()
        assert len(first) == 1 and first[0].vehicle_id in {"LX1", "LX2"} and first[0].risk == 4
        assert first[0].stop_name in {"Stop A", "Stop C"} and first[0].towards == "Euston"
        assert await fleet.pairings() == first
        await store.save_run(ModeMetrics(mode="bus", run_id="r2", generated_at="2"),
                             [Incident(id="b1", mode="bus", run_id="r2", risk=3, type="Blocked lane")])
        assert [p.incident_id for p in await fleet.pairings()] == ["b1"]  # latest bus run wins
        await store.save_run(ModeMetrics(mode="bus_front", run_id="r3", generated_at="3"),
                             [Incident(id="f1", mode="bus_front", run_id="r3", risk=2, camera_view="front")])
        await store.save_run(ModeMetrics(mode="bus_nearside", run_id="r4", generated_at="3"),
                             [Incident(id="n1", mode="bus_nearside", run_id="r4", risk=4, camera_view="nearside")])
        assert [p.incident_id for p in await fleet.pairings()] == ["n1", "f1"]  # bus views beat bus
        assert [m.mode for m in await store.metrics()][:3] == ["bus_front", "bus_nearside", "bus"]
    for r in fake.requests:
        assert r.headers["user-agent"] == TFL_USER_AGENT and r.url.params["app_key"] == "k-secret"


def test_api_and_socketio_emit_vehicles(settings):
    s = settings.model_copy(update={"fleet_enabled": True, "fleet_poll_s": 3600, "tfl_app_key": SecretStr("k"),
                                    "mapbox_token": SecretStr("pk.test")})
    t = Transports(vss=httpx.MockTransport(FakeVSS()), tfl=httpx.MockTransport(FakeTfl()))
    app = create_app(s, t, FakeModels())
    with TestClient(app) as c:
        for _ in range(100):
            snap = c.get("/api/vehicles").json()
            if snap["vehicles"]:
                break
            c.portal.call(__import__("asyncio").sleep, 0.05)
        assert {v["id"] for v in snap["vehicles"]} == {"LX1", "LX2"}
        assert c.get("/api/routes").json()[0] == {"id": "18", "name": "18"}
        assert c.get("/api/routes/18").json()["id"] == "18"
        assert c.get("/api/routes/..%2Fx").status_code in (400, 404)
        assert c.get("/api/routes/18;drop").status_code == 400
        assert c.get("/api/fleet/pairings").json() == []
        assert c.get("/api/map-config").json() == {"mapbox_token": "pk.test"}


def test_socketio_wrapper_serves_handshake_and_api(settings):
    with TestClient(create_asgi(settings)) as c:
        r = c.get("/socket.io/", params={"EIO": "4", "transport": "polling"})
        assert r.status_code == 200 and r.text.startswith("0")
        sid = json.loads(r.text[1:])["sid"]
        assert c.post("/socket.io/", params={"EIO": "4", "transport": "polling", "sid": sid}, content="40").text == "OK"
        msg = c.get("/socket.io/", params={"EIO": "4", "transport": "polling", "sid": sid}).text
        assert '"vehicles"' in msg and '"source":"tfl"' in msg
        assert c.get("/healthz").json()["ok"] is True
