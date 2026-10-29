"""Security and role checks for the additive React/browser API surface."""
from sqlalchemy import select
from sqlalchemy.orm import Session
import pytest
import jwt
from urllib.parse import parse_qs, urlsplit

from backend.api import app
from backend.db import get_engine
from backend.models import AdminAuditEvent, ActivityReviewDecision, Farmer, Farm, FarmActivity, ReviewerDistrict, AccountActionToken, AgronomyRuleDecision, AgronomyRuleProposal, AgronomyReviewAuthorizationEvent
from fastapi.testclient import TestClient

from test_backend_api import api_client, auth, register


def make_role(email, role):
    with Session(get_engine()) as db:
        farmer = db.scalar(select(Farmer).where(Farmer.email == email))
        farmer.role = role
        db.commit()
        return farmer.id


def test_browser_auth_cookie_refresh_csrf_and_logout(api_client):
    register(api_client, "browser@example.com")
    csrf = api_client.get("/v1/browser-auth/csrf", headers={"Origin": "http://127.0.0.1:5173"})
    assert csrf.status_code == 200
    assert csrf.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    assert csrf.headers["cache-control"] == "no-store"
    token = csrf.json()["csrf_token"]
    assert api_client.cookies.get("cp_csrf") == token and len(token) > 32
    invalid_login = api_client.post("/v1/browser-auth/login", json={
        "email": "browser@example.com", "password": "invalid-password"
    }, headers={"X-CSRF-Token": token})
    assert invalid_login.status_code == 401
    login = api_client.post("/v1/browser-auth/login", json={
        "email": "browser@example.com", "password": "long-test-password-123"
    }, headers={"X-CSRF-Token": token})
    assert login.status_code == 200
    assert "access_token" not in login.json()
    cookie = login.cookies.get("cp_session")
    assert cookie
    set_cookie = login.headers["set-cookie"].lower()
    assert "httponly" in set_cookie and "samesite=lax" in set_cookie and "max-age=1800" in set_cookie
    api_client.cookies.delete("cp_csrf", path="/v1")
    api_client.cookies.set("cp_csrf", "forged-token", path="/v1")
    request = api_client.build_request("POST", "/v1/farms", headers={"X-CSRF-Token": "forged-token"})
    assert "authorization" not in request.headers
    assert "cp_csrf=forged-token" in request.headers.get("cookie", "")
    forged = api_client.post("/v1/farms", json={"name": "Forged", "district": "Huye"},
                             headers={"X-CSRF-Token": "forged-token"})
    assert forged.status_code == 403
    api_client.cookies.delete("cp_csrf", path="/v1")
    api_client.cookies.set("cp_csrf", token, path="/v1")
    assert login.json()["role"] == "farmer"
    assert api_client.get("/v1/me").status_code == 200  # cookie persists across requests/refresh
    assert api_client.post("/v1/farms", json={"name": "Blocked", "district": "Huye"}).status_code == 403
    created = api_client.post("/v1/farms", json={"name": "Browser farm", "district": "Huye"},
                              headers={"X-CSRF-Token": token})
    assert created.status_code == 201
    logout_no_csrf = api_client.post("/v1/browser-auth/logout")
    assert logout_no_csrf.status_code == 403
    logout = api_client.post("/v1/browser-auth/logout", headers={"X-CSRF-Token": token})
    assert logout.status_code == 204
    assert api_client.get("/v1/me").status_code == 401


def test_api_startup_fails_clearly_when_signing_key_is_missing_or_insecure(monkeypatch):
    import asyncio
    import backend.api as api_module

    async def start_api():
        async with api_module.lifespan(api_module.app):
            pass

    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    invalid_keys = [None, "short", "x" * 48, "replace-with-a-random-secret-at-least-32-characters"]
    for value in invalid_keys:
        if value is None:
            monkeypatch.delenv("CROP_PULSE_SECRET_KEY", raising=False)
        else:
            monkeypatch.setenv("CROP_PULSE_SECRET_KEY", value)
        with pytest.raises(RuntimeError, match="CROP_PULSE_SECRET_KEY"):
            asyncio.run(start_api())
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "test-only-secret-key-of-at-least-32-characters")
    with pytest.raises(RuntimeError, match="CROP_PULSE_SECRET_KEY"):
        asyncio.run(start_api())


def test_startup_requires_explicit_environment_and_secure_production_configuration(monkeypatch):
    import asyncio
    import backend.api as api_module

    async def start_api():
        async with api_module.lifespan(api_module.app):
            pass

    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "test-only-secret-key-of-at-least-32-characters")
    monkeypatch.delenv("CROP_PULSE_ENVIRONMENT", raising=False)
    with pytest.raises(RuntimeError, match="CROP_PULSE_ENVIRONMENT"):
        asyncio.run(start_api())

    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    monkeypatch.setenv("CROP_PULSE_CORS_ORIGINS", "https://app.example.test")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "production-signing-secret-with-enough-entropy-839201")
    for setting, value in (("CROP_PULSE_COOKIE_SECURE", "0"),
                           ("CROP_PULSE_CORS_ORIGINS", "*"),
                           ("CROP_PULSE_CORS_ORIGINS", "https://*.example.test"),
                           ("CROP_PULSE_CORS_ORIGINS", "http://app.example.test"),
                           ("CROP_PULSE_AUTO_CREATE_SCHEMA", "1")):
        monkeypatch.setenv("CROP_PULSE_CORS_ORIGINS", "https://app.example.test")
        monkeypatch.delenv("CROP_PULSE_COOKIE_SECURE", raising=False)
        monkeypatch.setenv("CROP_PULSE_AUTO_CREATE_SCHEMA", "0")
        monkeypatch.setenv(setting, value)
        with pytest.raises(RuntimeError):
            asyncio.run(start_api())
    monkeypatch.setenv("CROP_PULSE_CORS_ORIGINS", "https://app.example.test")
    monkeypatch.setenv("CROP_PULSE_COOKIE_SECURE", "0")
    assert api_module._cookie_secure() is True

    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "staging")
    monkeypatch.setenv("CROP_PULSE_SECRET_KEY", "test-only-secret-key-of-at-least-32-characters")
    monkeypatch.setenv("CROP_PULSE_CORS_ORIGINS", "https://app.example.test")
    with pytest.raises(RuntimeError, match="CROP_PULSE_SECRET_KEY"):
        asyncio.run(start_api())


def test_api_rejects_oversized_body_before_json_or_multipart_parsing(api_client):
    too_large = b"x" * (8 * 1024 * 1024 + 1)
    response = api_client.post("/v1/auth/login", content=too_large,
                               headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body is too large."}
    get_with_body = api_client.request("GET", "/health", content=too_large)
    assert get_with_body.status_code == 413


def test_request_body_middleware_limits_chunked_body_without_content_length():
    import asyncio
    from backend.api import RequestBodyLimitMiddleware

    incoming = [
        {"type": "http.request", "body": b"1234", "more_body": True},
        {"type": "http.request", "body": b"5678", "more_body": True},
        {"type": "http.request", "body": b"9", "more_body": False},
    ]
    sent = []

    async def receive():
        return incoming.pop(0)

    async def send(message):
        sent.append(message)

    async def app(_scope, _receive, _send):
        raise AssertionError("Oversized request reached the application.")

    middleware = RequestBodyLimitMiddleware(app, max_body_bytes=8)
    asyncio.run(middleware({"type": "http", "method": "POST", "headers": []}, receive, send))
    assert sent[0]["status"] == 413


def test_browser_registration_sets_http_only_session_and_never_returns_token(api_client):
    csrf = api_client.get("/v1/browser-auth/csrf").json()["csrf_token"]
    response = api_client.post("/v1/browser-auth/register", headers={"X-CSRF-Token": csrf}, json={
        "email": "new-browser@example.com", "password": "long-test-password-123",
        "display_name": "New Browser Farmer", "privacy_notice_accepted": True,
    })
    assert response.status_code == 201
    assert response.json()["role"] == "farmer"
    assert "access_token" not in response.json()
    assert "httponly" in response.headers["set-cookie"].lower()
    assert api_client.get("/v1/me").status_code == 200


def test_streamlit_handoff_exchange_succeeds_with_sqlite_datetime_values(api_client):
    csrf = api_client.get("/v1/browser-auth/csrf").json()["csrf_token"]
    registration = api_client.post("/v1/browser-auth/register", headers={"X-CSRF-Token": csrf}, json={
        "email": "streamlit-handoff@example.com", "password": "long-test-password-123",
        "display_name": "Handoff Farmer", "privacy_notice_accepted": True,
    })
    assert registration.status_code == 201

    created = api_client.post("/v1/browser-auth/streamlit-handoff", headers={"X-CSRF-Token": csrf})
    assert created.status_code == 200
    handoff_code = parse_qs(urlsplit(created.json()["redirect_url"]).query)["cp_handoff"][0]

    exchanged = api_client.post("/v1/streamlit/handoff/exchange", json={"code": handoff_code})
    assert exchanged.status_code == 200
    assert exchanged.json()["token_type"] == "bearer"
    assert api_client.get("/v1/me", headers={"Authorization": f"Bearer {exchanged.json()['access_token']}"}).status_code == 200
    assert api_client.post("/v1/streamlit/handoff/exchange", json={"code": handoff_code}).status_code == 401


def test_streamlit_to_react_handoff_preserves_admin_role_and_sets_browser_cookie(api_client):
    token = register(api_client, "streamlit-admin@example.com")
    make_role("streamlit-admin@example.com", "admin")
    created = api_client.post("/v1/streamlit/react-handoff", headers=auth(token))
    assert created.status_code == 200
    redirect = urlsplit(created.json()["redirect_url"])
    code = parse_qs(redirect.query)["cp_handoff"][0]
    assert redirect.path.endswith("/overview")

    csrf = api_client.get("/v1/browser-auth/csrf").json()["csrf_token"]
    exchanged = api_client.post("/v1/browser-auth/react-handoff/exchange", headers={"X-CSRF-Token": csrf},
                                json={"code": code})
    assert exchanged.status_code == 200
    assert exchanged.json()["role"] == "admin"
    assert "access_token" not in exchanged.json()
    assert "cp_session=" in exchanged.headers["set-cookie"]
    assert "Path=/;" in exchanged.headers["set-cookie"] and "HttpOnly" in exchanged.headers["set-cookie"]
    assert api_client.get("/v1/me").json()["role"] == "admin"
    assert api_client.post("/v1/browser-auth/react-handoff/exchange", headers={"X-CSRF-Token": csrf},
                           json={"code": code}).status_code == 401


def test_browser_auth_rejects_expired_and_malformed_credentials(api_client):
    register(api_client, "expiry@example.com")
    expired = jwt.encode({"sub": "no-account", "exp": 1, "jti": "expired"},
                         "test-only-secret-key-of-at-least-32-characters", algorithm="HS256")
    api_client.cookies.set("cp_session", expired, path="/v1")
    assert api_client.get("/v1/me").status_code == 401
    api_client.cookies.set("cp_session", "malformed.token.value", path="/v1")
    assert api_client.get("/v1/me").status_code == 401


def test_self_assignment_and_non_admin_routes_are_denied(api_client):
    token = register(api_client, "ordinary@example.com")
    me = api_client.get("/v1/me", headers=auth(token)).json()
    assert me["role"] == "farmer"
    self_escalation = api_client.post("/v1/auth/register", json={
        "email": "attacker@example.com", "password": "long-test-password-123",
        "display_name": "Attacker", "privacy_notice_accepted": True, "role": "admin"
    })
    assert self_escalation.status_code == 422
    assert api_client.get("/v1/admin/overview", headers=auth(token)).status_code == 403
    assert api_client.get("/v1/admin/farmers", headers=auth(token)).status_code == 403
    assert api_client.get("/v1/reviewer/activities", headers=auth(token)).status_code == 403


def test_react_nisr_statistics_requires_login_and_serves_filtered_provenance(api_client, monkeypatch):
    import pandas as pd
    import backend.api as api_module

    token = register(api_client, "statistics@example.com")
    frame = pd.DataFrame([
        {"district": "Huye", "crop": "Maize", "season": "A", "year": 2025,
         "area_ha": 100.0, "production_t": 200.0, "yield_t_ha": 2.0},
        {"district": "Karongi", "crop": "Beans", "season": "B", "year": 2024,
         "area_ha": 50.0, "production_t": 40.0, "yield_t_ha": 0.8},
    ])
    provenance = {"publisher": "National Institute of Statistics of Rwanda (NISR)", "title": "NISR SAS test",
                  "source_url": "https://statistics.gov.rw/test", "reference_period": "2024-2025",
                  "retrieved_at": "2026-10-21", "units": "area ha; production tonnes", "limitations": "Aggregate only."}
    monkeypatch.setattr(api_module, "load_data", lambda: (frame, {
        "state": "validated", "provenance": [provenance],
        "geography": {"n_valid": 2, "missing_districts": [], "coverage_label": "Partial"},
    }))

    assert api_client.get("/v1/agricultural-statistics/nisr").status_code == 401
    response = api_client.get("/v1/agricultural-statistics/nisr?year=2025&district=Huye", headers=auth(token))
    assert response.status_code == 200
    body = response.json()
    assert body["publisher"] == provenance["publisher"]
    assert body["records"] == [{"district": "Huye", "crop": "Maize", "season": "A", "year": 2025,
                                "area_ha": 100.0, "production_t": 200.0, "yield_t_ha": 2.0}]
    assert body["coverage"]["n_valid"] == 2
    assert api_client.get("/v1/agricultural-statistics/nisr?season=D", headers=auth(token)).status_code == 422


def test_react_nisr_statistics_never_serves_demo_data(api_client, monkeypatch):
    import pandas as pd
    import backend.api as api_module

    token = register(api_client, "no-statistics@example.com")
    monkeypatch.setattr(api_module, "load_data", lambda: (pd.DataFrame(), {"state": "demo", "provenance": []}))
    response = api_client.get("/v1/agricultural-statistics/nisr", headers=auth(token))
    assert response.status_code == 503


def test_failed_password_attempts_are_rate_limited(api_client):
    register(api_client, "throttle@example.com")
    for _ in range(8):
        response = api_client.post("/v1/auth/login", json={"email": "throttle@example.com", "password": "incorrect-password"})
        assert response.status_code == 401
    limited = api_client.post("/v1/auth/login", json={"email": "throttle@example.com", "password": "incorrect-password"})
    assert limited.status_code == 429
    assert limited.headers.get("retry-after") == "900"


def test_cors_and_security_headers(api_client):
    allowed = api_client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert allowed.headers.get("access-control-allow-credentials") == "true"
    assert allowed.headers.get("x-content-type-options") == "nosniff"
    assert allowed.headers.get("x-frame-options") == "DENY"
    assert allowed.headers.get("referrer-policy") == "no-referrer"
    blocked = api_client.options("/v1/browser-auth/login", headers={
        "Origin": "https://untrusted.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-csrf-token",
    })
    assert "access-control-allow-origin" not in blocked.headers


def _enable_test_mail(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("CROP_PULSE_SMTP_FROM", "CropPulse <no-reply@example.test>")
    monkeypatch.setenv("CROP_PULSE_PUBLIC_APP_URL", "http://127.0.0.1:5173")
    sent = []
    monkeypatch.setattr("backend.account_mail.send_account_email", lambda recipient, subject, text: sent.append((recipient, subject, text)))
    return sent


def _browser_sign_in(api_client, email):
    csrf = api_client.get("/v1/browser-auth/csrf").json()["csrf_token"]
    response = api_client.post("/v1/browser-auth/login", headers={"X-CSRF-Token": csrf}, json={
        "email": email, "password": "long-test-password-123",
    })
    assert response.status_code == 200
    return csrf


def _link_token(message):
    import re
    match = re.search(r"\?token=([A-Za-z0-9_-]+)", message)
    assert match
    return match.group(1)


def test_email_change_requires_confirmation_and_revokes_sessions(api_client, monkeypatch):
    register(api_client, "change-old@example.com")
    csrf = _browser_sign_in(api_client, "change-old@example.com")
    sent = _enable_test_mail(monkeypatch)
    requested = api_client.post("/v1/browser-auth/email-change", headers={"X-CSRF-Token": csrf}, json={
        "current_password": "long-test-password-123", "new_email": "change-new@example.com",
    })
    assert requested.status_code == 202 and sent[0][0] == "change-new@example.com"
    assert api_client.get("/v1/me").json()["email"] == "change-old@example.com"
    token = _link_token(sent[0][2])
    with Session(get_engine()) as db:
        action = db.scalar(select(AccountActionToken).where(AccountActionToken.purpose == "email_change"))
        assert action.token_hash != token and action.target_email == "change-new@example.com"
    confirmed = api_client.post("/v1/browser-auth/email-change/confirm", json={"token": token})
    assert confirmed.status_code == 200
    assert api_client.get("/v1/me").status_code == 401
    assert api_client.post("/v1/browser-auth/email-change/confirm", json={"token": token}).status_code == 400
    assert api_client.post("/v1/auth/login", json={"email": "change-new@example.com", "password": "long-test-password-123"}).status_code == 200
    assert api_client.post("/v1/auth/login", json={"email": "change-old@example.com", "password": "long-test-password-123"}).status_code == 401


def test_password_recovery_is_private_single_use_and_revokes_sessions(api_client, monkeypatch):
    register(api_client, "recover@example.com")
    _browser_sign_in(api_client, "recover@example.com")
    sent = _enable_test_mail(monkeypatch)
    existing = api_client.post("/v1/browser-auth/password-recovery", json={"email": "recover@example.com"})
    unknown = api_client.post("/v1/browser-auth/password-recovery", json={"email": "unknown@example.com"})
    assert existing.status_code == unknown.status_code == 202
    assert existing.json() == unknown.json() and len(sent) == 1
    token = _link_token(sent[0][2])
    reset = api_client.post("/v1/browser-auth/password-reset/complete", json={
        "token": token, "new_password": "new-long-password-456",
    })
    assert reset.status_code == 200 and api_client.get("/v1/me").status_code == 401
    assert api_client.post("/v1/browser-auth/password-reset/complete", json={
        "token": token, "new_password": "another-long-password-789",
    }).status_code == 400
    assert api_client.post("/v1/auth/login", json={"email": "recover@example.com", "password": "long-test-password-123"}).status_code == 401
    assert api_client.post("/v1/auth/login", json={"email": "recover@example.com", "password": "new-long-password-456"}).status_code == 200


def test_self_service_deletion_cascades_farmer_data_and_anonymizes_review_history(api_client):
    token = register(api_client, "deleting-reviewer@example.com")
    reviewer = api_client.get("/v1/me", headers=auth(token)).json()
    with Session(get_engine()) as db:
        account = db.get(Farmer, reviewer["id"])
        account.role = "reviewer"
        db.commit()
    own_farm = api_client.post("/v1/farms", headers=auth(token), json={"name": "Own farm", "district": "Huye"}).json()
    reporter_token = register(api_client, "reporter-for-deletion-test@example.com")
    report_farm = api_client.post("/v1/farms", headers=auth(reporter_token), json={"name": "Report farm", "district": "Huye"}).json()
    activity = api_client.post(f"/v1/farms/{report_farm['id']}/activities", headers=auth(reporter_token), json={
        "district": "Huye", "crop": "Beans", "season": "B", "activity_type": "Harvest", "event_date": "2026-10-01",
    }).json()
    with Session(get_engine()) as db:
        db.add(ActivityReviewDecision(activity_id=activity["id"], reviewer_id=reviewer["id"], decision="approved_as_reviewed", reason="Synthetic test decision"))
        db.commit()
    csrf = _browser_sign_in(api_client, "deleting-reviewer@example.com")
    deleted = api_client.request("DELETE", "/v1/browser-auth/account", headers={"X-CSRF-Token": csrf}, json={
        "current_password": "long-test-password-123", "confirmation": "DELETE",
    })
    assert deleted.status_code == 204
    assert api_client.get("/v1/me").status_code == 401
    with Session(get_engine()) as db:
        assert db.get(Farmer, reviewer["id"]) is None
        assert db.get(Farm, own_farm["id"]) is None
        preserved = db.scalar(select(ActivityReviewDecision).where(ActivityReviewDecision.activity_id == activity["id"]))
        assert preserved is not None and preserved.reviewer_id is None
        assert db.scalar(select(AdminAuditEvent).where(AdminAuditEvent.action == "self_service_account_deleted")) is not None


def test_last_admin_cannot_delete_own_account(api_client):
    token = register(api_client, "last-admin@example.com")
    make_role("last-admin@example.com", "admin")
    response = api_client.request("DELETE", "/v1/browser-auth/account", headers=auth(token), json={
        "current_password": "long-test-password-123", "confirmation": "DELETE",
    })
    assert response.status_code == 409
    assert api_client.get("/v1/me", headers=auth(token)).status_code == 200


def test_first_admin_is_only_provisioned_by_explicit_operator_command(api_client, monkeypatch):
    register(api_client, "initial-admin@example.com")
    monkeypatch.setattr("builtins.input", lambda _prompt: "initial-admin@example.com")
    from backend.admin_cli import promote_first_admin
    promote_first_admin("initial-admin@example.com")
    with Session(get_engine()) as db:
        account = db.scalar(select(Farmer).where(Farmer.email == "initial-admin@example.com"))
        assert account.role == "admin"
        assert db.scalar(select(AdminAuditEvent).where(AdminAuditEvent.action == "first_admin_provisioned")) is not None
    with pytest.raises(SystemExit, match="An administrator already exists"):
        promote_first_admin("initial-admin@example.com")


def test_admin_account_actions_revoke_sessions_and_audit(api_client):
    admin_token = register(api_client, "admin@example.com")
    admin_id = make_role("admin@example.com", "admin")
    target_token = register(api_client, "target@example.com")
    target = api_client.get("/v1/me", headers=auth(target_token)).json()
    farm = api_client.post("/v1/farms", headers=auth(target_token), json={"name": "Target farm", "district": "Huye"}).json()
    overview = api_client.get("/v1/admin/overview", headers=auth(admin_token))
    assert overview.status_code == 200
    assert overview.json()["accounts"]["total"] == 2
    assert overview.json()["farms"] == 1
    listed = api_client.get("/v1/admin/farmers?q=target", headers=auth(admin_token))
    assert listed.status_code == 200 and listed.json()[0]["email"] == "target@example.com"
    assert listed.json()[0]["farm_count"] == 1
    suspended = api_client.patch(f"/v1/admin/farmers/{target['id']}/status", headers=auth(admin_token),
                                 json={"status": "suspended", "reason": "User requested account suspension"})
    assert suspended.status_code == 200
    # Suspension revokes every active session, so the old token is rejected before
    # the account-status check can return 403.
    assert api_client.get("/v1/farms", headers=auth(target_token)).status_code == 401
    assert api_client.post("/v1/auth/login", json={"email": "target@example.com", "password": "long-test-password-123"}).status_code == 403
    audit = api_client.get("/v1/admin/audit-events", headers=auth(admin_token))
    assert audit.status_code == 200
    assert any(item["action"] == "account_suspended" and item["target_farmer_id"] == target["id"] for item in audit.json())
    assert db_has_revoked_sessions(target["id"])
    assert admin_id != target["id"] and farm["owner_id"] == target["id"]


def db_has_revoked_sessions(farmer_id):
    from backend.models import FarmerSession
    with Session(get_engine()) as db:
        sessions = db.scalars(select(FarmerSession).where(FarmerSession.farmer_id == farmer_id)).all()
        return bool(sessions) and all(row.revoked_at is not None for row in sessions)


def test_reviewer_is_limited_to_assigned_district_and_reviews_are_immutable(api_client):
    admin_token = register(api_client, "admin2@example.com")
    make_role("admin2@example.com", "admin")
    farmer_token = register(api_client, "reporter@example.com")
    huye = api_client.post("/v1/farms", headers=auth(farmer_token), json={"name": "Huye plot", "district": "Huye"}).json()
    musanze = api_client.post("/v1/farms", headers=auth(farmer_token), json={"name": "Musanze plot", "district": "Musanze"}).json()
    payload = {"district": "Huye", "crop": "Maize", "season": "A", "activity_type": "Harvest",
               "event_date": "2026-08-01", "quantity": 90, "unit": "kg", "notes": "Farmer report"}
    activity = api_client.post(f"/v1/farms/{huye['id']}/activities", headers=auth(farmer_token), json=payload).json()
    outside = {**payload, "district": "Musanze"}
    outside_activity = api_client.post(f"/v1/farms/{musanze['id']}/activities", headers=auth(farmer_token), json=outside).json()
    reviewer_token = register(api_client, "reviewer@example.com")
    reviewer_id = make_role("reviewer@example.com", "reviewer")
    assignment = api_client.patch(f"/v1/admin/farmers/{reviewer_id}/permissions", headers=auth(admin_token),
                                  json={"role": "reviewer", "districts": ["Huye"], "reason": "Assigned Huye review work"})
    assert assignment.status_code == 200
    assert api_client.patch(f"/v1/admin/farmers/{reviewer_id}/permissions", headers=auth(admin_token),
                            json={"role": "reviewer", "districts": [], "reason": "Remove all reviewer scope"}).status_code == 422
    queue = api_client.get("/v1/reviewer/activities", headers=auth(reviewer_token))
    assert queue.status_code == 200
    assert [row["id"] for row in queue.json()] == [activity["id"]]
    assert api_client.get("/v1/reviewer/activities?district=Musanze", headers=auth(reviewer_token)).status_code == 403
    assert api_client.post(f"/v1/reviewer/activities/{outside_activity['id']}/decisions", headers=auth(reviewer_token),
                           json={"decision": "approved_as_reviewed", "reason": "Outside assigned area"}).status_code == 404
    assert api_client.post(f"/v1/reviewer/activities/{activity['id']}/decisions", headers=auth(farmer_token),
                           json={"decision": "approved_as_reviewed", "reason": "Farmer cannot self-approve"}).status_code == 403
    assert api_client.put(f"/v1/farms/{huye['id']}/activities/{activity['id']}", headers=auth(reviewer_token),
                          json={**payload, "notes": "Reviewer attempted to alter farmer data"}).status_code == 404
    decision = api_client.post(f"/v1/reviewer/activities/{activity['id']}/decisions", headers=auth(reviewer_token),
                               json={"decision": "correction_requested", "reason": "Please clarify the harvest unit"})
    assert decision.status_code == 200
    after = api_client.get("/v1/reviewer/activities?district=Huye", headers=auth(reviewer_token)).json()[0]
    assert after["verification"] == "user_reported"
    assert after["review_status"] == "correction_requested"
    assert len(after["review_history"]) == 1
    farmer_records = api_client.get(f"/v1/farms/{huye['id']}/activities", headers=auth(farmer_token))
    assert farmer_records.status_code == 200
    assert farmer_records.json()[0]["review_status"] == "correction_requested"
    update = api_client.put(f"/v1/farms/{huye['id']}/activities/{activity['id']}", headers=auth(farmer_token), json={
        **payload, "notes": "Clarified farmer report", "quantity": 92,
    })
    assert update.status_code == 200
    assert update.json()["verification"] == "user_reported"
    farmer_records = api_client.get(f"/v1/farms/{huye['id']}/activities", headers=auth(farmer_token))
    assert farmer_records.json()[0]["review_status"] == "pending"
    refreshed_queue = api_client.get("/v1/reviewer/activities?district=Huye", headers=auth(reviewer_token)).json()
    assert refreshed_queue[0]["review_status"] == "pending"
    assert len(refreshed_queue[0]["review_history"]) == 1
    assert api_client.get("/v1/reviewer/activities", headers=auth(farmer_token)).status_code == 403
    assert api_client.put(f"/v1/reviewer/activities/{activity['id']}/decisions", headers=auth(reviewer_token),
                          json={"decision": "approved_as_reviewed", "reason": "Cannot modify prior decision"}).status_code == 405
    with Session(get_engine()) as db:
        stored = db.get(FarmActivity, activity["id"])
        assert stored.quantity == 92 and stored.notes == "Clarified farmer report"
        decisions = db.scalars(select(ActivityReviewDecision).where(ActivityReviewDecision.activity_id == activity["id"])).all()
        assert len(decisions) == 1 and decisions[0].decision == "correction_requested"
        assert db.scalar(select(AdminAuditEvent).where(AdminAuditEvent.action == "activity_review_decision")) is not None


def test_agronomy_rule_proposals_require_explicit_grants_and_keep_immutable_decisions(api_client):
    admin_token = register(api_client, "agronomy-admin@example.com")
    admin_id = make_role("agronomy-admin@example.com", "admin")
    proposer_token = register(api_client, "agronomy-proposer@example.com")
    proposer_id = make_role("agronomy-proposer@example.com", "reviewer")
    reviewer_token = register(api_client, "agronomy-reviewer@example.com")
    reviewer_id = make_role("agronomy-reviewer@example.com", "reviewer")

    proposal_payload = {
        "rule_id": "test.rule.provenance", "version": "1.0.0", "title": "Test-only proposal fixture",
        "category": "other", "crop_or_topic": "TEST FIXTURE",
        "proposed_claim": "Test-only workflow record; not agricultural guidance.",
        "geographic_scope": {"type": "district", "scope": ["Huye"], "limitations": "Test fixture scope only."},
        "season_scope": ["A"], "units": ["not applicable: test fixture"],
        "assumptions": ["Test data only."], "limitations": ["Not a real recommendation."],
        "uncertainty": "Test fixture; no agricultural evidence is asserted.", "source_references": [],
    }
    proposals_url = "/v1/agronomy/rule-proposals"
    assert api_client.get(proposals_url).status_code == 401
    assert api_client.get(proposals_url, headers=auth(proposer_token)).status_code == 403
    assert api_client.post(proposals_url, headers=auth(proposer_token), json=proposal_payload).status_code == 403
    assert api_client.post(f"/v1/admin/farmers/{reviewer_id}/agronomy-review-authorization",
                           headers=auth(proposer_token), json={"action": "grant", "reason": "Unauthorized farmer attempt"}).status_code == 403

    for reviewer_account_id in (proposer_id, reviewer_id):
        grant = api_client.post(f"/v1/admin/farmers/{reviewer_account_id}/agronomy-review-authorization",
                                headers=auth(admin_token), json={"action": "grant", "reason": "Authorized test-only review work"})
        assert grant.status_code == 200 and grant.json()["authorized"] is True
    assert api_client.post(f"/v1/admin/farmers/{admin_id}/agronomy-review-authorization",
                           headers=auth(admin_token), json={"action": "grant", "reason": "Authorized admin test role"}).status_code == 200

    created = api_client.post(proposals_url, headers=auth(proposer_token), json=proposal_payload)
    assert created.status_code == 201, created.text
    proposal = created.json()
    assert proposal["status"] == "proposed" and proposal["guidance_activation"] is False
    assert api_client.post(f"{proposals_url}/{proposal['id']}/decisions", headers=auth(proposer_token),
                           json={"decision": "approved", "rationale": "Proposer cannot approve own work"}).status_code == 403
    assert api_client.post(f"{proposals_url}/{proposal['id']}/decisions", headers=auth(reviewer_token),
                           json={"decision": "approved", "rationale": "Approval without evidence is rejected"}).status_code == 422
    assert api_client.post(f"{proposals_url}/{proposal['id']}/decisions", headers=auth(reviewer_token),
                           json={"decision": "rejected", "reviewer_id": proposer_id,
                                 "rationale": "Test proposal has no source evidence."}).status_code == 422
    rejected = api_client.post(f"{proposals_url}/{proposal['id']}/decisions", headers=auth(reviewer_token),
                               json={"decision": "rejected", "rationale": "Test proposal has no source evidence."})
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert rejected.json()["decision_history"][0]["reviewer_id"] == reviewer_id
    assert rejected.json()["guidance_activation"] is False

    revision_payload = {**proposal_payload, "version": "2.0.0", "revision_of_id": proposal["id"],
                        "source_references": [{"source_id": "test.fixture", "title": "Test-only source reference",
                            "url": "https://example.invalid/evidence", "source_version": "fixture-v1",
                            "locator": "test fixture", "permission_status": "unknown"}]}
    revision = api_client.post(proposals_url, headers=auth(proposer_token), json=revision_payload)
    assert revision.status_code == 201, revision.text
    assert revision.json()["revision_of_id"] == proposal["id"]
    superseded = api_client.post(f"{proposals_url}/{revision.json()['id']}/decisions", headers=auth(reviewer_token),
                                 json={"decision": "superseded", "rationale": "A later test-only revision replaces this fixture."})
    assert superseded.status_code == 200 and superseded.json()["status"] == "superseded"
    assert superseded.json()["guidance_activation"] is False

    final_payload = {**revision_payload, "version": "3.0.0", "revision_of_id": revision.json()["id"]}
    final_revision = api_client.post(proposals_url, headers=auth(proposer_token), json=final_payload)
    assert final_revision.status_code == 201, final_revision.text
    approved = api_client.post(f"{proposals_url}/{final_revision.json()['id']}/decisions", headers=auth(reviewer_token),
                               json={"decision": "approved", "rationale": "Workflow test only; trust anchor remains disabled."})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved" and approved.json()["guidance_activation"] is False
    assert approved.json()["decision_history"][0]["reviewer_id"] == reviewer_id
    from utils.agronomy_knowledge import approved_rules_for
    assert approved_rules_for("TEST FIXTURE", "Huye", "A") == []

    revoke = api_client.post(f"/v1/admin/farmers/{reviewer_id}/agronomy-review-authorization",
                             headers=auth(admin_token), json={"action": "revoke", "reason": "End test review authorization"})
    assert revoke.status_code == 200 and revoke.json()["authorized"] is False
    assert api_client.get(proposals_url, headers=auth(reviewer_token)).status_code == 403
    with Session(get_engine()) as db:
        assert db.scalar(select(AgronomyRuleProposal).where(AgronomyRuleProposal.id == proposal["id"])) is not None
        assert len(db.scalars(select(AgronomyRuleDecision)).all()) == 3
        assert len(db.scalars(select(AgronomyReviewAuthorizationEvent).where(
            AgronomyReviewAuthorizationEvent.reviewer_id == reviewer_id)).all()) == 2
