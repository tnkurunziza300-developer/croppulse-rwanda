from pathlib import Path
from contextlib import contextmanager
from streamlit.testing.v1 import AppTest

from utils import geography, weather
import product_pages

ROOT = str(Path(__file__).resolve().parent.parent)
PRE = f"import sys; sys.path.insert(0, r'{ROOT}')\nimport product_pages\nproduct_pages.weather_page()\n"


def test_weather_page_exposes_national_districts_and_unverified_coordinates():
    at = AppTest.from_string(PRE, default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert list(at.selectbox[0].options) == geography.ALL_DISTRICTS
    assert any("NISR's 2022 boundary-service metadata" in item.value for item in at.caption)
    assert any("does not yet verify" in item.value for item in at.warning)
    assert any("No forecast requested" in item.value for item in at.info)
    assert len(at.text_input) == 3  # farm coordinates and observation source


def test_weather_page_renders_forecast_and_stale_warning(monkeypatch):
    result = {"status": "stale", "source": "Open-Meteo", "attribution": "Weather forecast data by Open-Meteo.com (CC BY 4.0)",
              "retrieved_at": "2026-10-18T10:00:00+00:00", "cache_age_seconds": 1900,
              "coordinates": {"latitude": -2.5, "longitude": 29.9},
              "daily_forecast": [{"date": "2026-10-18", "temperature_max_c": 25, "temperature_min_c": 15, "precipitation_sum_mm": 2}],
              "message": "Provider unavailable; cached forecast."}
    monkeypatch.setattr(weather, "get_forecast", lambda *_args, **_kwargs: result)
    at = AppTest.from_string(PRE, default_timeout=90).run()
    at.text_input[0].set_value("-2.5")
    at.text_input[1].set_value("29.9")
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("STALE FORECAST" in item.value and "31 min" in item.value for item in at.warning)
    assert any("Retrieved:" in item.value and "Open-Meteo" in item.value for item in at.caption)
    assert at.dataframe


def test_weather_page_renders_provider_error(monkeypatch):
    monkeypatch.setattr(weather, "get_forecast", lambda *_args, **_kwargs: {"status": "unavailable", "message": "Weather provider is unavailable."})
    at = AppTest.from_string(PRE, default_timeout=90).run()
    at.text_input[0].set_value("-2.5")
    at.text_input[1].set_value("29.9")
    at.button[0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Weather provider is unavailable" in item.value for item in at.error)


def test_weather_request_is_wrapped_in_loading_indicator(monkeypatch):
    events = []

    @contextmanager
    def spinner(label):
        events.append(("loading", label))
        yield
        events.append(("finished", label))

    monkeypatch.setattr(product_pages.st, "spinner", spinner)
    monkeypatch.setattr(weather, "get_forecast", lambda latitude, longitude: (latitude, longitude))
    assert product_pages._request_weather_forecast("-2.5", "29.9") == ("-2.5", "29.9")
    assert events[0][0] == "loading" and events[1][0] == "finished"
    assert "Open-Meteo" in events[0][1]
