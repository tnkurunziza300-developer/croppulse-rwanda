"""Coordinate-based Open-Meteo forecast adapter.

Forecasts are model estimates for the supplied point, not observations or farm
measurements. Coordinates must be supplied by a caller; district centroids are
deliberately not substituted for farm locations.
"""
from datetime import date, datetime, timezone
from json import loads
from math import isfinite
from threading import RLock
from time import monotonic
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROVIDER = "Open-Meteo"
ATTRIBUTION = "Weather forecast data by Open-Meteo.com (CC BY 4.0)"
ENDPOINT = "https://api.open-meteo.com/v1/forecast"
# Extent from NISR's District Boundary 2022 layer, rounded to the service's
# published precision. This bounds-check is not point-in-polygon validation.
RWANDA_BOUNDS = (-2.840230102, -1.047166706, 28.861730820, 30.899746642)  # S, N, W, E
CACHE_SECONDS = 30 * 60
STALE_SECONDS = 24 * 60 * 60
_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_lock = RLock()


def _valid_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None
    south, north, west, east = RWANDA_BOUNDS
    if not (south <= lat <= north and west <= lon <= east):
        return None
    return round(lat, 4), round(lon, 4)


def _parse(payload, retrieved_at):
    if not isinstance(payload, dict):
        raise ValueError("Weather response was not an object.")
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Weather response did not contain daily forecast data.")
    dates = daily.get("time")
    if not isinstance(dates, list) or not dates:
        raise ValueError("Weather response contained no forecast dates.")
    fields = {
        "temperature_max_c": "temperature_2m_max",
        "temperature_min_c": "temperature_2m_min",
        "precipitation_sum_mm": "precipitation_sum",
    }
    forecast = []
    for i, day in enumerate(dates):
        try:
            date.fromisoformat(day)
        except (TypeError, ValueError):
            raise ValueError("Weather response contained an invalid forecast date.") from None
        item = {"date": day}
        for output, key in fields.items():
            values = daily.get(key)
            value = values[i] if isinstance(values, list) and i < len(values) else None
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value)):
                raise ValueError("Weather response contained an invalid numeric forecast value.")
            item[output] = value
        forecast.append(item)
    return {
        "status": "available", "source": PROVIDER, "attribution": ATTRIBUTION,
        "retrieved_at": retrieved_at.isoformat(), "forecast_type": "model forecast",
        "coordinates": {"latitude": payload.get("latitude"), "longitude": payload.get("longitude")},
        "daily_forecast": forecast,
        "message": "Point forecast; local conditions can differ. This is not an observation or a seasonal outlook.",
    }


def get_forecast(latitude=None, longitude=None, *, fetcher=None, now=None):
    """Fetch up to seven daily values; return cached stale data on provider errors.

    No request is made for missing or out-of-country coordinates. An optional
    fetcher(payload_url, timeout) is provided for deterministic tests.
    """
    coords = _valid_coordinates(latitude, longitude)
    if coords is None:
        return {"status": "unavailable", "message": "Enter valid coordinates within Rwanda to request a point forecast."}
    clock = now or datetime.now(timezone.utc)
    key = coords
    with _lock:
        cached = _cache.get(key)
    age = monotonic() - cached[0] if cached else None
    if cached and age <= CACHE_SECONDS:
        return {**cached[1], "cache": "fresh"}
    query = urlencode({"latitude": coords[0], "longitude": coords[1], "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum", "forecast_days": 7, "timezone": "Africa/Kigali"})
    url = f"{ENDPOINT}?{query}"
    try:
        if fetcher:
            payload = fetcher(url, 8)
        else:
            request = Request(url, headers={"User-Agent": "CropPulse-Rwanda/1.0 (weather attribution: open-meteo.com)"})
            with urlopen(request, timeout=8) as response:
                payload = loads(response.read().decode("utf-8"))
        result = _parse(payload, clock)
        with _lock:
            _cache[key] = (monotonic(), result)
        return {**result, "cache": "miss"}
    except (URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
        if cached and age is not None and age <= STALE_SECONDS:
            return {**cached[1], "status": "stale", "cache": "stale", "cache_age_seconds": max(0, int(age)), "message": "Weather provider is unavailable. Showing a cached forecast; check its retrieval time before acting."}
        return {"status": "unavailable", "source": PROVIDER, "message": "Weather provider is unavailable and no recent cached forecast exists."}


def clear_cache():
    """Clear process-local cache (used by maintenance and isolated tests)."""
    with _lock:
        _cache.clear()
