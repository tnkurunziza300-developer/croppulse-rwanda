from datetime import datetime, timezone

from utils import weather


def _payload():
    return {"latitude": -2.5, "longitude": 29.9, "daily": {
        "time": ["2026-10-18", "2026-10-19"],
        "temperature_2m_max": [25.0, 24.0],
        "temperature_2m_min": [15.0, 16.0],
        "precipitation_sum": [2.0, 0.0],
    }}


def test_requires_coordinates_in_rwanda_without_fetching():
    calls = []
    result = weather.get_forecast(fetcher=lambda *_: calls.append(True))
    assert result["status"] == "unavailable" and not calls
    assert weather.get_forecast(-10, 30)["status"] == "unavailable"


def test_forecast_is_provenanced_and_cached(monkeypatch):
    weather.clear_cache()
    monkeypatch.setattr(weather, "monotonic", lambda: 100.0)
    calls = []

    def fetch(url, timeout):
        calls.append((url, timeout))
        return _payload()

    result = weather.get_forecast(-2.5, 29.9, fetcher=fetch, now=datetime(2026, 10, 18, tzinfo=timezone.utc))
    cached = weather.get_forecast(-2.5, 29.9, fetcher=fetch)
    assert result["status"] == "available" and result["forecast_type"] == "model forecast"
    assert result["daily_forecast"][0]["precipitation_sum_mm"] == 2.0
    assert "CC BY 4.0" in result["attribution"] and cached["cache"] == "fresh"
    assert len(calls) == 1 and "forecast_days=7" in calls[0][0] and calls[0][1] == 8
    weather.clear_cache()


def test_provider_failure_returns_recent_cache_as_stale(monkeypatch):
    weather.clear_cache()
    ticks = iter([0.0, 1900.0])
    monkeypatch.setattr(weather, "monotonic", lambda: next(ticks))
    weather.get_forecast(-2.5, 29.9, fetcher=lambda *_: _payload())
    result = weather.get_forecast(-2.5, 29.9, fetcher=lambda *_: (_ for _ in ()).throw(TimeoutError()))
    assert result["status"] == "stale" and result["cache"] == "stale"
    assert "cached forecast" in result["message"]
    weather.clear_cache()


def test_malformed_provider_payload_is_unavailable():
    weather.clear_cache()
    for payload in ({"daily": {}}, {"daily": {"time": ["not-a-date"]}},
                    {"daily": {"time": ["2026-10-18"], "precipitation_sum": ["rain"]}}):
        result = weather.get_forecast(-2.5, 29.9, fetcher=lambda *_args, value=payload: value)
        assert result["status"] == "unavailable"
        assert "forecast" in result["message"].lower()
    weather.clear_cache()
