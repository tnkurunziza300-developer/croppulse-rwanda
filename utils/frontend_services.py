"""Farmer workflow service adapters.

Farm activities and saved crop plans use the authenticated API when configured
and signed in. Other frontend collections remain session-only in Phase 1 and
the Streamlit application clears them at account login/logout boundaries.
"""
from datetime import date
from typing import Any
import pandas as pd
import streamlit as st
from backend import client as backend

SESSION_COLLECTIONS = (
    "cp_farm_records", "cp_market_quotes", "cp_review_submissions", "cp_recommendation_feedback",
    "cp_pest_reports", "cp_extension_notes", "cp_cooperative_notes", "cp_weather_observations",
)


def clear_session_data(state=None) -> None:
    """Remove frontend-submitted data and generated plans from the current session only."""
    state = st.session_state if state is None else state
    keys = set(SESSION_COLLECTIONS) | {f"{key}_next_id" for key in SESSION_COLLECTIONS}
    keys.update({"cp_plan", "cp_plan_error", "cp_saved_crop_plans", "cp_feedback_context", "confirm_clear_frontend_data"})
    for key in keys:
        state.pop(key, None)


def _get(key: str) -> list[dict[str, Any]]:
    return st.session_state.setdefault(key, [])


def _next_id(key: str) -> int:
    counter_key = f"{key}_next_id"
    value = int(st.session_state.get(counter_key, 1))
    st.session_state[counter_key] = value + 1
    return value


def _insert(key: str, item: dict[str, Any], status: str) -> int:
    entries = _get(key)
    item = {**item, "id": _next_id(key), "created_in_session": True, "status": status}
    entries.insert(0, item)
    return item["id"]


def add_farm_record(**record) -> int | str:
    for field in ("area_ha", "quantity", "amount_rwf"):
        if record.get(field) is not None and float(record[field]) < 0:
            raise ValueError(f"{field.replace('_', ' ').title()} cannot be negative.")
    if backend.enabled() and st.session_state.get("cp_access_token"):
        payload = {"district": record["district"], "crop": record["crop"], "season": record["season"],
                   "activity_type": record["record_type"], "event_date": record["record_date"],
                   "area_ha": record.get("area_ha"), "quantity": record.get("quantity"),
                   "unit": record.get("unit"), "amount_rwf": record.get("amount_rwf"), "notes": record.get("notes", "")}
        return backend.create_activity(**payload)["id"]
    return _insert("cp_farm_records", record, "Farmer-reported; temporary session data")


def update_farm_record(record_id: int | str, **changes) -> None:
    if backend.enabled() and st.session_state.get("cp_access_token"):
        payload = {"district": changes["district"], "crop": changes["crop"], "season": changes["season"],
                   "activity_type": changes["record_type"], "event_date": changes["record_date"],
                   "area_ha": changes.get("area_ha"), "quantity": changes.get("quantity"),
                   "unit": changes.get("unit"), "amount_rwf": changes.get("amount_rwf"), "notes": changes.get("notes", "")}
        backend.update_activity(record_id, **payload)
        return
    for entry in _get("cp_farm_records"):
        if entry["id"] == record_id:
            entry.update(changes)
            entry["updated_in_session"] = True
            return


def delete_farm_record(record_id: int | str) -> None:
    if backend.enabled() and st.session_state.get("cp_access_token"):
        backend.delete_activity(record_id)
        return
    st.session_state["cp_farm_records"] = [r for r in _get("cp_farm_records") if r["id"] != record_id]


def farm_records() -> pd.DataFrame:
    if backend.enabled() and st.session_state.get("cp_access_token"):
        # The overview may be opened before the farmer visits My profile, where
        # the active farm is normally selected. Resolve that state from the
        # authenticated farm list; a farmer with no farms gets an empty summary.
        if not st.session_state.get("cp_selected_farm"):
            farms = backend.farms()
            if not farms:
                return pd.DataFrame(columns=[
                    "id", "farm_id", "district", "crop", "season", "event_date",
                    "activity_type", "record_date", "record_type", "created_in_session", "status",
                ])
            st.session_state["cp_selected_farm"] = farms[0]["id"]
        rows = backend.activities()
        return pd.DataFrame([{**row, "record_date": row["event_date"], "record_type": row["activity_type"],
                              "created_in_session": False, "status": "Farmer-reported; persistently stored"}
                             for row in rows])
    return pd.DataFrame(_get("cp_farm_records"))


def add_crop_plan(plan: dict) -> str:
    if backend.enabled() and st.session_state.get("cp_access_token"):
        result = backend.create_plan(crop=plan["crop"], season=plan["season"],
                                     planting_date=plan["planting_date"].isoformat(),
                                     district=plan["district"], area_ha=float(plan["area_ha"]), plan=plan)
        return result["id"]
    st.session_state.setdefault("cp_saved_crop_plans", []).insert(0, plan)
    return "session"


def add_market_quote(crop, market, observed_on, price_rwf, unit, source):
    if price_rwf <= 0: raise ValueError("Price must be greater than zero.")
    if str(observed_on) > date.today().isoformat(): raise ValueError("Observation date cannot be in the future.")
    if not all(str(x).strip() for x in (crop, market, observed_on, unit, source)):
        raise ValueError("Crop, market, date, unit, and source are required.")
    _insert("cp_market_quotes", {"crop": crop, "market": market, "observed_on": str(observed_on),
                                  "price_rwf": float(price_rwf), "unit": unit, "source": source.strip()},
            "User-entered; unverified; temporary session data")


def delete_market_quote(quote_id: int):
    st.session_state["cp_market_quotes"] = [q for q in _get("cp_market_quotes") if q["id"] != quote_id]


def market_quotes() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_market_quotes"))


def add_review_submission(**submission):
    _insert("cp_review_submissions", submission, "Unauthenticated submission; not an approval")


def review_submissions() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_review_submissions"))


def add_feedback(**feedback):
    if feedback.get("rating") not in {"useful", "not useful", "unclear", "unsafe"}:
        raise ValueError("Choose a feedback rating.")
    _insert("cp_recommendation_feedback", feedback, "User feedback; temporary session data")


def recommendation_feedback() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_recommendation_feedback"))


def add_pest_report(**report):
    if not str(report.get("description", "")).strip():
        raise ValueError("Describe the observed symptoms or pest.")
    _insert("cp_pest_reports", report, "Farmer-reported; unverified; temporary session data")


def pest_reports() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_pest_reports"))


def add_extension_note(**note):
    _insert("cp_extension_notes", note, "Demonstration; temporary session data")


def extension_notes() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_extension_notes"))


def add_cooperative_note(**note):
    members = int(note.get("members_reached", 0))
    area = float(note.get("area_ha", 0))
    if members < 0 or area < 0:
        raise ValueError("Member count and area cannot be negative.")
    if not str(note.get("topic", "")).strip():
        raise ValueError("Enter a topic or shared issue.")
    _insert("cp_cooperative_notes", note, "Demonstration; temporary session data")


def cooperative_notes() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_cooperative_notes"))


def add_weather_observation(**observation):
    low, high = observation.get("temperature_min_c"), observation.get("temperature_max_c")
    if observation.get("rainfall_mm") is None and low is None and high is None:
        raise ValueError("Enter at least one rainfall or temperature observation.")
    if low is not None and high is not None and float(low) > float(high):
        raise ValueError("Minimum temperature cannot exceed maximum temperature.")
    rainfall = observation.get("rainfall_mm")
    if rainfall is not None and float(rainfall) < 0:
        raise ValueError("Rainfall cannot be negative.")
    if not str(observation.get("source", "")).strip():
        raise ValueError("Enter where this observation came from (for example, a local gauge).")
    _insert("cp_weather_observations", observation, "User-entered observation; unverified; temporary session data")


def weather_observations() -> pd.DataFrame:
    return pd.DataFrame(_get("cp_weather_observations"))


def csv_bytes(frame: pd.DataFrame) -> bytes:
    """Neutralize spreadsheet formula prefixes in user-entered text before export."""
    safe = frame.copy()
    for col in safe.select_dtypes(include=["object", "string"]).columns:
        safe[col] = safe[col].map(lambda value: "'" + value if isinstance(value, str) and value[:1] in ("=", "+", "-", "@") else value)
    return safe.to_csv(index=False).encode("utf-8")
