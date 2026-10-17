import httpx
import pytest

from sixthsense.clients.http import public_client
from sixthsense.weather import WeatherService, wmo_to_wx


@pytest.mark.parametrize(
    ("code", "wx"),
    [(0, "clear"), (1, "clear"), (2, "cloudy"), (3, "cloudy"), (45, "cloudy"), (48, "cloudy"),
     (51, "rain"), (61, "rain"), (67, "rain"), (71, "cloudy"), (77, "cloudy"), (80, "rain"),
     (82, "rain"), (85, "cloudy"), (86, "cloudy"), (95, "rain"), (99, "rain")],
)
def test_wmo_table(code, wx):
    assert wmo_to_wx(code, True)[0] == wx


def test_is_day_zero_is_night():
    assert wmo_to_wx(0, False)[0] == "night"
    assert wmo_to_wx(61, False) == ("night", "Rain")


async def test_fetch_caches_and_falls_back(settings):
    calls = {"n": 0}

    async def ok(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        assert request.url.params["current"] == "temperature_2m,weather_code,is_day"
        return httpx.Response(200, json={"current": {"temperature_2m": 12.34, "weather_code": 3, "is_day": 1}})

    async with public_client(httpx.MockTransport(ok)) as http:
        svc = WeatherService(settings, http)
        w = await svc.current()
        await svc.current()
    assert (w.wx, w.temp_c, w.source, w.city) == ("cloudy", 12.3, "open-meteo", "London")
    assert calls["n"] == 1

    async def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("blocked", request=request)

    async with public_client(httpx.MockTransport(down)) as http:
        w = await WeatherService(settings, http).current()
    assert w.source == "clock" and w.wx in ("clear", "night") and w.temp_c is None
