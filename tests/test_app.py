from pathlib import Path
from types import SimpleNamespace
from streamlit.testing.v1 import AppTest
from utils.data_loader import load_data

ROOT = str(Path(__file__).resolve().parent.parent)
PRE = f"import sys; sys.path.insert(0, r'{ROOT}')\nimport streamlit as st, plan, views\nfrom utils.data_loader import load_data\ndf, status = load_data()\n"


def run(body):
    at = AppTest.from_string(PRE + body, default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_full_app_shows_sign_in_form_before_opening_dashboard(monkeypatch):
    monkeypatch.delenv("CROP_PULSE_API_URL", raising=False)
    monkeypatch.delenv("CROP_PULSE_ENVIRONMENT", raising=False)
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Continue to CropPulse" in title.value for title in at.title)
    assert any(link.label == "Sign in to CropPulse" for link in at.link_button)
    assert not at.text_input
    assert not at.radio
    assert not any("Which crops should I consider" in item.value for item in at.markdown)


def test_streamlit_reloads_cached_client_missing_react_return_helper(monkeypatch):
    import backend.client as client

    monkeypatch.setenv("CROP_PULSE_API_URL", "http://api.test")
    monkeypatch.delattr(client, "react_portal_url")
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()

    assert not at.exception, [e.value for e in at.exception]
    assert callable(client.react_portal_url)


def test_streamlit_uses_local_api_default_but_requires_production_configuration(monkeypatch):
    import backend.client as client
    monkeypatch.delenv("CROP_PULSE_API_URL", raising=False)
    monkeypatch.delenv("CROP_PULSE_ENVIRONMENT", raising=False)
    assert client.api_url() == "http://127.0.0.1:8001"
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    assert client.api_url() == ""
    monkeypatch.setenv("CROP_PULSE_API_URL", "https://api.example.test")
    assert client.api_url() == "https://api.example.test"


def test_streamlit_react_return_url_is_environment_aware_and_safe(monkeypatch):
    import backend.client as client

    monkeypatch.delenv("CROP_PULSE_REACT_URL", raising=False)
    monkeypatch.delenv("CROP_PULSE_ENVIRONMENT", raising=False)
    assert client.react_portal_url() == "http://127.0.0.1:5173/overview"

    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    assert client.react_portal_url() == ""
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "http://react.example.test")
    assert client.react_portal_url() == ""
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "https://crop.example.test/app")
    assert client.react_portal_url() == "https://crop.example.test/app/overview"
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "https://user:password@crop.example.test")
    assert client.react_portal_url() == ""


def test_streamlit_restores_signed_in_farmer_from_browser_session_cookie(monkeypatch):
    from types import SimpleNamespace
    import backend.client as client

    state = {}
    farmer = {"id": "farmer-cookie", "display_name": "Cookie Farmer", "role": "farmer"}
    requests = []
    monkeypatch.setattr(client.st, "session_state", state)
    monkeypatch.setattr(client.st, "context", SimpleNamespace(cookies={"cp_session": "synthetic-session-cookie"}))

    def fake_request(method, path, *, authenticated=True, **kwargs):
        requests.append((method, path, authenticated, state.get("cp_access_token")))
        return farmer

    monkeypatch.setattr(client, "request", fake_request)

    assert client.restore_browser_session() is True
    assert state["cp_farmer"] == farmer
    assert state["cp_access_token"] == "synthetic-session-cookie"
    assert requests == [("GET", "/v1/me", True, "synthetic-session-cookie")]


def test_streamlit_refresh_restores_dashboard_without_showing_sign_in(monkeypatch):
    import backend.client as client
    import streamlit as st

    farmer = {"id": "farmer-cookie", "display_name": "Cookie Farmer", "email": "cookie@example.com", "role": "farmer"}
    monkeypatch.setenv("CROP_PULSE_API_URL", "http://api.test")
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "http://127.0.0.1:5173")
    monkeypatch.setattr(st, "context", SimpleNamespace(cookies={"cp_session": "synthetic-browser-session"}))

    def fake_request(method, path, *, authenticated=True, **kwargs):
        if path == "/v1/me": return farmer
        if path == "/v1/farms": return []
        if path == "/v1/streamlit/react-handoff": return {"redirect_url": "http://127.0.0.1:5173/overview?cp_handoff=synthetic-one-use-code"}
        raise AssertionError(f"Unexpected API request: {method} {path}")

    monkeypatch.setattr(client, "request", fake_request)
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Welcome, Cookie Farmer" in title.value for title in at.title)
    assert "cp_access_token" in at.session_state
    assert not any("Welcome to CropPulse" in title.value for title in at.title)


def test_streamlit_admin_session_keeps_admin_role_in_its_workspace(monkeypatch):
    from types import SimpleNamespace
    import backend.client as client
    import streamlit as st

    admin = {"id": "admin-cookie", "display_name": "Crop Admin", "email": "admin@example.com", "role": "admin"}
    monkeypatch.setenv("CROP_PULSE_API_URL", "http://api.test")
    monkeypatch.setattr(st, "context", SimpleNamespace(cookies={"cp_session": "synthetic-admin-session"}))

    def fake_request(method, path, *, authenticated=True, **kwargs):
        if path == "/v1/me": return admin
        if path == "/v1/streamlit/react-handoff": return {"redirect_url": "http://127.0.0.1:5173/overview?cp_handoff=admin-code"}
        raise AssertionError(f"Unexpected API request: {method} {path}")

    monkeypatch.setattr(client, "request", fake_request)
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()

    assert not at.exception, [e.value for e in at.exception]
    assert any("Administrator workspace" in title.value for title in at.title)
    assert any("administrator identity" in element.value for element in at.info)
    assert at.session_state["cp_farmer"]["role"] == "admin"
    assert not any("Welcome, Crop Admin" in title.value for title in at.title)


def test_streamlit_sign_out_revokes_handoff_and_browser_sessions(monkeypatch):
    from types import SimpleNamespace
    import backend.client as client

    state = {"cp_access_token": "handoff-session", "cp_farmer": {"id": "farmer"}, "cp_selected_farm": "farm"}
    revoked = []
    monkeypatch.setattr(client.st, "session_state", state)
    monkeypatch.setattr(client.st, "context", SimpleNamespace(cookies={"cp_session": "browser-session"}))
    monkeypatch.setattr(client, "request", lambda method, path: revoked.append(state["cp_access_token"]))

    client.sign_out()

    assert revoked == ["handoff-session", "browser-session"]
    assert "cp_access_token" not in state and "cp_farmer" not in state and "cp_selected_farm" not in state


def test_streamlit_backend_client_updates_a_specific_farm_crop_plan(monkeypatch):
    import backend.client as client
    captured = {}

    def fake_request(method, path, *, authenticated=True, **kwargs):
        captured.update(method=method, path=path, authenticated=authenticated, json=kwargs.get("json"))
        return {"id": "plan-id", "crop": "Beans"}

    monkeypatch.setattr(client, "request", fake_request)
    result = client.update_plan("farm/id", "plan id", district="Huye", crop="Beans", season="B",
                                planting_date="2026-10-22", area_ha=0.7, field_id=None,
                                plan={"farmer_notes": "Updated"})
    assert result["crop"] == "Beans"
    assert captured == {"method": "PUT", "path": "/v1/farms/farm%2Fid/plans/plan%20id",
                        "authenticated": True,
                        "json": {"district": "Huye", "crop": "Beans", "season": "B",
                                 "planting_date": "2026-10-22", "area_ha": 0.7,
                                 "field_id": None, "plan": {"farmer_notes": "Updated"}}}


def test_streamlit_unauthenticated_user_is_sent_to_react_for_sign_in(monkeypatch):
    import backend.client as client
    import streamlit as st
    monkeypatch.setenv("CROP_PULSE_API_URL", "http://api.test")
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "http://127.0.0.1:5173")
    monkeypatch.setattr(st, "context", SimpleNamespace(cookies={}))
    monkeypatch.setattr(client.st, "session_state", {})
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Continue to CropPulse" in title.value for title in at.title)
    link = next(link for link in at.link_button if link.label == "Sign in to CropPulse")
    assert link.url == "http://127.0.0.1:5173/overview?cp_return=streamlit"


def test_farm_records_read_is_empty_until_signed_in_farmer_selects_a_farm(monkeypatch):
    import backend.client as client
    from utils import frontend_services

    monkeypatch.setattr(client, "enabled", lambda: True)
    monkeypatch.setattr(frontend_services.st, "session_state", {"cp_access_token": "test-token"})
    monkeypatch.setattr(client, "farms", lambda: [])
    monkeypatch.setattr(
        client,
        "activities",
        lambda: (_ for _ in ()).throw(AssertionError("activities must not be requested without a farm")),
    )
    records = frontend_services.farm_records()

    assert records.empty
    assert "record_type" in records.columns


def test_farm_records_selects_first_owned_farm_before_loading_activities(monkeypatch):
    import backend.client as client
    from utils import frontend_services

    state = {"cp_access_token": "test-token"}
    monkeypatch.setattr(frontend_services.st, "session_state", state)
    monkeypatch.setattr(client, "enabled", lambda: True)
    monkeypatch.setattr(client, "farms", lambda: [{"id": "owned-farm-1"}, {"id": "owned-farm-2"}])
    monkeypatch.setattr(client, "activities", lambda: [{
        "id": "activity-1", "event_date": "2026-10-26", "activity_type": "Planting",
    }])

    records = frontend_services.farm_records()

    assert state["cp_selected_farm"] == "owned-farm-1"
    assert records.loc[0, "record_type"] == "Planting"


def test_streamlit_does_not_offer_a_separate_login_or_registration_form(monkeypatch):
    monkeypatch.setenv("CROP_PULSE_API_URL", "http://api.test")
    at = AppTest.from_file(f"{ROOT}/app.py", default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.text_input
    assert not at.radio
    assert any(link.label == "Sign in to CropPulse" for link in at.link_button)


def test_streamlit_react_signin_url_keeps_configured_path_and_return_intent(monkeypatch):
    import backend.client as client
    monkeypatch.setenv("CROP_PULSE_REACT_URL", "https://crop.example.test/app")
    monkeypatch.setenv("CROP_PULSE_ENVIRONMENT", "production")
    assert client.react_signin_url() == "https://crop.example.test/app/overview?cp_return=streamlit"


def test_plan_pages_render():
    run("plan.decisions(df, status)")
    for fn in ("crop_guide", "calendar", "planner", "districts"):
        run(f"plan.{fn}()")


def _rendered_strings(at):
    values = []
    for name in ("title", "header", "subheader", "caption", "markdown", "info", "warning", "success"):
        values.extend(element.value for element in getattr(at, name, []) if isinstance(getattr(element, "value", None), str))
    return "\n".join(values)


def test_streamlit_crop_guide_and_planning_labels_are_explicitly_provisional():
    guide = _rendered_strings(run("plan.crop_guide()"))
    assert "not locally verified recommendations" in guide
    assert "Altitude range (unverified)" in guide
    assert "not NISR observations or a yield forecast" in guide
    assert "planting months from the unverified CropPulse guide" in guide

    embedded_guide = _rendered_strings(run("plan.crop_guide(False)"))
    assert "not locally verified recommendations" in embedded_guide

    calendar = _rendered_strings(run("plan.calendar()"))
    assert "unverified CropPulse guide" in calendar
    assert "omitted crop is not evidence that it cannot be grown locally" in calendar

    planner = _rendered_strings(run("plan.planner()"))
    assert "not a local yield forecast" in planner
    assert "Indicative harvest range (unverified)" in planner

    district_map = _rendered_strings(run("plan.districts()"))
    assert "not verified district suitability" in district_map


def test_every_data_lab_page_renders_with_installed_data_status():
    status = load_data()[1]
    assert status["state"] in {"demo", "validated", "pending", "warning"}
    for fn in ("overview", "crop_intel", "district_explorer", "seasonal", "risk", "data_explorer", "briefs", "methodology"):
        run(f"views.{fn}(df, 2025, status)")


def test_planner_edge_cases():
    at = run("plan.planner()")
    at.number_input[0].set_value(0.0).run(); assert not at.exception
    at.number_input[0].set_value(2.0).run(); at.number_input[1].set_value(300.0).run(); assert not at.exception


def test_decisions_react_to_inputs():
    at = run("plan.decisions(df, status)")
    before = [m.value for m in at.markdown if m.value.startswith("###")]
    at.checkbox[0].check().run(); at.number_input[0].set_value(2600).run(); assert not at.exception
    after = [m.value for m in at.markdown if m.value.startswith("###")]
    assert before != after
