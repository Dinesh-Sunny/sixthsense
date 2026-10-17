"""Live sky for the header pill: Open-Meteo current weather, cached server-side.

Open-Meteo free tier is ~10k calls/day, so browsers never call it directly. Data CC BY 4.0.
"""

import asyncio
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from .clients.http import HttpClient
from .contracts import Weather, Wx
from .settings import Settings

log = logging.getLogger("sixthsense.weather")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NIGHT_HOURS = (19, 7)  # clock fallback: dark from 19:00 to 07:00

# WMO weather codes -> (wx, label)
_CLEAR = {0: "Clear", 1: "Mostly clear"}
_CLOUDY = {
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    71: "Snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    85: "Snow showers",
    86: "Snow showers",
}
_RAIN = {
    **{c: "Drizzle" for c in (51, 53, 55, 56, 57)},
    **{c: "Rain" for c in (61, 63, 65, 66, 67)},
    **{c: "Showers" for c in (80, 81, 82)},
    **{c: "Thunderstorm" for c in (95, 96, 99)},
}


def wmo_to_wx(code: int, is_day: bool) -> tuple[Wx, str]:
    if code in _RAIN:
        wx: Wx = "rain"
        label = _RAIN[code]
    elif code in _CLOUDY:
        wx, label = "cloudy", _CLOUDY[code]
    else:
        wx, label = "clear", _CLEAR.get(code, "Clear")
    if not is_day:
        return "night", label
    return wx, label


class WeatherService:
    def __init__(self, settings: Settings, http: HttpClient) -> None:
        self.settings = settings
        self.http = http
        self._cache: tuple[float, Weather] | None = None
        self._lock = asyncio.Lock()

    def _clock(self) -> Weather:
        try:
            now = datetime.now(ZoneInfo(self.settings.weather_tz))
        except ZoneInfoNotFoundError:
            now = datetime.now().astimezone()
        dark = now.hour >= NIGHT_HOURS[0] or now.hour < NIGHT_HOURS[1]
        return Weather(
            city=self.settings.weather_city,
            temp_c=None,
            label="Night" if dark else "Day",
            wx="night" if dark else "clear",
            source="clock",
        )

    async def _fetch(self) -> Weather:
        s = self.settings
        r = await self.http.get(
            OPEN_METEO_URL,
            params={
                "latitude": s.weather_lat,
                "longitude": s.weather_lon,
                "current": "temperature_2m,weather_code,is_day",
                "timezone": "auto",
            },
        )
        r.raise_for_status()
        cur = r.json()["current"]
        wx, label = wmo_to_wx(int(cur["weather_code"]), bool(cur.get("is_day", 1)))
        return Weather(
            city=s.weather_city,
            temp_c=round(float(cur["temperature_2m"]), 1),
            label=label,
            wx=wx,
            source="open-meteo",
        )

    async def current(self) -> Weather:
        if self._cache and self._cache[0] > time.monotonic():
            return self._cache[1]
        async with self._lock:  # one upstream call per burst
            if self._cache and self._cache[0] > time.monotonic():
                return self._cache[1]
            try:
                w = await self._fetch()
            except (httpx.HTTPError, KeyError, ValueError) as e:
                log.info("weather: Open-Meteo unavailable (%s)", type(e).__name__)
                # Serve stale if we have it, else the clock. Retry sooner than a full TTL.
                stale = self._cache[1] if self._cache else self._clock()
                self._cache = (time.monotonic() + 60.0, stale)
                return stale
            self._cache = (time.monotonic() + self.settings.weather_ttl_s, w)
            return w
