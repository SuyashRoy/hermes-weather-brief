#!/usr/bin/env python3
"""weather-brief: today's forecast for a city as one briefing line plus practical flags.

    python3 weather_brief.py "Los Angeles"
    python3 weather_brief.py "Berlin" --units metric
    python3 weather_brief.py "Austin, TX" --json

Uses Open-Meteo (https://open-meteo.com): free, no API key. Python standard
library only. Two HTTPS requests: geocoding (city -> lat/lon/timezone), then
today's hourly + daily forecast in the city's own timezone.

Flags (only the ones that apply are printed):
  - rain likely during commute hours (07-09 or 16-19 local, chance >= 50%)
  - very hot (high >= 95 F / 35 C) or very cold (low <= 32 F / 0 C)
  - high wind (gusts >= 35 mph / 56 km/h, or sustained >= 25 mph / 40 km/h)

Exit codes: 0 ok, 2 city not found, 3 network/API error.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "weather-brief/1.0 (Hermes skill)"
TIMEOUT_S = 15

COMMUTE_HOURS = (7, 8, 9, 16, 17, 18, 19)
RAIN_LIKELY_PCT = 50
# (imperial, metric)
HOT = (95.0, 35.0)
COLD = (32.0, 0.0)
GUST = (35.0, 56.0)
WIND = (25.0, 40.0)

# WMO weather interpretation codes (Open-Meteo docs), condensed.
WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "freezing fog",
       51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
       61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain", 67: "freezing rain",
       71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains", 80: "rain showers",
       81: "rain showers", 82: "violent rain showers", 85: "snow showers", 86: "heavy snow showers",
       95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail"}


class WeatherError(Exception):
    def __init__(self, message: str, exit_code: int = 3):
        super().__init__(message)
        self.exit_code = exit_code


def _get_json(url: str, params: dict) -> dict:
    full = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise WeatherError(f"Open-Meteo request failed: {exc}") from None


def geocode(city: str) -> dict:
    """First Open-Meteo geocoding match: {name, admin1, country, country_code, latitude, longitude, timezone}."""
    name = city.split(",")[0].strip()
    if not name:
        raise WeatherError("No city given.", 2)
    data = _get_json(GEOCODE_URL, {"name": name, "count": 10, "language": "en", "format": "json"})
    results = data.get("results") or []
    hint = city.split(",", 1)[1].strip().lower() if "," in city else ""
    if hint:  # "Portland, OR" / "Paris, France": prefer a match whose region or country fits the hint
        fits = [r for r in results if hint in " ".join(str(r.get(k, "")) for k in
                                                      ("admin1", "country", "country_code")).lower()]
        results = fits or results
    if not results:
        raise WeatherError(f"City not found: {city!r}.", 2)
    return results[0]


def fetch_forecast(place: dict, units: str) -> dict:
    params = {"latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
              "forecast_days": 1,
              "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                       "wind_speed_10m_max,wind_gusts_10m_max,weather_code",
              "hourly": "precipitation_probability"}
    if units == "imperial":
        params.update(temperature_unit="fahrenheit", wind_speed_unit="mph")
    return _get_json(FORECAST_URL, params)


def resolve_units(units: str, place: dict) -> str:
    if units != "auto":
        return units
    return "imperial" if place.get("country_code") in ("US", "LR", "MM") else "metric"


def _first(daily: dict, key: str):
    values = daily.get(key) or [None]
    return values[0]


def flags_for(forecast: dict, units: str) -> list[str]:
    """Practical flags for today, most actionable first. Pure function (unit-tested offline)."""
    i = 0 if units == "imperial" else 1
    t_unit, w_unit = ("°F", "mph") if units == "imperial" else ("°C", "km/h")
    daily, hourly = forecast.get("daily", {}), forecast.get("hourly", {})
    out = []

    commute = []
    for stamp, pct in zip(hourly.get("time", []), hourly.get("precipitation_probability", [])):
        hour = int(stamp[11:13])
        if hour in COMMUTE_HOURS and pct is not None and pct >= RAIN_LIKELY_PCT:
            commute.append((hour, pct))
    if commute:
        am = [h for h, _ in commute if h < 12]
        pm = [h for h, _ in commute if h >= 12]
        when = " and ".join(w for w, hs in (("morning", am), ("evening", pm)) if hs)
        peak = max(p for _, p in commute)
        out.append(f"Rain likely during the {when} commute (up to {peak:.0f}%): take an umbrella.")

    hi, lo = _first(daily, "temperature_2m_max"), _first(daily, "temperature_2m_min")
    if hi is not None and hi >= HOT[i]:
        out.append(f"Very hot: high of {hi:.0f}{t_unit}. Drink water and avoid midday sun.")
    if lo is not None and lo <= COLD[i]:
        out.append(f"Very cold: low of {lo:.0f}{t_unit}. Watch for ice.")

    gust, wind = _first(daily, "wind_gusts_10m_max"), _first(daily, "wind_speed_10m_max")
    if (gust is not None and gust >= GUST[i]) or (wind is not None and wind >= WIND[i]):
        peak = max(v for v in (gust, wind) if v is not None)
        out.append(f"High wind: gusts up to {peak:.0f} {w_unit}.")
    return out


def brief_line(place: dict, forecast: dict, units: str) -> str:
    t_unit = "°F" if units == "imperial" else "°C"
    daily = forecast.get("daily", {})
    where = ", ".join(x for x in (place.get("name"), place.get("admin1") or place.get("country")) if x)
    sky = WMO.get(_first(daily, "weather_code"), "mixed conditions")
    hi, lo = _first(daily, "temperature_2m_max"), _first(daily, "temperature_2m_min")
    rain = _first(daily, "precipitation_probability_max")
    temps = f", high {hi:.0f}{t_unit} / low {lo:.0f}{t_unit}" if hi is not None and lo is not None else ""
    rain_txt = f", {rain:.0f}% max chance of rain" if rain is not None else ""
    day = (_first(daily, "time") or "today")
    return f"{where} ({day}): {sky}{temps}{rain_txt}."


def weather_brief(city: str, units: str = "auto") -> dict:
    """Geocode + forecast + flags. Returns {"line", "flags", "place", "units"}; raises WeatherError."""
    place = geocode(city)
    units = resolve_units(units, place)
    forecast = fetch_forecast(place, units)
    return {"line": brief_line(place, forecast, units), "flags": flags_for(forecast, units),
            "place": {k: place.get(k) for k in ("name", "admin1", "country", "latitude", "longitude", "timezone")},
            "units": units}


def render(result: dict) -> str:
    flags = result["flags"]
    return result["line"] + ("\n" + "\n".join(f"- {f}" for f in flags) if flags else "\n- No weather flags today.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Today's weather briefing for a city (Open-Meteo, no API key).")
    p.add_argument("city", help='City name, optionally with region/country: "Portland, OR"')
    p.add_argument("--units", choices=["auto", "imperial", "metric"], default="auto")
    p.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = p.parse_args(argv)
    try:
        result = weather_brief(args.city, args.units)
    except WeatherError as exc:
        print(f"weather-brief: {exc}", file=sys.stderr)
        return exc.exit_code
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
