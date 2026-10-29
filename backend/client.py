"""Small synchronous Streamlit-to-API client. Tokens stay only in Streamlit session state."""
import os
import json
from urllib.parse import quote, urlsplit, urlunsplit

import streamlit as st


def api_url() -> str:
    configured = os.environ.get("CROP_PULSE_API_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if environment in {"production", "prod"}:
        return ""
    return "http://127.0.0.1:8001"


def enabled() -> bool:
    return bool(api_url())


def react_portal_url() -> str:
    """Return the configured React overview URL, or empty if not safely configured."""
    configured = os.environ.get("CROP_PULSE_REACT_URL", "").strip()
    environment = os.environ.get("CROP_PULSE_ENVIRONMENT", "development").strip().lower()
    if not configured and environment not in {"production", "prod"}:
        configured = "http://127.0.0.1:5173"
    if not configured:
        return ""
    try:
        parts = urlsplit(configured)
        if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment):
            return ""
        if environment in {"production", "prod"} and parts.scheme != "https":
            return ""
    except ValueError:
        return ""
    path = f"{parts.path.rstrip('/')}/overview"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def react_signin_url() -> str:
    """Open React's shared sign-in and ask it to return to Streamlit afterward."""
    configured = react_portal_url()
    if not configured:
        return ""
    parts = urlsplit(configured)
    from urllib.parse import urlencode
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode({"cp_return": "streamlit"}), ""))


def request(method: str, path: str, *, authenticated: bool = True, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    if authenticated:
        token = st.session_state.get("cp_access_token")
        if not token:
            raise RuntimeError("Sign in to save or view persistent farm records.")
        headers["Authorization"] = f"Bearer {token}"
    try:
        import httpx
    except ImportError:
        # Keep the local account flow usable when Streamlit is launched by a
        # system Python that does not have the optional HTTP client installed.
        from urllib.error import HTTPError, URLError
        from urllib.request import Request as UrlRequest, urlopen

        json_payload = kwargs.pop("json", None)
        body = json.dumps(json_payload).encode("utf-8") if json_payload is not None else None
        if body is not None:
            headers.setdefault("Content-Type", "application/json")
        req = UrlRequest(f"{api_url()}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=8.0) as response:
                status_code = response.status
                raw = response.read()
        except HTTPError as exc:
            status_code = exc.code
            raw = exc.read()
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("CropPulse record service is unavailable. Check that the API is running.") from exc
        try:
            payload = json.loads(raw) if raw else None
        except (ValueError, UnicodeDecodeError):
            payload = None
    else:
        try:
            response = httpx.request(method, f"{api_url()}{path}", headers=headers, timeout=8.0, **kwargs)
        except httpx.HTTPError as exc:
            raise RuntimeError("CropPulse record service is unavailable. Check that the API is running.") from exc
        status_code = response.status_code
        try:
            payload = response.json()
        except ValueError:
            payload = None
    if status_code == 401 and authenticated:
        st.session_state.pop("cp_access_token", None)
        st.session_state.pop("cp_farmer", None)
        st.session_state.pop("cp_selected_farm", None)
        st.session_state.pop("active_farm_choice", None)
        raise RuntimeError("Your sign-in expired. Sign in again to continue.")
    if status_code >= 400:
        try:
            detail = payload.get("detail")
        except (AttributeError, TypeError):
            detail = None
        if isinstance(detail, list):
            detail = "; ".join(
                f"{'.'.join(str(part) for part in item.get('loc', []) if part != 'body')}: {item.get('msg', 'Invalid value')}"
                for item in detail
            ) or "Please check the submitted values."
        if not detail:
            detail = f"Request failed (HTTP {status_code}). The API returned no error details."
        raise RuntimeError(str(detail))
    if status_code == 204:
        return None
    if payload is None:
        raise RuntimeError("The CropPulse record service returned an unreadable response.")
    return payload


def sign_in(email: str, password: str, display_name: str | None = None, privacy_accepted: bool = False):
    route = "/v1/auth/register" if display_name is not None else "/v1/auth/login"
    payload = {"email": email, "password": password}
    if display_name is not None:
        payload["display_name"] = display_name
        payload["privacy_notice_accepted"] = privacy_accepted
    result = request("POST", route, authenticated=False, json=payload)
    st.session_state["cp_access_token"] = result["access_token"]
    try:
        farmer = request("GET", "/v1/me")
    except RuntimeError:
        clear_local_login_state(st.session_state)
        raise
    st.session_state["cp_farmer"] = farmer
    st.session_state.pop("cp_selected_farm", None)
    return farmer


def exchange_handoff(code: str):
    result = request("POST", "/v1/streamlit/handoff/exchange", authenticated=False, json={"code": code})
    st.session_state["cp_access_token"] = result["access_token"]
    farmer = request("GET", "/v1/me")
    st.session_state["cp_farmer"] = farmer
    st.session_state.pop("cp_selected_farm", None)
    st.session_state["cp_open_dashboard_after_login"] = True
    return farmer


def create_react_handoff() -> str:
    """Create a short-lived one-time URL that signs this browser into React."""
    result = request("POST", "/v1/streamlit/react-handoff")
    return result["redirect_url"]


def restore_browser_session() -> bool:
    """Restore React's HttpOnly browser session after a Streamlit page reload."""
    if st.session_state.get("cp_access_token"):
        return True
    if not enabled():
        return False
    try:
        token = st.context.cookies.get("cp_session")
    except (AttributeError, RuntimeError):
        token = None
    if not token:
        return False
    st.session_state["cp_access_token"] = token
    try:
        farmer = request("GET", "/v1/me")
    except RuntimeError:
        clear_local_login_state(st.session_state)
        return False
    st.session_state["cp_farmer"] = farmer
    st.session_state.pop("cp_selected_farm", None)
    return True


def clear_local_login_state(state):
    for key in ("cp_access_token", "cp_farmer", "cp_selected_farm", "active_farm_choice"):
        state.pop(key, None)


def sign_out():
    tokens = []
    session_token = st.session_state.get("cp_access_token")
    if session_token:
        tokens.append(session_token)
    try:
        browser_token = st.context.cookies.get("cp_session")
    except (AttributeError, RuntimeError):
        browser_token = None
    if browser_token and browser_token not in tokens:
        tokens.append(browser_token)
    for token in tokens:
        try:
            # Revoke both the Streamlit handoff session and the shared React
            # cookie session so a later refresh cannot silently sign back in.
            st.session_state["cp_access_token"] = token
            request("POST", "/v1/auth/logout")
        except RuntimeError:
            # Expired or unavailable APIs should not keep the local UI signed in.
            pass
    clear_local_login_state(st.session_state)


def farms():
    return request("GET", "/v1/farms")


def plans(farm_id: str):
    return request("GET", f"/v1/farms/{quote(str(farm_id), safe='')}/plans")


def create_farm(**values):
    return request("POST", "/v1/farms", json=values)


def _farm_id():
    farm_id = st.session_state.get("cp_selected_farm")
    if not farm_id:
        raise RuntimeError("Create or select one of your farms before saving farm records.")
    return quote(str(farm_id), safe="")


def activities():
    return request("GET", f"/v1/farms/{_farm_id()}/activities")


def create_activity(**values):
    return request("POST", f"/v1/farms/{_farm_id()}/activities", json=values)


def update_activity(activity_id, **values):
    return request("PUT", f"/v1/farms/{_farm_id()}/activities/{quote(str(activity_id), safe='')}", json=values)


def delete_activity(activity_id):
    return request("DELETE", f"/v1/farms/{_farm_id()}/activities/{quote(str(activity_id), safe='')}")


def create_plan(**values):
    return request("POST", f"/v1/farms/{_farm_id()}/plans", json=json.loads(json.dumps(values, default=str)))


def update_plan(farm_id: str, plan_id: str, **values):
    return request("PUT", f"/v1/farms/{quote(str(farm_id), safe='')}/plans/{quote(str(plan_id), safe='')}",
                   json=json.loads(json.dumps(values, default=str)))
