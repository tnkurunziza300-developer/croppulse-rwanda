import pytest
import jwt
import backend.api as api_module
from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
from pathlib import Path
from uuid import uuid4

from backend.api import app
from backend.db import Base, get_engine, _engine
from backend.models import Farmer
from backend.api import password_hash
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


@pytest.fixture
def api_client(monkeypatch):
    # Fixed writable workspace temp root avoids this environment's broken Windows tempfile ACLs.
    temp_root = Path(__file__).resolve().parent.parent / ".test-runtime" / "api-test-databases"
    temp_root.mkdir(parents=True, exist_ok=True)
    db_path = temp_root / f"records-{uuid4().hex}.sqlite3"
    monkeypatch.setenv("CROP_PULSE_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "test-only-secret-key-of-at-least-32-characters")
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "test")
    _engine.cache_clear()
    Base.metadata.create_all(get_engine())
    with TestClient(app) as client:
        yield client
    get_engine().dispose()
    _engine.cache_clear()
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(f"{db_path}{suffix}")
        if candidate.exists(): candidate.unlink()


def register(client, email="farmer@example.com"):
    response = client.post("/v1/auth/register", json={
        "email": email, "password": "long-test-password-123", "display_name": "Test Farmer",
        "privacy_notice_accepted": True,
    })
    assert response.status_code == 201
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_authentication_hashes_password_and_rejects_plaintext(api_client):
    token = register(api_client)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert api_client.get("/v1/me", headers=auth(token)).status_code == 200
    with Session(get_engine()) as db:
        farmer = db.scalar(select(Farmer).where(Farmer.email == "farmer@example.com"))
        assert farmer.password_hash != "long-test-password-123"
        assert password_hash.verify("long-test-password-123", farmer.password_hash)
    bad_login = api_client.post("/v1/auth/login", json={"email": "farmer@example.com", "password": "wrong"})
    assert bad_login.status_code == 401
    assert api_client.get("/v1/farms").status_code == 401
    assert api_client.post("/v1/auth/logout", headers=auth(token)).status_code == 204
    assert api_client.get("/v1/me", headers=auth(token)).status_code == 401


def test_browser_session_cookie_is_available_to_same_host_streamlit_and_cleared_on_logout(api_client):
    csrf = api_client.get("/v1/browser-auth/csrf")
    assert csrf.status_code == 200
    response = api_client.post("/v1/browser-auth/register", headers={"X-CSRF-Token": csrf.json()["csrf_token"]}, json={
        "email": "browser-cookie@example.com", "password": "long-test-password-123",
        "display_name": "Browser Cookie Farmer", "privacy_notice_accepted": True,
    })
    assert response.status_code == 201
    set_cookie = response.headers["set-cookie"]
    assert "cp_session=" in set_cookie and "Path=/;" in set_cookie and "HttpOnly" in set_cookie
    assert api_client.get("/v1/me").status_code == 200

    logout = api_client.post("/v1/browser-auth/logout", headers={"X-CSRF-Token": csrf.json()["csrf_token"]})
    assert logout.status_code == 204
    assert 'cp_session="";' in logout.headers["set-cookie"] and "Path=/;" in logout.headers["set-cookie"]
    assert api_client.get("/v1/me").status_code == 401


def test_health_and_expired_session(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    expired = jwt.encode({"sub": "missing-user", "exp": 1, "jti": "expired"}, "test-only-secret-key-of-at-least-32-characters", algorithm="HS256")
    assert api_client.get("/v1/me", headers=auth(expired)).status_code == 401


def test_crop_recommendation_endpoint_requires_auth_and_uses_shared_validated_engine(api_client, monkeypatch):
    import pandas as pd
    from backend import api as backend_api

    frame = pd.DataFrame({
        "district": ["Huye"] * 4, "crop": ["Beans"] * 4, "season": ["A"] * 4,
        "year": [2021, 2022, 2023, 2024], "area_ha": [100.0] * 4,
        "production_t": [100.0, 110.0, 105.0, 115.0],
    })
    monkeypatch.setattr(backend_api, "load_data", lambda: (frame, {
        "state": "validated", "message": "Manifest and structural checks passed.",
        "provenance": [{"title": "NISR SAS district crop area and production",
                        "publisher": "National Institute of Statistics of Rwanda (NISR)",
                        "reference_period": "2021–2024", "sha256": "a" * 64}],
    }))
    payload = {"district": "Huye", "season": "A", "elevation_m": None,
               "irrigation": "Unknown", "water_availability": "Unknown"}
    assert api_client.post("/v1/crop-planning/recommendations", json=payload).status_code == 401

    token = register(api_client, "crop-planning@example.com")
    response = api_client.post("/v1/crop-planning/recommendations", headers=auth(token), json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    beans = next(item for item in result["results"] if item["crop"] == "Beans")
    assert result["context"]["statistics_status"] == "validated"
    assert result["context"]["statistics_provenance"][0]["publisher"] == "National Institute of Statistics of Rwanda (NISR)"
    assert beans["used_stats"] is False and beans["history_context_available"] is True and beans["history"]["n_periods"] == 4
    assert "descriptive historical context only" in beans["evidence_basis"]
    assert "not independently verified" in beans["evidence_basis"]
    assert beans["evidence_record"]["statistics_used_for_ranking"] is False
    assert beans["evidence_record"]["evidence_status"] == "provisional"
    assert beans["evidence_record"]["approved_guidance"] == []
    assert beans["status"].startswith("Provisional guide fit:")
    assert "confidence" not in beans
    assert api_client.post("/v1/crop-planning/recommendations", headers=auth(token),
                           json={**payload, "unknown": "ignored"}).status_code == 422


def test_weather_outlook_manifest_has_explicit_ranges_and_existing_pdf_sources():
    from utils.weather_bulletin_data import load_records

    records = load_records()
    observed = {(row["period_label"], row["value_min"], row["value_max"], row["unit"]) for row in records}
    expected = {
        ("February 2026", 80, 360, "mm per month"), ("March 2026", 100, 350, "mm per month"),
        ("April 2026", 100, 320, "mm per month"), ("May 2026", 50, 230, "mm per month"),
        ("June 2026", 20, 120, "mm per month"), ("July 2026", 0, 35, "mm per month"),
        ("August 2026", 5, 100, "mm per month"), ("December 2025", 40, 200, "mm per month"),
        ("October 2026", 90, 300, "mm per month"),
        ("March–May 2025 (MAM)", 250, 550, "mm per season"),
        ("June–August 2026 (JJA)", 40, 250, "mm per season"),
        ("March–May 2026 (MAM)", 280, 800, "mm per season"),
        ("September–December 2026 (SOND)", 300, 1000, "mm per season"),
    }
    source_dir = Path(__file__).resolve().parent.parent / "data" / "raw" / "weather_climate"
    assert len(records) == 13 and observed == expected
    assert all((source_dir / row["document_key"]).is_file() for row in records)
    assert all(row["geography_type"] == "national" and row["source_page"] == 1 for row in records)
    assert all(row["source_text"].startswith("Transcription note, not a quotation:") for row in records)


def test_weather_bulletin_records_are_source_linked_filterable_and_authenticated(api_client):
    import json
    from datetime import date
    from backend.models import WeatherBulletin, WeatherBulletinRecord
    from utils.weather_bulletin_data import import_records
    source_file = Path(__file__).resolve().parent.parent / ".test-runtime" / f"weather-records-{uuid4().hex}.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)

    token = register(api_client, "weather-records@example.com")
    record_data = {
        "document_key": "source.pdf", "record_key": "national-rainfall-outlook",
        "record_type": "monthly_outlook", "geography_type": "national",
        "geography_label": "Rwanda (national range)", "period_label": "October 2026",
        "valid_from": "2026-10-01", "valid_to": "2026-10-31",
        "value_min": 90, "value_max": 300, "normal_min": None, "normal_max": None,
        "unit": "mm per month", "anomaly_label": None, "source_page": 1,
        "source_text": "Transcription note, not a quotation: national rainfall outlook range 90 to 300 mm per month for October 2026; see PDF page 1.",
    }
    source_file.write_text(json.dumps([record_data]), encoding="utf-8")
    try:
        with Session(get_engine()) as db:
            bulletin = WeatherBulletin(
                document_key="source.pdf", title="October rainfall outlook", category="monthly",
                publisher="METEO RWANDA", issued_at=date(2026, 9, 1),
                valid_from=date(2026, 10, 1), valid_to=date(2026, 10, 31),
                source_url="https://example.test/source.pdf", provenance_status="publisher-indicated",
                sha256="a" * 64, document_bytes=b"%PDF-test",
            )
            db.add(bulletin)
            db.commit()
            assert import_records(db, source_file) == 1
            assert import_records(db, source_file) == 1
            assert len(db.scalars(select(WeatherBulletinRecord)).all()) == 1
    finally:
        source_file.unlink(missing_ok=True)

    response = api_client.get("/v1/weather/climate-data?year=2026&record_type=monthly_outlook&search=October", headers=auth(token))
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["value_min"] == 90 and payload["items"][0]["value_max"] == 300
    assert payload["items"][0]["bulletin"]["document_url"].endswith("/document")
    assert payload["items"][0]["source_page"] == 1
    assert api_client.get("/v1/weather/climate-data").status_code == 401
    assert api_client.get("/v1/weather/climate-data?record_type=observations", headers=auth(token)).status_code == 422


def test_field_crud_ownership_coordinates_archive_and_crop_plan_linkage(api_client):
    farmer = register(api_client, "field-owner@example.com")
    another = register(api_client, "field-other@example.com")
    headers = auth(farmer)
    farm = api_client.post("/v1/farms", headers=headers, json={"name": "Home farm", "district": "Huye"}).json()
    other_farm = api_client.post("/v1/farms", headers=auth(another), json={"name": "Other farm", "district": "Huye"}).json()
    fields_url = f"/v1/farms/{farm['id']}/fields"
    created = api_client.post(fields_url, headers=headers, json={"name": "Upper plot", "area_ha": 0.7}).json()
    assert created["area_ha"] == 0.7 and created["latitude"] is None
    assert api_client.get(f"/v1/farms/{other_farm['id']}/fields", headers=headers).status_code == 404
    assert api_client.put(f"{fields_url}/{created['id']}", headers=auth(another), json={"name": "Stolen", "area_ha": None}).status_code == 404
    assert api_client.post(fields_url, headers=headers, json={"name": "Incomplete", "latitude": -2.5}).status_code == 422
    assert api_client.post(fields_url, headers=headers, json={"name": "Bad location", "latitude": 91, "longitude": 29}).status_code == 422
    assert api_client.post(fields_url, headers=headers, json={"name": "Outside Rwanda", "latitude": 0, "longitude": 29}).status_code == 422
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=headers, json={
        "district": "Huye", "crop": "Maize", "season": "A", "planting_date": "2026-09-01",
        "area_ha": 0.5, "field_id": created["id"], "plan": {"farmer_notes": "test"},
    })
    assert plan.status_code == 201 and plan.json()["field_id"] == created["id"]
    assert plan.json()["evidence"] == []
    wrong_field_plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=headers, json={
        "district": "Huye", "crop": "Maize", "season": "A", "planting_date": "2026-09-02",
        "area_ha": 0.5, "field_id": "not-a-field-on-this-farm", "plan": {},
    })
    assert wrong_field_plan.status_code == 404
    archived = api_client.post(f"{fields_url}/{created['id']}/archive", headers=headers)
    assert archived.status_code == 200 and archived.json()["archived_at"]
    assert api_client.get(fields_url, headers=headers).json() == []
    plans = api_client.get(f"/v1/farms/{farm['id']}/plans", headers=headers).json()
    assert len(plans) == 1 and plans[0]["field_id"] == created["id"]


def test_crop_plan_edit_is_owner_scoped_validated_and_limited_to_unstarted_plans(api_client):
    owner = register(api_client, "plan-edit-owner@example.com")
    other = register(api_client, "plan-edit-other@example.com")
    headers = auth(owner)
    farm = api_client.post("/v1/farms", headers=headers,
                           json={"name": "Plan edit farm", "district": "Huye"}).json()
    base = f"/v1/farms/{farm['id']}/plans"
    created = api_client.post(base, headers=headers, json={
        "district": "Huye", "crop": "Maize", "season": "A", "planting_date": "2026-09-01",
        "area_ha": 0.5, "plan": {"farmer_notes": "first draft", "recommendation_snapshot": {"crop": "Maize"}},
    })
    assert created.status_code == 201
    plan_id = created.json()["id"]
    update = {"district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-10-12",
              "area_ha": 0.8, "field_id": None, "plan": {"farmer_notes": "revised"}}
    url = f"{base}/{plan_id}"
    assert api_client.put(url, headers=auth(other), json=update).status_code == 404
    invalid = {**update, "area_ha": 0}
    assert api_client.put(url, headers=headers, json=invalid).status_code == 422
    saved = api_client.put(url, headers=headers, json=update)
    assert saved.status_code == 200
    assert saved.json()["crop"] == "Beans" and saved.json()["season"] == "B"
    assert saved.json()["area_ha"] == 0.8 and saved.json()["plan"] == {"farmer_notes": "revised"}
    planted = api_client.patch(f"{url}/status", headers=headers,
                               json={"status": "planted", "actual_planting_date": "2026-10-13"})
    assert planted.status_code == 200
    assert api_client.put(url, headers=headers, json=update).status_code == 409


def test_saved_weather_forecasts_require_consent_and_are_private_with_stale_status(api_client, monkeypatch):
    owner_token = register(api_client, "weather-owner@example.com")
    other_token = register(api_client, "weather-other@example.com")
    retrieved_at = "2026-10-22T08:00:00+00:00"
    provider_result = {"status": "available", "source": "Open-Meteo", "retrieved_at": retrieved_at,
        "daily_forecast": [{"date": "2026-10-22", "temperature_max_c": 24, "temperature_min_c": 15,
            "precipitation_sum_mm": 1}], "message": "Model forecast"}
    monkeypatch.setattr(api_module, "get_forecast", lambda *_args: dict(provider_result))
    url = "/v1/weather/forecast"
    request = {"latitude": -2.5, "longitude": 29.9}

    assert api_client.post(url, headers=auth(owner_token), json=request).status_code == 422
    saved = api_client.post(url, headers=auth(owner_token), json={**request, "save_to_account": True})
    assert saved.status_code == 200 and saved.json()["stored"] is True
    assert api_client.get("/v1/weather/forecasts", headers=auth(other_token)).json()["items"] == []

    provider_result.update(status="stale", cache="stale", cache_age_seconds=1900,
        message="Provider unavailable; showing cached data.")
    stale = api_client.post(url, headers=auth(owner_token), json={**request, "save_to_account": True})
    assert stale.status_code == 200 and stale.json()["stored"] is True
    listed = api_client.get("/v1/weather/forecasts", headers=auth(owner_token)).json()["items"]
    assert len(listed) == 1
    assert listed[0]["status"] == listed[0]["forecast"]["status"] == "stale"
    assert listed[0]["retrieved_at"] == retrieved_at


def test_weather_forecast_links_only_owner_field_with_matching_saved_coordinates(api_client, monkeypatch):
    owner = register(api_client, "field-weather-owner@example.com")
    other = register(api_client, "field-weather-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Weather farm", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={
        "name": "Upper field", "latitude": -2.5, "longitude": 29.9,
    }).json()
    provider = {"status": "available", "source": "Open-Meteo", "retrieved_at": "2026-10-22T08:00:00+00:00",
                "daily_forecast": [{"date": "2026-10-22", "temperature_max_c": 22,
                    "temperature_min_c": 14, "precipitation_sum_mm": 1}], "message": "Model forecast"}
    monkeypatch.setattr(api_module, "get_forecast", lambda *_args: dict(provider))
    url = "/v1/weather/forecast"
    payload = {"latitude": -2.5, "longitude": 29.9, "save_to_account": True,
               "field_id": field["id"], "location_source": "saved_field"}
    assert api_client.post(url, headers=auth(other), json=payload).status_code == 404
    assert api_client.post(url, headers=auth(owner), json={**payload, "longitude": 29.91}).status_code == 409
    saved = api_client.post(url, headers=auth(owner), json=payload)
    assert saved.status_code == 200
    context = saved.json()["location_context"]
    assert context["association"] == "owned_field_record"
    assert context["field_id"] == field["id"] and context["farm_name"] == "Weather farm"
    assert context["geographic_verification"] == "not_independently_verified"
    assert api_client.get("/v1/weather/forecasts", headers=auth(owner)).json()["items"][0]["field_id"] == field["id"]
    manual = api_client.post(url, headers=auth(owner), json={
        "latitude": -2.6, "longitude": 29.8, "save_to_account": True, "location_source": "manual",
    })
    assert manual.status_code == 200
    assert manual.json()["location_context"]["association"] == "coordinate_only"


def test_weather_alert_preferences_are_owner_scoped_off_by_default_and_reversible(api_client):
    owner = register(api_client, "alert-pref-owner@example.com")
    other = register(api_client, "alert-pref-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Alert farm", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={
        "name": "Alert field", "latitude": -2.5, "longitude": 29.9,
    }).json()
    path = "/v1/weather/alert-preferences"
    assert api_client.get(path).status_code == 401
    initial = api_client.get(path, headers=auth(owner)).json()
    assert initial["items"][0]["enabled"] is False
    assert initial["active_rules"] == []
    assert api_client.put(f"{path}/{field['id']}", headers=auth(other), json={"enabled": True}).status_code == 404
    assert api_client.put(f"{path}/{field['id']}", headers=auth(owner), json={"enabled": True}).json()["enabled"] is True
    assert api_client.get(path, headers=auth(other)).json()["items"] == []
    assert api_client.put(f"{path}/{field['id']}", headers=auth(owner), json={"enabled": False}).json()["enabled"] is False
    assert api_client.get(path, headers=auth(owner)).json()["items"][0]["enabled"] is False


def test_weather_alert_history_is_private_deduplicated_acknowledgeable_and_expires(api_client):
    owner = register(api_client, "alert-history-owner@example.com")
    other = register(api_client, "alert-history-other@example.com")
    owner_id = api_client.get("/v1/me", headers=auth(owner)).json()["id"]
    now = datetime.now(timezone.utc)
    with Session(get_engine()) as db:
        row = api_module.models.WeatherAlert(
            recipient_id=owner_id, alert_type="test_only", rule_id="test-only", rule_version="test",
            weather_source="Open-Meteo", forecast_retrieved_at=now,
            valid_from=date.today(), valid_to=date.today(), reason="Test fixture only.",
            evidence_status="test_fixture", evidence_snapshot_json="{}", approval_status="approved", status="active",
            dedupe_key="a" * 64, created_at=now, expires_at=now + timedelta(days=1),
        )
        db.add(row); db.commit(); alert_id = row.id
        db.add(api_module.models.WeatherAlert(
            recipient_id=owner_id, alert_type="test_only", rule_id="test-only", rule_version="test",
            weather_source="Open-Meteo", forecast_retrieved_at=now,
            valid_from=date.today(), valid_to=date.today(), reason="Duplicate fixture.",
            evidence_status="test_fixture", evidence_snapshot_json="{}", approval_status="approved", status="active",
            dedupe_key="a" * 64, created_at=now, expires_at=now + timedelta(days=1),
        ))
        with pytest.raises(SQLAlchemyError):
            db.commit()
        db.rollback()
        expired = api_module.models.WeatherAlert(
            recipient_id=owner_id, alert_type="test_expired", rule_id="test-only", rule_version="test",
            weather_source="Open-Meteo", forecast_retrieved_at=now - timedelta(days=2),
            valid_from=date.today() - timedelta(days=2), valid_to=date.today() - timedelta(days=1),
            reason="Expired fixture only.", evidence_status="test_fixture", approval_status="approved",
            evidence_snapshot_json="{}",
            status="active", dedupe_key="b" * 64, created_at=now - timedelta(days=2),
            expires_at=now - timedelta(days=1),
        )
        db.add(expired); db.commit()
    path = "/v1/weather/alerts"
    assert api_client.get(path, headers=auth(owner)).json()["total"] == 2
    assert api_client.get(path, headers=auth(other)).json()["items"] == []
    expired_item = next(item for item in api_client.get(path, headers=auth(owner)).json()["items"] if item["status"] == "expired")
    assert api_client.patch(f"{path}/{expired_item['id']}/status", headers=auth(owner), json={"status": "dismissed"}).status_code == 409
    assert api_client.patch(f"{path}/{alert_id}/status", headers=auth(other), json={"status": "acknowledged"}).status_code == 404
    changed = api_client.patch(f"{path}/{alert_id}/status", headers=auth(owner), json={"status": "acknowledged"})
    assert changed.status_code == 200 and changed.json()["status"] == "acknowledged"
    assert changed.json()["acknowledged_at"] is not None


def test_health_hides_database_driver_details(api_client, monkeypatch):
    class BrokenEngine:
        def connect(self):
            raise SQLAlchemyError("private://db-password and SQL details")
    monkeypatch.setattr(api_module, "get_engine", lambda: BrokenEngine())
    response = api_client.get("/health")
    assert response.status_code == 503
    assert "private://" not in response.text and "db-password" not in response.text


def test_frontend_logout_clears_local_login_state():
    from backend.client import clear_local_login_state
    state = {"cp_access_token": "synthetic", "cp_farmer": {"id": "synthetic"}, "cp_selected_farm": "synthetic", "active_farm_choice": "synthetic", "keep": "ui preference"}
    clear_local_login_state(state)
    assert state == {"keep": "ui preference"}


def test_api_client_falls_back_to_standard_library_when_httpx_is_missing(monkeypatch):
    import builtins
    import urllib.request
    from backend.client import request
    original_import = builtins.__import__

    def import_without_httpx(name, *args, **kwargs):
        if name == "httpx":
            raise ModuleNotFoundError("No module named 'httpx'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_httpx)

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return b'{"status":"ok"}'

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    assert request("GET", "/health", authenticated=False) == {"status": "ok"}


def test_private_messaging_pair_access_unread_and_live_scope_enforcement(api_client):
    farmer_token = register(api_client, "messaging-farmer@example.com")
    reviewer_token = register(api_client, "messaging-reviewer@example.com")
    admin_token = register(api_client, "messaging-admin@example.com")
    outsider_token = register(api_client, "messaging-outsider@example.com")
    farmer_id = api_client.get("/v1/me", headers=auth(farmer_token)).json()["id"]
    reviewer_id = api_client.get("/v1/me", headers=auth(reviewer_token)).json()["id"]
    admin_id = api_client.get("/v1/me", headers=auth(admin_token)).json()["id"]
    with Session(get_engine()) as db:
        db.get(Farmer, reviewer_id).role = "reviewer"
        db.get(Farmer, admin_id).role = "admin"
        from backend.models import ReviewerDistrict
        db.add(ReviewerDistrict(reviewer_id=reviewer_id, district="Huye"))
        db.commit()
    assert api_client.post("/v1/farms", headers=auth(farmer_token), json={
        "name": "Messaging farm", "district": "Huye", "area_ha": 1,
    }).status_code == 201
    assert api_client.get("/v1/messaging/reviewers", headers=auth(farmer_token)).status_code == 403
    assert api_client.get("/v1/messaging/conversations", headers=auth(farmer_token)).status_code == 403
    assert api_client.post("/v1/messaging/conversations", headers=auth(farmer_token), json={
        "reviewer_id": reviewer_id,
    }).status_code == 403
    assert api_client.put("/v1/admin/messaging-setting", headers=auth(admin_token), json={
        "farmer_reviewer_enabled": True, "reason": "Enable pilot messaging",
    }).json() == {"farmer_reviewer_enabled": True}
    assert api_client.put("/v1/admin/messaging-setting", headers=auth(farmer_token), json={
        "farmer_reviewer_enabled": False, "reason": "Unauthorized toggle attempt",
    }).status_code == 403
    available = api_client.get("/v1/messaging/reviewers", headers=auth(farmer_token))
    assert available.status_code == 200 and available.json()[0]["role_label"] == "CropPulse reviewer"
    assert "email" not in available.json()[0]

    first = api_client.post("/v1/messaging/conversations", headers=auth(farmer_token), json={"reviewer_id": reviewer_id})
    second = api_client.post("/v1/messaging/conversations", headers=auth(farmer_token), json={"reviewer_id": reviewer_id})
    assert first.status_code == 200 and first.json()["id"] == second.json()["id"]
    conversation_id = first.json()["id"]
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(outsider_token)).status_code == 404
    assert api_client.post(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token), json={
        "body": "Forged sender", "sender_id": reviewer_id,
    }).status_code == 422
    assert api_client.post(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token), json={
        "body": "x" * 4001,
    }).status_code == 422
    sent = api_client.post(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token), json={"body": "Hello reviewer"})
    assert sent.status_code == 201 and sent.json()["read_at"] is None
    sent_newer = api_client.post(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token), json={"body": "Second message"})
    assert sent_newer.status_code == 201
    listed = api_client.get("/v1/messaging/conversations", headers=auth(reviewer_token)).json()
    assert listed[0]["unread_count"] == 2
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages?offset=0&limit=1", headers=auth(reviewer_token)).json()["total"] == 2
    assert api_client.get("/v1/messaging/conversations", headers=auth(reviewer_token)).json()[0]["unread_count"] == 2
    assert api_client.post(f"/v1/messaging/conversations/{conversation_id}/read", headers=auth(reviewer_token), json={"message_ids": [sent_newer.json()["id"]]}).json()["marked_read"] == 1
    assert api_client.get("/v1/messaging/conversations", headers=auth(reviewer_token)).json()[0]["unread_count"] == 1
    farmer_history = api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token)).json()
    assert farmer_history["items"][0]["read_at"] is None
    assert farmer_history["items"][1]["read_at"] is not None
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(admin_token)).status_code == 404
    assert api_client.post(f"/v1/messaging/conversations/{conversation_id}/read", headers=auth(farmer_token), json={
        "message_ids": [sent.json()["id"]],
    }).json()["marked_read"] == 0

    with Session(get_engine()) as db:
        db.get(Farmer, reviewer_id).status = "suspended"
        db.commit()
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(reviewer_token)).status_code == 403
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token)).status_code == 404
    with Session(get_engine()) as db:
        db.get(Farmer, reviewer_id).status = "active"
        db.commit()

    with Session(get_engine()) as db:
        from backend.models import ReviewerDistrict
        db.query(ReviewerDistrict).filter_by(reviewer_id=reviewer_id).delete()
        db.commit()
    assert api_client.get(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token)).status_code == 404
    assert api_client.put("/v1/admin/messaging-setting", headers=auth(admin_token), json={
        "farmer_reviewer_enabled": False, "reason": "Disable pilot messaging",
    }).status_code == 200
    assert api_client.get("/v1/messaging/conversations", headers=auth(farmer_token)).status_code == 403
    assert api_client.post(f"/v1/messaging/conversations/{conversation_id}/messages", headers=auth(farmer_token), json={
        "body": "Disabled feature must block sending",
    }).status_code == 403


def test_private_messaging_rejects_invalid_message_and_unowned_conversation(api_client):
    farmer_token = register(api_client, "messaging-owner@example.com")
    stranger_token = register(api_client, "messaging-stranger@example.com")
    response = api_client.post("/v1/messaging/conversations/not-a-conversation/messages", headers=auth(farmer_token), json={"body": "   "})
    assert response.status_code == 422
    assert api_client.get("/v1/messaging/conversations/synthetic/messages", headers=auth(stranger_token)).status_code == 403


def test_account_change_clears_temporary_farmer_entries():
    from utils.frontend_services import SESSION_COLLECTIONS, clear_session_data
    state = {key: [{"owner": "previous-session"}] for key in SESSION_COLLECTIONS}
    state.update({f"{key}_next_id": 2 for key in SESSION_COLLECTIONS})
    state.update({"cp_plan": {"crop": "synthetic"}, "cp_saved_crop_plans": [{}], "keep": "language preference"})
    clear_session_data(state)
    assert state == {"keep": "language preference"}


def test_owner_scope_blocks_other_farmer_and_unauthorized_access(api_client):
    owner = register(api_client, "owner@example.com")
    other = register(api_client, "other@example.com")
    owner_profile = api_client.get("/v1/me", headers=auth(owner)).json()
    created = api_client.post("/v1/farms", headers=auth(owner), json={"name": "My farm", "district": "Huye", "area_ha": 1.5, "owner_id": "forged-owner"})
    assert created.status_code == 201
    assert created.json()["owner_id"] == owner_profile["id"]
    farm_id = created.json()["id"]
    assert api_client.get(f"/v1/farms/{farm_id}", headers=auth(other)).status_code == 404
    assert api_client.put(f"/v1/farms/{farm_id}", headers=auth(other), json={"name": "Stolen", "district": "Huye"}).status_code == 404
    assert api_client.delete(f"/v1/farms/{farm_id}", headers=auth(other)).status_code == 404
    assert api_client.post(f"/v1/farms/{farm_id}/plans", headers=auth(other), json={
        "district": "Huye", "crop": "Maize", "season": "A", "planting_date": "2026-02-01", "area_ha": 1.0, "plan": {}
    }).status_code == 404
    assert api_client.patch(f"/v1/farms/{farm_id}/plans/unknown/status", headers=auth(other), json={"status": "cancelled"}).status_code == 404
    activity = api_client.post(f"/v1/farms/{farm_id}/activities", headers=auth(owner), json={
        "district": "Huye", "crop": "Maize", "season": "A", "activity_type": "Planting",
        "event_date": "2026-02-01", "area_ha": 1.0, "quantity": None, "unit": None,
        "amount_rwf": None, "notes": "reported"
    })
    assert activity.status_code == 201
    assert activity.json()["verification"] == "user_reported"
    assert api_client.get(f"/v1/farms/{farm_id}/activities", headers=auth(other)).status_code == 404
    assert api_client.post(f"/v1/farms/{farm_id}/activities", headers=auth(other), json={
        "district": "Huye", "crop": "Maize", "season": "A", "activity_type": "Planting", "event_date": "2026-02-01"
    }).status_code == 404
    foreign_url = f"/v1/farms/{farm_id}/activities/{activity.json()['id']}"
    assert api_client.put(foreign_url, headers=auth(other), json={
        "district": "Huye", "crop": "Maize", "season": "A", "activity_type": "Harvest", "event_date": "2026-03-01"
    }).status_code == 404
    assert api_client.delete(foreign_url, headers=auth(other)).status_code == 404
    assert api_client.get(f"/v1/farms/{farm_id}/plans", headers=auth(other)).status_code == 404
    assert api_client.get(f"/v1/farms/{farm_id}/activities").status_code == 401
    assert api_client.get("/v1/farms", headers=auth(other)).json() == []


def test_validation_and_persistent_plan_and_activity(api_client):
    token = register(api_client)
    invalid_farm = api_client.post("/v1/farms", headers=auth(token), json={"name": "Farm", "district": "Atlantis"})
    assert invalid_farm.status_code == 422
    farm = api_client.post("/v1/farms", headers=auth(token), json={"name": "North plot", "district": "Musanze"}).json()
    invalid = api_client.post(f"/v1/farms/{farm['id']}/activities", headers=auth(token), json={
        "district": "Musanze", "crop": "Maize", "season": "Z", "activity_type": "Harvest", "event_date": "2026-05-01"
    })
    assert invalid.status_code == 422
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(token), json={
        "district": "Musanze", "crop": "Maize", "season": "A", "planting_date": "2026-09-20",
        "area_ha": 0.5, "plan": {"source": "provisional"}
    })
    assert plan.status_code == 201 and plan.json()["verification"] == "provisional"
    assert plan.json()["status"] == "planned" and plan.json()["actual_planting_date"] is None
    assert len(api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(token)).json()) == 1
    activities = api_client.get(f"/v1/farms/{farm['id']}/activities", headers=auth(token)).json()
    assert len(activities) == 1 and activities[0]["activity_type"] == "Seasonal plan"
    assert len(api_client.get("/v1/farms", headers=auth(token)).json()) == 1
    get_engine().dispose()
    _engine.cache_clear()
    assert len(api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(token)).json()) == 1


def test_plan_lifecycle_transitions_record_actual_planting_once_and_persist(api_client):
    token = register(api_client)
    farm = api_client.post("/v1/farms", headers=auth(token), json={"name": "Lifecycle farm", "district": "Huye"}).json()
    base = f"/v1/farms/{farm['id']}/plans"
    plan = api_client.post(base, headers=auth(token), json={
        "district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-09-15",
        "area_ha": 0.4, "plan": {"source": "provisional"}
    }).json()
    status_url = f"{base}/{plan['id']}/status"
    assert api_client.patch(status_url, headers=auth(token), json={"status": "planted"}).status_code == 422
    future = {"status": "planted", "actual_planting_date": (date.today() + timedelta(days=1)).isoformat()}
    assert api_client.patch(status_url, headers=auth(token), json=future).status_code == 422
    assert api_client.patch(status_url, headers=auth(token), json={"status": "monitoring"}).status_code == 409
    unchanged_plan = api_client.get(base, headers=auth(token)).json()[0]
    assert unchanged_plan["status"] == "planned" and unchanged_plan["actual_planting_date"] is None
    unchanged_activities = api_client.get(f"/v1/farms/{farm['id']}/activities", headers=auth(token)).json()
    assert not any(row["activity_type"] == "Planting" for row in unchanged_activities)

    planting = {"status": "planted", "actual_planting_date": "2026-09-20"}
    planted = api_client.patch(status_url, headers=auth(token), json=planting)
    assert planted.status_code == 200
    assert planted.json()["status"] == "planted" and planted.json()["actual_planting_date"] == "2026-09-20"
    # A retried identical transition is idempotent and does not duplicate the activity.
    assert api_client.patch(status_url, headers=auth(token), json=planting).status_code == 200
    activities = api_client.get(f"/v1/farms/{farm['id']}/activities", headers=auth(token)).json()
    planting_rows = [row for row in activities if row["activity_type"] == "Planting"]
    assert len(planting_rows) == 1
    assert planting_rows[0]["event_date"] == "2026-09-20"
    assert planting_rows[0]["area_ha"] is None and planting_rows[0]["verification"] == "user_reported"

    for status in ("monitoring", "harvesting", "completed"):
        response = api_client.patch(status_url, headers=auth(token), json={"status": status})
        assert response.status_code == 200 and response.json()["status"] == status
    assert api_client.patch(status_url, headers=auth(token), json={"status": "cancelled"}).status_code == 409
    get_engine().dispose()
    _engine.cache_clear()
    saved = api_client.get(base, headers=auth(token)).json()[0]
    assert saved["status"] == "completed" and saved["actual_planting_date"] == "2026-09-20"


def test_registration_requires_privacy_notice_acceptance(api_client):
    response = api_client.post("/v1/auth/register", json={
        "email": "no-consent@example.com", "password": "long-test-password-123", "display_name": "No Consent"
    })
    assert response.status_code == 422


def test_validation_errors_do_not_echo_submitted_secret(api_client):
    response = api_client.post("/v1/auth/register", json={
        "email": "safe@example.com", "password": "tiny-secret", "display_name": "Safe", "privacy_notice_accepted": True
    })
    assert response.status_code == 422
    assert "tiny-secret" not in response.text


def test_activity_update_delete_are_owner_scoped(api_client):
    token = register(api_client)
    farm = api_client.post("/v1/farms", headers=auth(token), json={"name": "Farm", "district": "Huye"}).json()
    activity = api_client.post(f"/v1/farms/{farm['id']}/activities", headers=auth(token), json={
        "district": "Huye", "crop": "Beans", "season": "B", "activity_type": "Harvest", "event_date": "2026-06-01"
    }).json()
    url = f"/v1/farms/{farm['id']}/activities/{activity['id']}"
    updated = api_client.put(url, headers=auth(token), json={
        "district": "Huye", "crop": "Beans", "season": "B", "activity_type": "Harvest", "event_date": "2026-06-02"
    })
    assert updated.status_code == 200 and updated.json()["event_date"] == "2026-06-02"
    assert api_client.delete(url, headers=auth(token)).status_code == 204
    assert api_client.get(f"/v1/farms/{farm['id']}/activities", headers=auth(token)).json() == []


def test_harvest_creation_validation_units_ownership_and_plan_linkage(api_client):
    owner = register(api_client, "harvest-owner@example.com")
    other = register(api_client, "harvest-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={
        "name": "Harvest farm", "district": "Huye", "area_ha": 1.0,
    }).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={
        "name": "North field", "area_ha": 0.8, "latitude": None, "longitude": None,
    }).json()
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(owner), json={
        "district": "Huye", "crop": "Maize", "season": "A", "planting_date": "2026-09-15",
        "area_ha": 0.8, "field_id": field["id"], "plan": {},
    }).json()
    endpoint = f"/v1/farms/{farm['id']}/harvests"
    payload = {
        "crop_plan_id": plan["id"], "crop": "Maize", "season": "A",
        "harvest_date": date.today().isoformat(), "harvested_area": 0.5, "area_unit": "ha",
        "quantity": 200, "quantity_unit": "kg", "loss_quantity": 10,
        "post_harvest_observations": "Some grain drying needed", "notes": None,
    }

    created = api_client.post(endpoint, headers=auth(owner), json=payload)
    assert created.status_code == 201
    result = created.json()
    assert result["field_id"] == field["id"] and result["crop_plan_id"] == plan["id"]
    assert result["yield_kg_ha"] == 400
    assert result["yield_calculation"] == "(200 kg x 1 kg/kg) / (0.5 ha x 1 ha/ha) = 400 kg/ha"
    assert result["loss_quantity"] == 10 and result["notes"] is None
    assert result["created_at"] and result["updated_at"]
    assert api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(owner)).json()[0]["status"] == "planned"

    assert api_client.get(endpoint, headers=auth(other)).status_code == 404
    assert api_client.post(endpoint, headers=auth(other), json=payload).status_code == 404
    assert api_client.put(f"{endpoint}/{result['id']}", headers=auth(other), json=payload).status_code == 404
    assert api_client.get(endpoint).status_code == 401

    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "harvested_area": 0}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={key: value for key, value in payload.items() if key != "harvested_area"}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={key: value for key, value in payload.items() if key != "quantity"}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "quantity_unit": "bushel"}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "quantity": 0}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "loss_quantity": -1}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={
        **payload, "harvest_date": (date.today() + timedelta(days=1)).isoformat()
    }).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "season": "B"}).status_code == 422
    assert api_client.post(endpoint, headers=auth(owner), json={**payload, "field_id": "foreign-field"}).status_code == 422
    assert len(api_client.get(endpoint, headers=auth(owner)).json()) == 1


def test_harvest_update_is_validated_and_persists_converted_yield(api_client):
    token = register(api_client, "harvest-update@example.com")
    farm = api_client.post("/v1/farms", headers=auth(token), json={
        "name": "Harvest update farm", "district": "Musanze",
    }).json()
    endpoint = f"/v1/farms/{farm['id']}/harvests"
    payload = {
        "crop": "Beans", "season": "B", "harvest_date": "2026-08-01",
        "harvested_area": 1, "area_unit": "acre", "quantity": 1, "quantity_unit": "t",
    }
    created = api_client.post(endpoint, headers=auth(token), json=payload)
    assert created.status_code == 201 and created.json()["yield_kg_ha"] == 2471.05
    harvest_id = created.json()["id"]
    changed = {**payload, "harvested_area": 10000, "area_unit": "m2", "quantity": 500, "quantity_unit": "kg",
               "loss_quantity": 25, "notes": "Corrected after weighing"}
    updated = api_client.put(f"{endpoint}/{harvest_id}", headers=auth(token), json=changed)
    assert updated.status_code == 200
    assert updated.json()["yield_kg_ha"] == 500
    assert updated.json()["notes"] == "Corrected after weighing"
    assert updated.json()["updated_at"]

    invalid = api_client.put(f"{endpoint}/{harvest_id}", headers=auth(token), json={**changed, "quantity": -1})
    assert invalid.status_code == 422
    saved = api_client.get(endpoint, headers=auth(token)).json()
    assert len(saved) == 1 and saved[0]["quantity"] == 500 and saved[0]["yield_kg_ha"] == 500


def test_harvest_must_use_crop_plan_crop_and_season(api_client):
    token = register(api_client, "harvest-plan-check@example.com")
    farm = api_client.post("/v1/farms", headers=auth(token), json={
        "name": "Plan check farm", "district": "Huye",
    }).json()
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(token), json={
        "district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-09-10",
        "area_ha": 0.5, "plan": {},
    }).json()
    response = api_client.post(f"/v1/farms/{farm['id']}/harvests", headers=auth(token), json={
        "crop_plan_id": plan["id"], "crop": "Maize", "season": "A", "harvest_date": "2026-10-01",
        "harvested_area": 0.5, "area_unit": "ha", "quantity": 100, "quantity_unit": "kg",
    })
    assert response.status_code == 422
    assert api_client.get(f"/v1/farms/{farm['id']}/harvests", headers=auth(token)).json() == []


def test_post_harvest_observations_are_persistent_validated_and_owner_scoped(api_client):
    owner = register(api_client, "post-harvest-owner@example.com")
    other = register(api_client, "post-harvest-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Storage notes", "district": "Huye"}).json()
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(owner), json={
        "district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-09-10",
        "area_ha": 0.5, "plan": {},
    }).json()
    harvests_url = f"/v1/farms/{farm['id']}/harvests"
    harvest_payload = {
        "crop_plan_id": plan["id"], "crop": "Beans", "season": "B", "harvest_date": (date.today() - timedelta(days=10)).isoformat(),
        "harvested_area": 0.5, "area_unit": "ha", "quantity": 200, "quantity_unit": "kg",
    }
    harvest = api_client.post(harvests_url, headers=auth(owner), json=harvest_payload).json()
    observations_url = f"{harvests_url}/{harvest['id']}/observations"
    body = {
        "observed_date": date.today().isoformat(), "storage_method": "Farmer-entered method",
        "storage_location": "Optional local description", "stored_quantity": 120, "stored_unit": "kg",
        "lost_quantity": 2, "lost_unit": "kg", "condition": "Observed condition only",
        "notes": "Synthetic note", "follow_up": "Synthetic follow-up",
    }

    created = api_client.post(observations_url, headers=auth(owner), json=body)
    assert created.status_code == 201, created.text
    observation = created.json()
    assert observation["harvest_id"] == harvest["id"]
    assert observation["stored_quantity"] == 120 and observation["lost_quantity"] == 2
    assert observation["created_at"] and observation["updated_at"]
    assert api_client.get(observations_url, headers=auth(owner)).json() == [observation]

    corrected_body = {**body, "observed_date": (date.today() - timedelta(days=1)).isoformat(),
                      "condition": "Corrected condition", "stored_quantity": 100}
    corrected = api_client.put(f"{observations_url}/{observation['id']}", headers=auth(owner), json=corrected_body)
    assert corrected.status_code == 200 and corrected.json()["condition"] == "Corrected condition"
    assert corrected.json()["stored_quantity"] == 100 and corrected.json()["updated_at"]

    # All descriptive and quantity fields are optional; missing never becomes zero.
    sparse = api_client.post(observations_url, headers=auth(owner), json={"observed_date": date.today().isoformat()})
    assert sparse.status_code == 201 and sparse.json()["stored_quantity"] is None and sparse.json()["lost_quantity"] is None
    assert sparse.json()["storage_method"] is None and sparse.json()["follow_up"] is None
    zero_recorded = api_client.post(observations_url, headers=auth(owner), json={
        "observed_date": date.today().isoformat(), "stored_quantity": 0, "stored_unit": "kg",
    })
    assert zero_recorded.status_code == 201 and zero_recorded.json()["stored_quantity"] == 0

    # Different units are retained independently; no implicit conversion/comparison is done.
    different_units = api_client.post(observations_url, headers=auth(owner), json={
        "observed_date": date.today().isoformat(), "stored_quantity": 1, "stored_unit": "t",
        "lost_quantity": 2, "lost_unit": "kg",
    })
    assert different_units.status_code == 201
    assert different_units.json()["stored_quantity"] == 1 and different_units.json()["stored_unit"] == "t"

    future = (date.today() + timedelta(days=1)).isoformat()
    for invalid in (
        {"observed_date": future},
        {"observed_date": (date.today() - timedelta(days=11)).isoformat()},
        {"observed_date": date.today().isoformat(), "stored_quantity": -1, "stored_unit": "kg"},
        {"observed_date": date.today().isoformat(), "stored_quantity": 1, "stored_unit": "bushel"},
        {"observed_date": date.today().isoformat(), "stored_quantity": 1},
        {"observed_date": date.today().isoformat(), "lost_quantity": -0.1, "lost_unit": "kg"},
        {"observed_date": date.today().isoformat(), "stored_quantity": 10, "stored_unit": "kg", "lost_quantity": 11, "lost_unit": "kg"},
    ):
        assert api_client.post(observations_url, headers=auth(owner), json=invalid).status_code == 422

    other_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Other", "district": "Huye"}).json()
    other_harvests = f"/v1/farms/{other_farm['id']}/harvests"
    assert api_client.get(observations_url, headers=auth(other)).status_code == 404
    assert api_client.post(observations_url, headers=auth(other), json=body).status_code == 404
    assert api_client.put(f"{observations_url}/{observation['id']}", headers=auth(other), json=body).status_code == 404
    assert api_client.get(f"{other_harvests}/{harvest['id']}/observations", headers=auth(other)).status_code == 404
    assert api_client.get(observations_url).status_code == 401

    saved_harvest = api_client.get(harvests_url, headers=auth(owner)).json()[0]
    saved_plan = api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(owner)).json()[0]
    assert saved_harvest["quantity"] == 200 and saved_harvest["yield_kg_ha"] == 400
    assert saved_plan["status"] == "planned"


def test_irrigation_records_are_persistent_owner_scoped_and_link_validated(api_client):
    owner = register(api_client, "irrigation-owner@example.com")
    other = register(api_client, "irrigation-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Water log", "district": "Huye"}).json()
    other_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Other water log", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={"name": "Upper plot"}).json()
    other_field = api_client.post(f"/v1/farms/{other_farm['id']}/fields", headers=auth(other), json={"name": "Other plot"}).json()
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(owner), json={
        "district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-09-10",
        "area_ha": 0.5, "field_id": field["id"], "plan": {},
    }).json()
    other_plan = api_client.post(f"/v1/farms/{other_farm['id']}/plans", headers=auth(other), json={
        "district": "Huye", "crop": "Beans", "season": "B", "planting_date": "2026-09-10",
        "area_ha": 0.5, "field_id": other_field["id"], "plan": {},
    }).json()
    harvest_url = f"/v1/farms/{farm['id']}/harvests"
    harvest = api_client.post(harvest_url, headers=auth(owner), json={
        "crop_plan_id": plan["id"], "crop": "Beans", "season": "B", "harvest_date": (date.today() - timedelta(days=5)).isoformat(),
        "harvested_area": 0.5, "area_unit": "ha", "quantity": 200, "quantity_unit": "kg",
    }).json()
    records_url = f"/v1/farms/{farm['id']}/irrigation-records"
    body = {
        "event_date": date.today().isoformat(), "field_id": field["id"], "crop_plan_id": plan["id"],
        "water_source": "well_borehole", "irrigation_method": "unknown",
        "water_quantity": 0, "water_quantity_unit": "L", "duration_value": 0, "duration_unit": "minutes",
        "purpose": "Farmer-entered observation", "notes": "No adequacy assessed.",
    }
    created = api_client.post(records_url, headers=auth(owner), json=body)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["verification"] == "farmer_reported"
    assert item["farm_id"] == farm["id"] and item["field_id"] == field["id"] and item["crop_plan_id"] == plan["id"]
    assert item["water_quantity"] == 0 and item["duration_value"] == 0
    assert item["created_at"] and item["updated_at"]
    # Each HTTP request obtains a fresh SQLAlchemy session, so this confirms persisted read-after-write.
    assert api_client.get(records_url, headers=auth(owner)).json() == [item]
    assert api_client.get(f"{records_url}/{item['id']}", headers=auth(owner)).json() == item

    corrected = api_client.put(f"{records_url}/{item['id']}", headers=auth(owner), json={
        "event_date": (date.today() - timedelta(days=1)).isoformat(), "field_id": field["id"],
        "crop_plan_id": plan["id"], "water_source": "other", "water_source_other": "Collected runoff",
        "irrigation_method": "other", "irrigation_method_other": "Gravity channel",
        "water_quantity": 1, "water_quantity_unit": "m3", "duration_value": None, "duration_unit": None,
        "purpose": None, "notes": None,
    })
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["water_source_other"] == "Collected runoff"
    assert corrected.json()["duration_value"] is None and corrected.json()["notes"] is None
    assert corrected.json()["updated_at"]

    # Farm-level crop plans can be recorded with field-specific irrigation, while field-scoped plans cannot point elsewhere.
    invalid_links = [
        {**body, "field_id": other_field["id"]},
        {**body, "crop_plan_id": other_plan["id"]},
        {**body, "field_id": other_field["id"], "crop_plan_id": plan["id"]},
    ]
    for invalid in invalid_links:
        assert api_client.post(records_url, headers=auth(owner), json=invalid).status_code in (404, 422)
        assert api_client.put(f"{records_url}/{item['id']}", headers=auth(owner), json=invalid).status_code in (404, 422)

    for invalid in (
        {**body, "event_date": (date.today() + timedelta(days=1)).isoformat()},
        {**body, "water_quantity": -1},
        {**body, "water_quantity_unit": None},
        {**body, "water_quantity_unit": "gallon"},
        {**body, "duration_value": 2, "duration_unit": None},
        {**body, "duration_value": -1},
        {**body, "duration_unit": "days"},
        {**body, "water_source": "other", "water_source_other": "  "},
        {**body, "water_source": "made_up"},
        {**body, "irrigation_method": "other", "irrigation_method_other": None},
    ):
        response = api_client.post(records_url, headers=auth(owner), json=invalid)
        assert response.status_code == 422, (invalid, response.json())
    sparse_created = api_client.post(records_url, headers=auth(owner), json={"event_date": date.today().isoformat()})
    assert sparse_created.status_code == 201
    sparse = sparse_created.json()
    assert sparse["water_quantity"] is None and sparse["duration_value"] is None
    assert sparse["water_source"] == "unknown" and sparse["irrigation_method"] == "unknown"

    # Unit values stay exactly as entered; no conversion or water adequacy inference is performed.
    distinct_units = api_client.post(records_url, headers=auth(owner), json={
        "event_date": date.today().isoformat(), "water_source": "rainwater", "irrigation_method": "manual",
        "water_quantity": 3, "water_quantity_unit": "L", "duration_value": 1, "duration_unit": "hours",
    })
    assert distinct_units.status_code == 201
    assert distinct_units.json()["water_quantity_unit"] == "L" and distinct_units.json()["duration_unit"] == "hours"

    assert api_client.get(records_url, headers=auth(other)).status_code == 404
    assert api_client.get(f"/v1/farms/not-a-farm/irrigation-records", headers=auth(owner)).status_code == 404
    assert api_client.post(records_url, headers=auth(other), json=body).status_code == 404
    assert api_client.put(f"{records_url}/{item['id']}", headers=auth(other), json=body).status_code == 404
    assert api_client.delete(f"{records_url}/{item['id']}", headers=auth(other)).status_code == 404
    assert api_client.get(f"{records_url}/not-a-record", headers=auth(owner)).status_code == 404
    assert api_client.get(f"{records_url}/{item['id']}", headers=auth(other)).status_code == 404
    assert api_client.delete(f"{records_url}/not-a-record", headers=auth(owner)).status_code == 404
    assert api_client.get(records_url).status_code == 401
    assert api_client.delete(f"{records_url}/{item['id']}", headers=auth(owner)).status_code == 204

    saved_harvest = api_client.get(harvest_url, headers=auth(owner)).json()[0]
    saved_plan = api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(owner)).json()[0]
    assert saved_harvest["id"] == harvest["id"] and saved_harvest["quantity"] == 200
    assert saved_plan["id"] == plan["id"] and saved_plan["status"] == "planned"


def test_soil_observations_are_persistent_correctable_and_owner_scoped(api_client):
    owner = register(api_client, "soil-observation-owner@example.com")
    other = register(api_client, "soil-observation-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Soil farm", "district": "Huye"}).json()
    other_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Other farm", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={"name": "Field A"}).json()
    other_field = api_client.post(f"/v1/farms/{other_farm['id']}/fields", headers=auth(other), json={"name": "Other field"}).json()
    endpoint = f"/v1/farms/{farm['id']}/soil-observations"
    body = {
        "field_id": field["id"], "observation_date": date.today().isoformat(),
        "soil_description": "Farmer-described dark soil", "drainage_observation": "Water stayed after rain",
        "erosion_observation": "Small visible channels", "management_practices": "Mulch observed",
        "notes": "No test results recorded.",
    }
    assert api_client.get(endpoint).status_code == 401
    created = api_client.post(endpoint, headers=auth(owner), json=body)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["verification"] == "farmer_reported" and item["field_id"] == field["id"]
    assert api_client.get(endpoint, headers=auth(owner)).json() == [item]
    assert api_client.get(f"{endpoint}/{item['id']}", headers=auth(owner)).json() == item

    corrected = {**body, "field_id": None, "soil_description": "Corrected farmer description", "notes": None}
    updated = api_client.put(f"{endpoint}/{item['id']}", headers=auth(owner), json=corrected)
    assert updated.status_code == 200 and updated.json()["soil_description"] == "Corrected farmer description"
    assert updated.json()["field_id"] is None and updated.json()["notes"] is None
    assert api_client.get(f"/v1/farms/{other_farm['id']}/soil-observations/{item['id']}", headers=auth(other)).status_code == 404
    assert api_client.get(endpoint, headers=auth(other)).status_code == 404
    assert api_client.get(f"{endpoint}/{item['id']}", headers=auth(other)).status_code == 404

    for invalid in (
        {**body, "observation_date": (date.today() + timedelta(days=1)).isoformat()},
        {**body, "field_id": other_field["id"]},
        {**body, "farmer_id": "attacker-chosen"},
    ):
        response = api_client.post(endpoint, headers=auth(owner), json=invalid)
        assert response.status_code in (404, 422), response.text
    sparse = api_client.post(endpoint, headers=auth(owner), json={"observation_date": date.today().isoformat()})
    assert sparse.status_code == 201, sparse.text
    assert sparse.json()["field_id"] is None and sparse.json()["soil_description"] is None
    assert sparse.json()["drainage_observation"] is None and sparse.json()["notes"] is None


def test_soil_test_records_validate_units_preserve_null_zero_and_existing_farm_data(api_client):
    owner = register(api_client, "soil-test-owner@example.com")
    other = register(api_client, "soil-test-other@example.com")
    farm = api_client.post("/v1/farms", headers=auth(owner), json={"name": "Test farm", "district": "Musanze"}).json()
    other_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Other test farm", "district": "Musanze"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=auth(owner), json={"name": "Plot"}).json()
    other_field = api_client.post(f"/v1/farms/{other_farm['id']}/fields", headers=auth(other), json={"name": "Foreign plot"}).json()
    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=auth(owner), json={
        "district": "Musanze", "crop": "Beans", "season": "A", "planting_date": "2026-09-10",
        "area_ha": 0.4, "field_id": field["id"], "plan": {},
    }).json()
    harvest_url = f"/v1/farms/{farm['id']}/harvests"
    harvest = api_client.post(harvest_url, headers=auth(owner), json={
        "crop_plan_id": plan["id"], "crop": "Beans", "season": "A",
        "harvest_date": (date.today() - timedelta(days=4)).isoformat(), "harvested_area": 0.4,
        "area_unit": "ha", "quantity": 40, "quantity_unit": "kg",
    }).json()
    harvest_observations_url = f"{harvest_url}/{harvest['id']}/observations"
    harvest_observation = api_client.post(harvest_observations_url, headers=auth(owner), json={
        "observed_date": date.today().isoformat(), "condition": "Synthetic existing observation",
    }).json()
    irrigation_url = f"/v1/farms/{farm['id']}/irrigation-records"
    irrigation = api_client.post(irrigation_url, headers=auth(owner), json={
        "event_date": date.today().isoformat(), "water_source": "unknown",
    }).json()
    plan_status_before = api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(owner)).json()[0]["status"]

    endpoint = f"/v1/farms/{farm['id']}/soil-tests"
    assert api_client.get(endpoint).status_code == 401
    sparse = api_client.post(endpoint, headers=auth(owner), json={"field_id": field["id"], "test_date": date.today().isoformat()})
    assert sparse.status_code == 201, sparse.text
    sparse_record = sparse.json()
    assert sparse_record["ph_value"] is None and sparse_record["nitrogen_value"] is None
    assert sparse_record["nitrogen_unit"] is None and sparse_record["organic_matter_value"] is None

    body = {
        "field_id": field["id"], "test_date": date.today().isoformat(), "ph_value": 0,
        "nitrogen_value": 0, "nitrogen_unit": "mg/kg", "phosphorus_value": 1.25, "phosphorus_unit": "g/kg",
        "potassium_value": 3, "potassium_unit": "cmol/kg", "organic_matter_value": 0,
        "organic_matter_unit": "%", "laboratory_name": "Farmer-entered provider", "report_reference": "REF-1",
        "source_details": "Transcribed from a paper report", "notes": "Synthetic test values.",
    }
    created = api_client.post(endpoint, headers=auth(owner), json=body)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["verification"] == "farmer_reported" and item["ph_value"] == 0
    assert item["nitrogen_value"] == 0 and item["organic_matter_value"] == 0
    assert item["nitrogen_unit"] == "mg/kg" and item["phosphorus_unit"] == "g/kg"
    assert api_client.get(endpoint, headers=auth(owner)).json() == [item, sparse_record]
    assert api_client.get(f"{endpoint}/{item['id']}", headers=auth(owner)).json() == item
    updated = api_client.put(f"{endpoint}/{item['id']}", headers=auth(owner), json={
        **body, "ph_value": 6.2, "nitrogen_value": None, "nitrogen_unit": None,
        "phosphorus_value": None, "phosphorus_unit": None, "potassium_value": None,
        "potassium_unit": None, "organic_matter_value": None, "organic_matter_unit": None,
    })
    assert updated.status_code == 200 and updated.json()["ph_value"] == 6.2
    assert updated.json()["nitrogen_value"] is None and updated.json()["nitrogen_unit"] is None
    assert api_client.get(f"/v1/farms/{other_farm['id']}/soil-tests/{item['id']}", headers=auth(other)).status_code == 404
    assert api_client.get(endpoint, headers=auth(other)).status_code == 404
    assert api_client.put(f"{endpoint}/{item['id']}", headers=auth(other), json=body).status_code == 404

    for invalid in (
        {**body, "test_date": (date.today() + timedelta(days=1)).isoformat()},
        {**body, "ph_value": 14.1}, {**body, "ph_value": -0.1}, {**body, "nitrogen_value": -1},
        {**body, "potassium_unit": "bushel"}, {**body, "organic_matter_unit": "mg/kg"},
        {**body, "nitrogen_unit": None}, {**body, "field_id": other_field["id"]},
        {**body, "farmer_id": "attacker-chosen"},
    ):
        response = api_client.post(endpoint, headers=auth(owner), json=invalid)
        assert response.status_code in (404, 422), (invalid, response.text)

    # Adding/correcting soil records does not rewrite other domain records or advance plan lifecycle.
    assert api_client.get(harvest_url, headers=auth(owner)).json()[0]["quantity"] == harvest["quantity"]
    assert api_client.get(harvest_observations_url, headers=auth(owner)).json()[0]["condition"] == "Synthetic existing observation"
    assert api_client.get(irrigation_url, headers=auth(owner)).json() == [irrigation]
    assert api_client.get(f"/v1/farms/{farm['id']}/plans", headers=auth(owner)).json()[0]["status"] == plan_status_before == "planned"


def test_farm_timeline_aggregates_existing_records_in_order_without_mutation_or_cross_farm_leak(api_client):
    owner = register(api_client, "timeline-owner@example.com")
    other = register(api_client, "timeline-other@example.com")
    headers = auth(owner)
    farm = api_client.post("/v1/farms", headers=headers, json={"name": "Timeline farm", "district": "Huye"}).json()
    second_farm = api_client.post("/v1/farms", headers=headers, json={"name": "Second timeline farm", "district": "Huye"}).json()
    foreign_farm = api_client.post("/v1/farms", headers=auth(other), json={"name": "Private farm", "district": "Huye"}).json()
    field = api_client.post(f"/v1/farms/{farm['id']}/fields", headers=headers, json={"name": "Upper field"}).json()

    plan = api_client.post(f"/v1/farms/{farm['id']}/plans", headers=headers, json={
        "district": "Huye", "crop": "Beans", "season": "A", "planting_date": "2025-09-01",
        "area_ha": 0.5, "field_id": field["id"], "plan": {},
    }).json()
    planted = api_client.patch(f"/v1/farms/{farm['id']}/plans/{plan['id']}/status", headers=headers, json={
        "status": "planted", "actual_planting_date": "2025-09-04",
    })
    assert planted.status_code == 200, planted.text
    activity = api_client.post(f"/v1/farms/{farm['id']}/activities", headers=headers, json={
        "district": "Huye", "crop": "Beans", "season": "A", "activity_type": "Weeding",
        "event_date": "2025-09-08", "quantity": None, "unit": None, "notes": "not surfaced",
    })
    assert activity.status_code == 201
    irrigation = api_client.post(f"/v1/farms/{farm['id']}/irrigation-records", headers=headers, json={
        "event_date": "2025-09-12", "field_id": field["id"], "water_source": "unknown",
    })
    assert irrigation.status_code == 201
    soil = api_client.post(f"/v1/farms/{farm['id']}/soil-observations", headers=headers, json={
        "field_id": field["id"], "observation_date": "2025-09-15", "soil_description": "Farmer described soil",
    })
    assert soil.status_code == 201
    soil_test = api_client.post(f"/v1/farms/{farm['id']}/soil-tests", headers=headers, json={
        "test_date": "2025-09-16", "ph_value": None,
    })
    assert soil_test.status_code == 201
    harvest_url = f"/v1/farms/{farm['id']}/harvests"
    harvest = api_client.post(harvest_url, headers=headers, json={
        "crop": "Beans", "season": "A", "harvest_date": "2025-12-01", "field_id": field["id"],
        "harvested_area": 0.5, "area_unit": "ha", "quantity": 50, "quantity_unit": "kg",
    })
    assert harvest.status_code == 201, harvest.text
    post_harvest_url = f"{harvest_url}/{harvest.json()['id']}/observations"
    post_harvest = api_client.post(post_harvest_url, headers=headers, json={
        "observed_date": "2025-12-03", "condition": "Farmer observed condition",
    })
    assert post_harvest.status_code == 201

    # A separate same-owner farm and a different owner's farm both remain outside this farm timeline.
    second_activity = api_client.post(f"/v1/farms/{second_farm['id']}/activities", headers=headers, json={
        "district": "Huye", "crop": "Beans", "season": "A", "activity_type": "Other farm event", "event_date": "2025-12-04",
    })
    foreign_activity = api_client.post(f"/v1/farms/{foreign_farm['id']}/activities", headers=auth(other), json={
        "district": "Huye", "crop": "Beans", "season": "A", "activity_type": "Private event", "event_date": "2025-12-05",
    })
    assert second_activity.status_code == foreign_activity.status_code == 201

    before = {
        "plans": api_client.get(f"/v1/farms/{farm['id']}/plans", headers=headers).json(),
        "activities": api_client.get(f"/v1/farms/{farm['id']}/activities", headers=headers).json(),
        "harvests": api_client.get(harvest_url, headers=headers).json(),
        "irrigation": api_client.get(f"/v1/farms/{farm['id']}/irrigation-records", headers=headers).json(),
        "soil": api_client.get(f"/v1/farms/{farm['id']}/soil-observations", headers=headers).json(),
        "soil_tests": api_client.get(f"/v1/farms/{farm['id']}/soil-tests", headers=headers).json(),
        "post_harvest": api_client.get(post_harvest_url, headers=headers).json(),
    }
    endpoint = f"/v1/farms/{farm['id']}/timeline"
    assert api_client.get(endpoint).status_code == 401
    response = api_client.get(endpoint, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["has_more"] is False
    entries = body["entries"]
    assert {row["event_type"] for row in entries} == {
        "crop_plan_created", "planting_recorded", "activity", "irrigation", "soil_observation",
        "soil_test", "harvest", "post_harvest_observation",
    }
    assert sum(row["event_type"] == "planting_recorded" and row["event_date"] == "2025-09-04" for row in entries) == 1
    assert not any(row["event_type"] == "activity" and row["description"].startswith("Planting recorded for Beans") for row in entries)
    dates = [row["event_date"] for row in entries if row["event_date"] is not None]
    assert dates == sorted(dates, reverse=True)
    assert all(row["farm_id"] == farm["id"] and row["farm_name"] == farm["name"] for row in entries)
    assert all(row["field_name"] == "Upper field" for row in entries if row["field_id"] == field["id"])
    assert any(row["source_label"] == "Farmer reported" for row in entries)
    assert any(row["source_label"] == "Farmer entered; source not independently verified" for row in entries)
    assert any(row["href"] == "#soil-records-title" for row in entries)
    assert any("Farmer described soil" in row["description"] for row in entries)
    assert not any("not surfaced" in row["description"] or "Private event" in row["description"] or "Other farm event" in row["description"] for row in entries)
    assert api_client.get(f"/v1/farms/{foreign_farm['id']}/timeline", headers=headers).status_code == 404
    assert api_client.get(f"/v1/farms/{farm['id']}/timeline?limit=0", headers=headers).status_code == 422
    bounded = api_client.get(f"{endpoint}?limit=1", headers=headers).json()
    assert len(bounded["entries"]) == 1 and bounded["has_more"] is True

    after = {
        "plans": api_client.get(f"/v1/farms/{farm['id']}/plans", headers=headers).json(),
        "activities": api_client.get(f"/v1/farms/{farm['id']}/activities", headers=headers).json(),
        "harvests": api_client.get(harvest_url, headers=headers).json(),
        "irrigation": api_client.get(f"/v1/farms/{farm['id']}/irrigation-records", headers=headers).json(),
        "soil": api_client.get(f"/v1/farms/{farm['id']}/soil-observations", headers=headers).json(),
        "soil_tests": api_client.get(f"/v1/farms/{farm['id']}/soil-tests", headers=headers).json(),
        "post_harvest": api_client.get(post_harvest_url, headers=headers).json(),
    }
    assert after == before

