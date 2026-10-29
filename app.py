from pathlib import Path
import importlib
import os
import time
from datetime import date
import streamlit as st
from utils.data_loader import load_data, SAMPLE_LABEL
from utils.filters import apply_filters
from utils.data_validation import validate
import plan, views
import product_pages
import knowledge as K
from utils import frontend_services
from utils import geography as geo
from backend import client as backend_client
from utils.i18n import t

# Streamlit can keep imported modules alive across reruns and source updates.
# Reload the API client only when this process lacks a helper required by this
# entry point; unconditional reloads can discard injected clients in tests.
_required_backend_helpers = ("exchange_handoff", "react_portal_url", "react_signin_url", "restore_browser_session", "create_react_handoff")
if any(not callable(getattr(backend_client, name, None)) for name in _required_backend_helpers):
    backend_client = importlib.reload(backend_client)

# Streamlit can rerun this entry point while retaining an imported page module.
# Reload it if the entry point is newer than the page definitions in memory.
_required_product_pages = ("extension_notes_page", "pest_reporting_page", "feedback_page", "weather_page", "cooperative_page")
if any(not callable(getattr(product_pages, name, None)) for name in _required_product_pages):
    product_pages = importlib.reload(product_pages)

st.set_page_config(page_title="CropPulse Rwanda", page_icon="🌾", layout="wide")
handoff_code = st.query_params.get("cp_handoff")
if handoff_code:
    # Remove the one-time code from the address bar before any app content is rendered.
    del st.query_params["cp_handoff"]
    try:
        backend_client.exchange_handoff(handoff_code)
        frontend_services.clear_session_data()
        st.rerun()
    except (RuntimeError, ValueError) as exc:
        backend_client.clear_local_login_state(st.session_state)
        detail = str(exc).strip()
        st.session_state["cp_handoff_error"] = detail or "This sign-in link could not be used. Return to CropPulse and open the planning workspace again."

# Streamlit session state can be reset when the browser reloads. Revalidate the
# host-only HttpOnly React session cookie so a refresh does not force sign-in.
if not st.session_state.get("cp_access_token"):
    backend_client.restore_browser_session()
st.markdown(f"<style>{(Path(__file__).parent / 'assets' / 'styles.css').read_text()}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading dataset…")
def get_data():
    return load_data()


df, status = get_data()
year, fdf = None, df


def guarded(fn):
    def run():
        if status["state"] == "demo":
            st.warning(SAMPLE_LABEL)
        if status["state"] == "unavailable" or df.empty or year is None:
            st.error(status["message"]); st.info("Add a CSV to data/verified/ with: district, crop, season, year, area_ha, production_t."); return
        if fdf.empty:
            st.info("No records match the current filters. Use Clear filters in the sidebar."); return
        fn(fdf, int(year), status)
    return run


def page(slug, title, icon, blurb, parts, default=False):
    def p():
        st.title(title); st.caption(blurb)
        if len(parts) == 1:
            parts[0][1]()
        else:
            for t, (_, f) in zip(st.tabs([n for n, _ in parts]), parts):
                with t:
                    f()
    p.__name__ = slug
    return st.Page(p, title=title, icon=icon, url_path=slug, default=default)


def decide():
    plan.decisions(df, status)


def farmer_dashboard():
    farmer = st.session_state.get("cp_farmer", {})
    role = farmer.get("role", "farmer")
    if role == "admin":
        st.title("Administrator workspace")
        st.caption("Signed in with your CropPulse administrator account. Your administrator role is supplied by the account service.")
        st.info("Use the CropPulse React workspace for account, permission, and system administration. Your Streamlit session keeps the same administrator identity.")
        st.page_link(P["account"], label="View account profile")
        return
    if role == "reviewer":
        st.title("CropPulse reviewer workspace")
        st.caption("Signed in with your CropPulse reviewer account. Reviewer access is determined by the account service.")
        st.info("Use the reviewer queue for assigned review work. This role does not imply verified agricultural qualifications.")
        st.page_link(P["review_queue"], label="Open reviewer queue")
        return
    st.title(f"Welcome, {farmer.get('display_name', 'farmer')}")
    st.caption("Your private farm workspace. Plans and records below are loaded from the CropPulse account service.")
    try:
        farms = backend_client.farms()
        plans = [(farm, item) for farm in farms for item in backend_client.plans(farm["id"])]
    except RuntimeError as exc:
        st.error(str(exc))
        if not st.session_state.get("cp_access_token"):
            st.info("Your sign-in has ended. Open My profile to sign in again.")
        return
    active = [item for _, item in plans if item["status"] not in {"completed", "cancelled"}]
    a, b, c = st.columns(3)
    a.metric("My farms", len(farms))
    b.metric("My crop plans", len(plans))
    c.metric("Seasons in progress", len(active))
    st.subheader("Growing seasons")
    if not farms:
        st.info("Start by adding a farm in My profile. Farm records are private to your account.")
    elif not plans:
        st.info("No crop plans yet. Open Gahunda yo guhinga to draft a plan, then save it to your account.")
    else:
        for farm, item in plans:
            with st.container(border=True):
                st.markdown(f"### {item['crop']} · Season {item['season']} · {item['status'].replace('_', ' ')}")
                st.caption(f"{farm['name']} · {farm['district']} · {item['area_ha']:g} ha · Intended planting {item['planting_date']}")
                st.write(f"Actual planting: {item.get('actual_planting_date') or 'Not recorded'}")
                if item["status"] == "planned":
                    st.info("Next step: record the actual planting date when planting takes place.")
                elif item["status"] == "planted":
                    st.info("Next step: update the plan to monitoring when you begin checking crop progress.")
                elif item["status"] == "monitoring":
                    st.info("Keep recording farm work as it happens. Dated crop-stage observations are not available yet.")
                elif item["status"] == "harvesting":
                    st.info("Record harvest events in Farm Records, then complete the plan when the season ends.")
                elif item["status"] == "completed":
                    st.caption("Plan complete. Structured yield and cost review is not available yet.")
                else:
                    st.caption("This plan is cancelled.")
                if item["status"] in {"draft", "planned"}:
                    with st.expander("Edit saved crop plan"):
                        with st.form(f"edit_crop_plan_{item['id']}"):
                            crop_options = list(K.CROPS)
                            crop_index = crop_options.index(item["crop"]) if item["crop"] in crop_options else 0
                            crop = st.selectbox("Crop", crop_options, index=crop_index, key=f"edit_crop_{item['id']}")
                            season = st.selectbox("Season", list(K.SEASONS), index=list(K.SEASONS).index(item["season"]), key=f"edit_season_{item['id']}")
                            planting = st.date_input("Proposed planting date", value=date.fromisoformat(item["planting_date"]), key=f"edit_date_{item['id']}")
                            area = st.number_input("Planned area (ha)", min_value=0.01, max_value=100000.0, value=float(item["area_ha"]), step=0.1, key=f"edit_area_{item['id']}")
                            old_plan = item.get("plan") or {}
                            notes = st.text_area("Farmer notes (not verified)", value=old_plan.get("farmer_notes", ""), max_chars=2000, key=f"edit_notes_{item['id']}")
                            submitted = st.form_submit_button("Save plan changes")
                        if submitted:
                            try:
                                revised = product_pages.build_plan(crop, farm["district"], season, planting, float(area))
                                revised["farmer_notes"] = notes.strip()
                                backend_client.update_plan(farm["id"], item["id"],
                                    district=farm["district"], crop=crop, season=season,
                                    planting_date=planting.isoformat(), area_ha=float(area),
                                    field_id=item.get("field_id"), plan=revised)
                                st.success("Crop plan changes saved. Its guidance remains provisional.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Crop plan could not be updated: {exc}")
    st.markdown("### Continue your work")
    x, y, z = st.columns(3)
    with x: st.page_link(P["crop_plan"], label="Plan a crop", icon="🌱")
    with y: st.page_link(P["farm_records"], label="Farm records", icon="📒")
    with z: st.page_link(P["weather"], label="Weather & climate", icon="🌦️")


def account_page():
    farmer = st.session_state.get("cp_farmer")
    if not farmer:
        st.title("Continue to CropPulse")
        st.caption("Sign in or create your account in the CropPulse React app. You will return to this planning workspace automatically after signing in.")
        if st.session_state.get("cp_handoff_error"):
            st.error(st.session_state.pop("cp_handoff_error"))
        react_url = backend_client.react_signin_url()
        if react_url:
            st.link_button("Sign in to CropPulse", react_url, type="primary", use_container_width=True)
        else:
            st.error("The shared React sign-in address is not configured. Ask the administrator to set CROP_PULSE_REACT_URL.")
        st.caption("CropPulse has one account system. This workspace does not accept a separate password.")
        return

    st.title("My profile")
    role = farmer.get("role", "farmer")
    role_label = {"admin": "Platform administrator", "reviewer": "CropPulse reviewer", "farmer": "Farmer"}.get(role, "Account")
    st.caption("Account identity and access for the signed-in user.")
    st.markdown(f"**Name**  \n{farmer.get('display_name', 'Not provided')}")
    st.markdown(f"**Email**  \n{farmer.get('email', 'Not available')}")
    st.markdown(f"**CropPulse role**  \n{role_label}")
    if role == "farmer":
        st.caption("Your farms, crop plans, and saved activities are private to this account and loaded from the authenticated API.")
    elif role == "admin":
        st.caption("Administrator permissions come from the CropPulse account service. Use React for account and system administration.")
    else:
        st.caption("Reviewer access comes from the CropPulse account service. This role does not certify agricultural qualifications.")
    st.divider()
    if farmer.get("role", "farmer") == "farmer":
        st.subheader("My farms")
        try:
            farms = backend_client.farms()
            if farms:
                farm_options = {f"{farm['name']} · {farm['district']} · {farm['id'][:8]}": farm["id"] for farm in farms}
                selected = st.session_state.get("cp_selected_farm")
                if selected not in farm_options.values():
                    selected = next(iter(farm_options.values()))
                selected_label = next(label for label, farm_id in farm_options.items() if farm_id == selected)
                choice = st.selectbox("Active farm", list(farm_options), index=list(farm_options).index(selected_label), key="active_farm_choice")
                st.session_state["cp_selected_farm"] = farm_options[choice]
            else:
                st.info("You have no farm profiles yet. Add a farm to save plans and activities.")
            with st.form("cp_create_farm_form"):
                st.markdown("**Add a farm**")
                farm_name = st.text_input("Farm name", max_chars=120)
                farm_district = st.selectbox("Farm district", sorted(set(geo.ALL_DISTRICTS)))
                farm_sector = st.text_input("Sector (optional)", max_chars=80)
                farm_area = st.number_input("Area in hectares (optional; enter 0 if unknown)", min_value=0.0, step=0.1)
                farm_submitted = st.form_submit_button("Save farm", type="primary")
            if farm_submitted:
                if not farm_name.strip():
                    st.error("Enter a farm name.")
                else:
                    created = backend_client.create_farm(name=farm_name.strip(), district=farm_district,
                        sector=farm_sector.strip() or None, area_ha=farm_area or None)
                    st.session_state["cp_selected_farm"] = created["id"]
                    st.success("Farm saved to your account.")
                    st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    st.divider()
    if st.button("Sign out", type="secondary", key="cp_profile_sign_out"):
        backend_client.sign_out()
        frontend_services.clear_session_data()
        st.session_state.pop("cp_auth_mode", None)
        st.success("You are signed out.")
        st.rerun()


decide.__name__ = "decide"
P = {"decide": st.Page(decide, title="Crop Decisions", icon="🌱", url_path="decide", default=False),
     "calendar": st.Page(plan.calendar, title="Planting Calendar", icon="📅", url_path="calendar"),
     "planner": st.Page(plan.planner, title="Farm Planner", icon="🧮", url_path="planner"),
     "crop_plan": st.Page(product_pages.crop_plan_page, title=t("plan", st.session_state.get("cp_language", "en")), icon="🗓️", url_path="crop-plan"),
     "farm_records": st.Page(product_pages.farm_records_page, title=t("records", st.session_state.get("cp_language", "en")), icon="📒", url_path="farm-records"),
     "extension_notes": st.Page(product_pages.extension_notes_page, title=t("extension", st.session_state.get("cp_language", "en")), icon="🌱", url_path="extension-visits"),
     "pest_reports": st.Page(product_pages.pest_reporting_page, title=t("pest", st.session_state.get("cp_language", "en")), icon="🪲", url_path="crop-health"),
     "feedback": st.Page(product_pages.feedback_page, title=t("feedback", st.session_state.get("cp_language", "en")), icon="💬", url_path="feedback"),
     "weather": st.Page(product_pages.weather_page, title=t("weather_climate", st.session_state.get("cp_language", "en")), icon="🌦️", url_path="weather-climate"),
     "cooperative": st.Page(product_pages.cooperative_page, title=t("cooperative", st.session_state.get("cp_language", "en")), icon="🤝", url_path="cooperative"),
     "market": st.Page(product_pages.market_economics_page, title=t("markets", st.session_state.get("cp_language", "en")), icon="💹", url_path="market-economics"),
     "review_queue": st.Page(product_pages.review_queue_page, title="Agronomy Review Queue", icon="🧑‍🌾", url_path="review-queue"),
     "overview": page("overview", "Overview", "📊", "Production, yield and flagged records at a glance.", [("Overview", guarded(views.overview))]),
     "analytics": page("analytics", "Crop Analytics", "📈", "The evidence behind recommendations: crop guide, history, seasons and data briefs.",
                       [("Crop guide", lambda: plan.crop_guide(False)), ("Crop history", guarded(views.crop_intel)), ("Seasonal trends", guarded(views.seasonal)), ("Data brief", guarded(views.briefs))]),
     "districts": page("districts", "District Comparison", "🗺️", "Compare districts on a map and in the data.", [("Map: crop fit", lambda: plan.districts(False)), ("District data", guarded(views.district_explorer))]),
     "risks": page("risks", "Agricultural Risks", "⚠️", "Rule-based flags to investigate, never diagnoses.", [("Risks", guarded(views.risk))]),
     "explorer": page("explorer", "Data Explorer", "🔎", "Browse, check and export the records behind every number.", [("Records", guarded(views.data_explorer))]),
     "method": page("method", "Methodology & Sources", "📚", "How numbers and recommendations are produced, and their limits.", [("Methodology", guarded(views.methodology))])}
P["account"] = st.Page(account_page, title="My profile", url_path="account")
P["dashboard"] = st.Page(farmer_dashboard, title="Workspace", url_path="dashboard", default=True)
st.session_state["_pages"] = P
signed_in = backend_client.enabled() and bool(st.session_state.get("cp_access_token"))
if not signed_in:
    pg = st.navigation({"Account": [P["account"]]})
else:
    role = st.session_state.get("cp_farmer", {}).get("role", "farmer")
    workspace_label = "My farm" if role == "farmer" else "My workspace"
    if role in {"admin", "reviewer"}:
        sections = {workspace_label: [P["dashboard"], P["account"]],
                    "Evidence and review": [P[k] for k in ("overview", "analytics", "districts", "risks", "explorer", "review_queue")],
                    "About": [P["method"]]}
    else:
        sections = {workspace_label: [P["dashboard"], P["account"]],
                    "Plan / Gahunda": [P["decide"], P["crop_plan"], P["calendar"], P["planner"], P["weather"]],
                    "Farm / Umurima": [P["farm_records"], P["pest_reports"], P["extension_notes"], P["cooperative"], P["feedback"], P["market"]],
                    "Evidence": [P[k] for k in ("overview", "analytics", "districts", "risks", "explorer", "review_queue")],
                    "About": [P["method"]]}
    pg = st.navigation(sections)
if st.session_state.pop("cp_open_dashboard_after_login", False) and signed_in:
    st.switch_page(P["dashboard"])

with st.sidebar:
    st.markdown("### 🌾 CropPulse Rwanda"); st.caption("Evidence to decisions: what to plant, where and when.")
    lang = st.session_state.get("cp_language", "en")
    st.selectbox(t("language", lang), ["en", "rw"], format_func=lambda x: "English" if x == "en" else "Ikinyarwanda",
                 key="cp_language", help="English and Kinyarwanda labels are available across farmer workflows and primary decisions; detailed analytics and agronomy guidance remain mainly in English.")
    if backend_client.enabled() and signed_in:
        farmer = st.session_state.get("cp_farmer", {})
        role_label = {"admin": "Platform administrator", "reviewer": "CropPulse reviewer", "farmer": "Farmer"}.get(
            farmer.get("role"), "Account")
        st.caption(f"Signed in as {farmer.get('display_name', 'user')} · {role_label}")
        st.page_link(P["account"], label="My profile")
        try:
            react_url = st.session_state.get("cp_react_handoff_url")
            handoff_created = st.session_state.get("cp_react_handoff_created", 0)
            if not react_url or time.time() - handoff_created >= 240:
                react_url = backend_client.create_react_handoff()
                st.session_state["cp_react_handoff_url"] = react_url
                st.session_state["cp_react_handoff_created"] = time.time()
            st.link_button("Return to CropPulse React", react_url, use_container_width=True)
            if st.button("Refresh React sign-in link", key="refresh_react_handoff", use_container_width=True):
                st.session_state.pop("cp_react_handoff_url", None)
                st.session_state.pop("cp_react_handoff_created", None)
                st.rerun()
            st.caption("The secure sign-in link expires after 5 minutes and works once. Refresh it if you return here after using it.")
        except RuntimeError as exc:
            st.error(f"React sign-in handoff is unavailable: {exc}")
    elif backend_client.enabled():
        st.caption("Sign in to open your private farm workspace.")
    else:
        st.caption("Sign-in is required. Configure CROP_PULSE_API_URL to enable the account service.")
    with st.expander(t("session_controls", lang)):
        st.caption(t("session_notice", lang))
        if st.button(t("clear_session", lang), key="clear_session_data"):
            st.session_state["confirm_clear_frontend_data"] = True
        if st.session_state.get("confirm_clear_frontend_data"):
            st.warning(t("clear_warning", lang))
            confirm, cancel = st.columns(2)
            if confirm.button(t("confirm_clear", lang), key="confirm_clear_session"):
                frontend_services.clear_session_data()
                st.rerun()
            if cancel.button(t("cancel", lang), key="cancel_clear_session"):
                st.session_state.pop("confirm_clear_frontend_data", None)
                st.rerun()
    with st.expander(t("data_settings", lang)):
        years = sorted(df["year"].dropna().unique().tolist()) if not df.empty else []
        year = st.selectbox(t("analysis_year", lang), years[::-1]) if years else None
        st.multiselect(t("all_districts", lang), sorted(df.district.unique()), key="f_d", placeholder="All districts")
        st.multiselect(t("all_crops", lang), sorted(df.crop.unique()), key="f_c", placeholder="All crops")
        st.multiselect(t("all_seasons", lang), sorted(df.season.unique()), key="f_s", placeholder="All seasons")
        st.button(t("clear_filters", lang), on_click=lambda: [st.session_state.__setitem__(k, []) for k in ("f_d", "f_c", "f_s")])
        st.slider("Elevated: yield drop (%)", -50.0, -1.0, -15.0, key="e_drop"); st.slider("Elevated: variability CV (%)", 5.0, 60.0, 25.0, key="e_cv")
        st.slider("Watch: yield drop (%)", -50.0, -1.0, -8.0, key="w_drop"); st.slider("Watch: variability CV (%)", 5.0, 60.0, 15.0, key="w_cv")
        if st.button(t("reload_data", lang)):
            st.cache_data.clear(); st.rerun()
    if not df.empty and validate(df)["warnings"]:
        st.caption("⚠ Validation warnings: see Data Explorer.")
    st.caption(("DEMONSTRATION DATA in use" if status["state"] == "demo" else status["message"]) + " · v0.4")

fdf = apply_filters(df, st.session_state.get("f_d"), st.session_state.get("f_c"), st.session_state.get("f_s")) if not df.empty else df
pg.run()
