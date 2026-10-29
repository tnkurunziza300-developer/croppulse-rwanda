"""Frontend-only farmer workflows; mutable data exists only for this session."""
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
import knowledge as K
from utils import geography as geo
from utils import frontend_services as services
from utils import weather as weather_service
from backend import client as backend_client
from utils.i18n import t
from utils.seasonal_plan import build_plan


def _lang(): return st.session_state.get("cp_language", "en")


def _plan_markdown(p):
    e = p["evidence"]
    lines = [f"# Crop plan: {p['crop']} in {p['district']}", f"Date created: {date.today():%Y-%m-%d}",
             f"Planting target: {p['planting_date']:%Y-%m-%d}; Season {p['season']}; field {p['area_ha']:g} ha", "",
             f"**Evidence:** {e['verification_status']} · {e['evidence_status']}", f"**Source:** {e['source']}", "", "## Activities"]
    for a in p["activities"]:
        lines += [f"### {a['stage']} — {a['timing']}", a["activity"], f"Reason: {a['reason']}",
                  f"Conditions: {a['conditions']}", f"Resources: {a['resources']}", f"Caution: {a['warning']}", f"Evidence: {a['evidence']}", ""]
    lines += ["## Limitations"] + [f"- {x}" for x in e["limitations"]]
    return "\n".join(lines)


def crop_plan_page():
    lang = _lang(); st.title(t("plan", lang))
    st.caption("Create a field-specific checklist. Current CropPulse crop guidance is provisional and not locally verified." if lang == "en" else
               "Kora urutonde rw'ibikorwa bijyanye n'umurima wawe. Amakuru ya CropPulse ni ay'agateganyo kandi ntiyaremezwa mu karere.")
    with st.form("seasonal_crop_plan"):
        a, b, c = st.columns(3)
        district = a.selectbox(t("district", lang), geo.ALL_DISTRICTS, index=geo.ALL_DISTRICTS.index(st.session_state.get("_district", "Huye")))
        crop = b.selectbox(t("crop", lang), list(K.CROPS), index=list(K.CROPS).index(st.session_state.get("_crop", "Maize")))
        season = c.selectbox(t("season", lang), list(K.SEASONS), index=list(K.SEASONS).index(st.session_state.get("_season", K.season_for(date.today().month))),
                             format_func=lambda s: f"{s}: {K.SEASONS[s]}")
        d, e, f = st.columns(3)
        planting = d.date_input(t("planting", lang), value=date.today() + timedelta(days=7))
        area_units = ["hectares (ha)", "are (100 m²)", "square metres"]
        area_unit_names = {"hectares (ha)": t("hectares", lang), "are (100 m²)": t("ares", lang), "square metres": t("square_metres", lang)}
        area_unit = e.selectbox(t("area_unit", lang), area_units, format_func=lambda value: area_unit_names[value])
        area = f.number_input(t("area", lang), min_value=0.01, value=0.5, step=0.1)
        d, e = st.columns(2)
        water_options = ["Unknown", "Low", "Medium", "High"]
        irrigation_options = ["Unknown", "Yes", "No"]
        soil_options = ["Unknown", "Soil test available", "Farmer description only"]
        water = d.selectbox(t("water", lang), water_options, format_func=lambda v: t("choice_" + v.lower().replace(" ", "_"), lang))
        irrigation = d.selectbox(t("irrigation_choice", lang), irrigation_options, format_func=lambda v: t("choice_" + v.lower(), lang))
        soil = e.selectbox(t("soil", lang), soil_options, format_func=lambda v: t("soil_" + v.lower().replace(" ", "_"), lang))
        submitted = st.form_submit_button(t("build_plan", lang), type="primary", width="stretch")
    if submitted:
        try:
            st.session_state["cp_plan"] = build_plan(crop, district, season, planting, K.to_ha(float(area), area_unit), water, irrigation, soil)
            st.session_state["cp_plan_error"] = ""
            st.session_state["_crop"], st.session_state["_district"], st.session_state["_season"] = crop, district, season
        except ValueError as exc:
            st.session_state["cp_plan_error"] = str(exc)
    if st.session_state.get("cp_plan_error"):
        st.error(st.session_state["cp_plan_error"])
    p = st.session_state.get("cp_plan")
    if not p:
        st.info(t("build_plan_hint", lang))
        return
    if not p["window_fit"]:
        st.warning(f"The selected month is outside CropPulse's indicative planting months for Season {p['season']}. This calendar is unverified; confirm locally.")
    st.subheader(f"{p['crop']} · {p['district']} · {p['province']} · {p['area_ha']:g} ha")
    st.info(t("provisional", lang))
    with st.expander("Recommendation evidence / Amakuru y'icyifashishwa", expanded=True):
        st.write(f"**Source:** {p['evidence']['source']}")
        st.write(f"**Status:** {p['evidence']['verification_status']} · **Review:** {p['evidence']['expert_review_status']} · **Last reviewed:** Not recorded")
        st.write(f"**Applicability:** {p['crop']}; {p['district']} ({p['zone']}); Season {p['season']}.")
        st.write("**Evidence availability:** The source is provisional and farm-level measurements are missing; this is not a probability of success.")
    with st.expander(t("previous_records", lang)):
        st.caption("Farmer reports entered in this session are personal context only. They are not independently verified and do not affect crop ranking.")
        try:
            past = services.farm_records()
            if past.empty:
                st.info("No farm records in this session yet. Use Farm Records to capture activities and outcomes.")
            else:
                past = past[(past.crop == p["crop"]) & (past.district == p["district"])]
                if past.empty: st.info("No session records match this crop and district yet.")
                else: st.dataframe(past[["record_date", "season", "record_type", "quantity", "unit", "amount_rwf", "status"]], hide_index=True, width="stretch")
        except Exception as exc: st.info(f"Local records are unavailable: {exc}")
    for i, item in enumerate(p["activities"]):
        with st.container(border=True):
            st.markdown(f"**{i+1}. {item['stage']} — {item['timing']}**")
            st.write(item["activity"])
            st.caption(f"Why: {item['reason']}")
            st.caption(f"Conditions: {item['conditions']} · Resources: {item['resources']}")
            st.warning(item["warning"])
            st.caption("Evidence: " + item["evidence"])
    md = _plan_markdown(p)
    st.download_button("Download crop plan (Markdown)", md, f"crop_plan_{p['district']}_{p['crop']}.md", "text/markdown")
    if st.button(t("save_plan", lang), key="save_crop_plan"):
        try:
            services.add_crop_plan(p)
            if backend_client.enabled() and st.session_state.get("cp_access_token"):
                st.success("Crop plan and farm activity saved to your account.")
            else:
                services.add_farm_record(record_date=p["planting_date"].isoformat(), district=p["district"], crop=p["crop"], season=p["season"],
                                 record_type="Seasonal plan", area_ha=p["area_ha"], unit="ha", notes=md)
                st.success("Crop plan added to this session. It is not permanently saved.")
        except Exception as exc:
            st.error(f"Could not save crop plan: {exc}")
    if st.button(t("track_crop", lang), key="track_crop_from_plan"):
        st.session_state["_crop"], st.session_state["_district"], st.session_state["_season"] = p["crop"], p["district"], p["season"]
        st.session_state["record_crop"], st.session_state["record_district"], st.session_state["record_season"] = p["crop"], p["district"], p["season"]
        pages = st.session_state.get("_pages", {})
        if "farm_records" in pages:
            st.switch_page(pages["farm_records"])

    st.markdown("### " + t("weather", lang))
    st.info(t("no_live_weather", lang) + " The plan remains available without a forecast.")


RECORD_TYPES = ["Planting", "Seasonal plan", "Farm activity", "Input used", "Crop-health observation", "Harvest", "Production cost", "Challenge", "Recommendation feedback", "Reviewer submission"]
RECORD_TYPE_KEYS = {"Planting": "record_planting", "Seasonal plan": "record_plan", "Farm activity": "record_activity", "Input used": "record_input",
                    "Crop-health observation": "record_health", "Harvest": "record_harvest", "Production cost": "record_cost", "Challenge": "record_challenge",
                    "Recommendation feedback": "record_feedback", "Reviewer submission": "record_review"}


def farm_records_page():
    lang = _lang(); st.title(t("records", lang))
    st.warning(t("farm_data_warning", lang))
    with st.form("farm_record_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        record_type = a.selectbox(t("record_type", lang), RECORD_TYPES, format_func=lambda value: t(RECORD_TYPE_KEYS[value], lang))
        record_date = b.date_input(t("record_date", lang), value=date.today())
        districts = geo.ALL_DISTRICTS
        selected_district = st.session_state.get("_district", "Huye")
        district = c.selectbox(t("district", lang), districts, index=districts.index(selected_district) if selected_district in districts else 0, key="record_district")
        a, b, c = st.columns(3)
        crops, seasons = list(K.CROPS), list(K.SEASONS)
        selected_crop, selected_season = st.session_state.get("_crop", "Maize"), st.session_state.get("_season", "A")
        crop = a.selectbox(t("crop", lang), crops, index=crops.index(selected_crop) if selected_crop in crops else 0, key="record_crop")
        season = b.selectbox(t("season", lang), seasons, index=seasons.index(selected_season) if selected_season in seasons else 0, key="record_season")
        area = c.number_input(t("area", lang) + " (ha; 0 if not applicable)", min_value=0.0, value=0.0, step=0.1)
        a, b, c = st.columns(3)
        quantity = a.number_input(t("quantity", lang) + " (optional; 0 if not applicable)", min_value=0.0, value=0.0, step=1.0)
        unit = b.selectbox(t("unit", lang), ["not applicable", "kg", "tonnes", "litres", "bags", "items"])
        amount = c.number_input(t("amount", lang) + " (0 if not applicable)", min_value=0.0, value=0.0, step=1000.0)
        severity = st.selectbox("Observation severity (not a diagnosis)", ["Not applicable", "Mild", "Moderate", "Severe"],
                                disabled=record_type != "Crop-health observation")
        notes = st.text_area(t("notes", lang), max_chars=2000)
        submitted = st.form_submit_button(t("add_record", lang), type="primary")
    if submitted:
        try:
            detail = notes.strip()
            if record_type == "Crop-health observation":
                detail = f"Severity reported: {severity}. This is not a diagnosis. " + detail
            services.add_farm_record(record_date=record_date.isoformat(), district=district, crop=crop, season=season, record_type=record_type,
                             area_ha=area or None, quantity=quantity or None, unit=None if unit == "not applicable" else unit,
                             amount_rwf=amount or None, notes=detail)
            if backend_client.enabled() and st.session_state.get("cp_access_token"):
                st.success("Farm activity saved to your account. It remains farmer-reported.")
            else:
                st.success("Added to this session only. " + t("farmer_reported", lang))
        except (ValueError, OSError, RuntimeError) as exc: st.error(f"Could not save record: {exc}")
    try:
        records = services.farm_records()
    except RuntimeError as exc:
        st.error(f"Farm records could not be loaded: {exc}")
        return
    if records.empty:
        st.info(t("empty_records", lang)); return
    st.markdown("### " + t("farm_summary", lang))
    x, y, z = st.columns(3)
    x.metric("Records", len(records)); y.metric("Districts recorded", records.district.nunique())
    harvest = records[records.record_type == "Harvest"]
    z.metric("Harvest entries", len(harvest))
    if backend_client.enabled() and st.session_state.get("cp_access_token"):
        st.caption("These are farmer-reported records for the selected farm. They are private account data, not district or national statistics.")
    else:
        st.caption("These counts summarize only records entered in this session. They are not district or national statistics.")
    st.dataframe(records.drop(columns=["notes"]), hide_index=True, width="stretch")
    if not harvest.empty:
        st.markdown("### " + t("harvest_summary", lang))
        measured = harvest.dropna(subset=["quantity"]).copy()
        measured = measured[measured.unit.notna() & (measured.unit != "")]
        if measured.empty:
            st.info("Add harvest quantity and unit to a Harvest record to see performance summaries.")
        else:
            grouped = measured.groupby(["crop", "unit"], as_index=False).agg(entries=("id", "count"), reported_quantity=("quantity", "sum"))
            st.caption("Quantities are grouped by crop and unit; kg, bags, and other units are never combined.")
            st.dataframe(grouped, hide_index=True, width="stretch")
            crop_choice = st.selectbox("Harvest history crop", sorted(measured.crop.unique()), key="harvest_history_crop")
            selected_harvest = measured[measured.crop == crop_choice]
            unit_choices = sorted(selected_harvest.unit.unique())
            unit_choice = st.selectbox("Harvest unit", unit_choices, key="harvest_history_unit")
            timeline = selected_harvest[selected_harvest.unit == unit_choice].sort_values("record_date")
            if len(timeline) > 1:
                st.plotly_chart(px.bar(timeline, x="record_date", y="quantity", title=f"Farmer-reported {crop_choice} harvest ({unit_choice})",
                                       labels={"record_date": "Harvest date", "quantity": f"Quantity ({unit_choice})"}), width="stretch")
            else:
                st.caption("Add another matching harvest entry to see a time comparison.")
    st.download_button(t("export_records", lang), services.csv_bytes(records), "croppulse_farm_records.csv", "text/csv")
    with st.expander(t("edit_delete", lang)):
        choices = {f"#{r.id} · {r.record_date} · {r.crop} · {r.record_type}": (r.id if isinstance(r.id, str) else int(r.id)) for r in records.itertuples()}
        label = st.selectbox(t("choose_record", lang), list(choices))
        rid = choices[label]; row = records[records.id == rid].iloc[0]
        with st.form(f"edit_record_{rid}"):
            a, b, c = st.columns(3)
            edit_date = a.date_input("Date", value=date.fromisoformat(row.record_date), key=f"edate{rid}")
            edit_type = b.selectbox(t("record_type", lang), RECORD_TYPES, index=RECORD_TYPES.index(row.record_type) if row.record_type in RECORD_TYPES else 0,
                                    key=f"etype{rid}", format_func=lambda value: t(RECORD_TYPE_KEYS[value], lang))
            edit_district = c.selectbox("District", geo.ALL_DISTRICTS, index=geo.ALL_DISTRICTS.index(row.district), key=f"edist{rid}")
            a, b, c = st.columns(3)
            edit_crop = a.selectbox("Crop", list(K.CROPS), index=list(K.CROPS).index(row.crop), key=f"ecrop{rid}")
            edit_season = b.selectbox("Season", list(K.SEASONS), index=list(K.SEASONS).index(row.season), key=f"eseas{rid}")
            old_area = 0.0 if pd.isna(row.area_ha) else float(row.area_ha)
            edit_area = c.number_input("Area (ha)", min_value=0.0, value=old_area, key=f"earea{rid}")
            a, b, c = st.columns(3)
            old_quantity = 0.0 if pd.isna(row.quantity) else float(row.quantity)
            edit_quantity = a.number_input("Quantity", min_value=0.0, value=old_quantity, key=f"eqty{rid}")
            edit_unit = b.text_input("Unit", value=row.unit or "", key=f"eunit{rid}")
            old_amount = 0.0 if pd.isna(row.amount_rwf) else float(row.amount_rwf)
            edit_amount = c.number_input("Amount (RWF)", min_value=0.0, value=old_amount, key=f"eamt{rid}")
            edit_notes = st.text_area("Notes", value=row.notes, key=f"enotes{rid}")
            save = st.form_submit_button(t("save_changes", lang))
        if save:
            try:
                services.update_farm_record(rid, record_date=edit_date.isoformat(), district=edit_district, crop=edit_crop, season=edit_season,
                                    record_type=edit_type, area_ha=edit_area or None, quantity=edit_quantity or None,
                                    unit=edit_unit or None, amount_rwf=edit_amount or None, notes=edit_notes)
                st.success("Farm activity updated."); st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(f"Could not update activity: {exc}")
        if st.button(t("delete_record", lang), key=f"del_record{rid}"):
            st.session_state["confirm_delete_record"] = rid
        if st.session_state.get("confirm_delete_record") == rid:
            st.warning("This removes the record from this session.")
            yes, no = st.columns(2)
            if yes.button(t("confirm_delete", lang), key=f"confirmdel{rid}"):
                try:
                    services.delete_farm_record(rid); st.session_state.pop("confirm_delete_record", None); st.rerun()
                except RuntimeError as exc:
                    st.error(f"Could not delete activity: {exc}")
            if no.button(t("cancel", lang), key=f"canceldelete{rid}"): st.session_state.pop("confirm_delete_record", None); st.rerun()


def market_economics_page():
    lang = _lang(); st.title(t("markets", lang))
    st.info(t("market_unavailable", lang))
    with st.form("market_quote_form", clear_on_submit=True):
        st.markdown("### " + t("market_quote", lang))
        a, b, c = st.columns(3)
        crop = a.selectbox(t("crop", lang), list(K.CROPS))
        market = b.text_input(t("market", lang), placeholder="Market name or town")
        observed = c.date_input(t("observation_date", lang), value=date.today())
        a, b, c = st.columns(3)
        price = a.number_input(t("price", lang), min_value=0.0, value=0.0, step=10.0)
        unit = b.selectbox(t("price_unit", lang), ["kg", "tonne", "bag (specify in source)"])
        source = c.text_input(t("source", lang), placeholder="Person, bulletin, or document")
        submit = st.form_submit_button(t("save_price", lang))
    if submit:
        try:
            services.add_market_quote(crop, market, observed, price, unit, source)
            st.success("Added to this session as user-entered and unverified.")
        except ValueError as exc: st.error(str(exc))
    quotes = services.market_quotes()
    if quotes.empty: st.info(t("empty_quotes", lang))
    else:
        quote_dates = pd.to_datetime(quotes.observed_on, errors="coerce").dt.date
        date_bounds = (min(quote_dates), max(quote_dates))
        chosen_dates = st.date_input(t("observation_range", lang), value=date_bounds, key="market_date_range")
        if isinstance(chosen_dates, (tuple, list)) and len(chosen_dates) == 2:
            visible_quotes = quotes[(quote_dates >= chosen_dates[0]) & (quote_dates <= chosen_dates[1])]
        else:
            visible_quotes = quotes
        st.dataframe(visible_quotes.drop(columns=["created_in_session", "status"], errors="ignore"), hide_index=True, width="stretch")
        st.download_button(t("export_quotes", lang), services.csv_bytes(quotes), "market_observations.csv", "text/csv")
        crop_prices = st.selectbox("Crop price history", sorted(visible_quotes.crop.unique()) if not visible_quotes.empty else sorted(quotes.crop.unique()), key="quote_history_crop")
        crop_quotes = visible_quotes[visible_quotes.crop == crop_prices]
        if crop_quotes.empty:
            st.info("No observations match this date range.")
            crop_quotes = quotes[quotes.crop == crop_prices]
        market_choice = st.selectbox("Market for trend", sorted(crop_quotes.market.unique()), key="quote_history_market")
        market_quotes = crop_quotes[crop_quotes.market == market_choice]
        unit_choice = st.selectbox("Unit for trend", sorted(market_quotes.unit.unique()), key="quote_history_unit")
        series = market_quotes[market_quotes.unit == unit_choice]
        if len(series) >= 2:
            st.plotly_chart(px.line(series.sort_values("observed_on"), x="observed_on", y="price_rwf", markers=True,
                                    title=f"User-entered {crop_prices} prices · {series.market.iloc[0]} ({series.unit.iloc[0]})",
                                    labels={"observed_on": "Observed date", "price_rwf": "Price (RWF)"}), width="stretch")
        else:
            st.caption("Price trend needs at least two observations for the same crop, market, and unit.")
        qid = st.selectbox("Delete a local price observation", quotes.id.tolist(), format_func=lambda i: f"#{i} · {quotes.loc[quotes.id == i, 'crop'].iloc[0]} · {quotes.loc[quotes.id == i, 'market'].iloc[0]}")
        if st.button("Delete selected price observation"):
            st.session_state["delete_quote_id"] = int(qid)
        if st.session_state.get("delete_quote_id") == qid:
            st.warning("Delete this local observation?")
            if st.button("Confirm price deletion", key="confirm_quote_delete"):
                services.delete_market_quote(int(qid)); st.session_state.pop("delete_quote_id", None); st.rerun()

    st.markdown("### " + t("estimate_title", lang))
    st.caption(t("estimate_hint", lang))
    a, b, c, d = st.columns(4)
    crop2 = a.selectbox("Crop for estimate", list(K.CROPS), key="econ_crop")
    area = b.number_input("Area (ha)", min_value=0.0, value=0.5, step=0.1, key="econ_area")
    price2 = c.number_input(t("assumed_price", lang), min_value=0.0, value=0.0, step=10.0, key="econ_price")
    variable_cost = d.number_input(t("known_costs", lang), min_value=0.0, value=0.0, step=1000.0, key="econ_cost")
    if area > 0 and price2 > 0:
        harvest = K.estimate(crop2, area)["harvest_kg"]
        if harvest:
            revenue = (harvest[0] * price2, harvest[1] * price2)
            st.write(f"**Estimated gross revenue:** RWF {revenue[0]:,.0f}–{revenue[1]:,.0f}")
            st.write(f"**Estimated gross margin:** RWF {revenue[0]-variable_cost:,.0f}–{revenue[1]-variable_cost:,.0f} (gross revenue minus the variable costs you entered).")
            st.caption("Gross margin is not net profit. It excludes costs you did not enter, including labor, land, finance, storage, and transport. Harvest range is unverified CropPulse guidance.")
        else: st.info("This crop has no indicative yield range in CropPulse, so revenue is not estimated.")


def review_queue_page():
    st.title("Agronomy review submissions")
    st.warning("This is a local, unauthenticated submission queue. A submitted name or qualification is self-reported; no user can approve or mark guidance as verified here.")
    st.write("Use this workflow to collect crop-specific corrections and supporting sources for a later qualified review. It does not change any crop guidance.")
    with st.form("review_note_form"):
        a, b, c = st.columns(3)
        target = a.selectbox("Crop guidance to review", list(K.CROPS))
        review_district = b.selectbox("Applicable district", geo.ALL_DISTRICTS, key="review_district")
        review_season = c.selectbox("Applicable season", list(K.SEASONS), key="review_season")
        reviewer = st.text_input("Reviewer name and qualification (self-reported)")
        note = st.text_area("Suggested correction or evidence source")
        request = st.form_submit_button("Add review submission to this session")
    if request and not note.strip():
        st.error("Enter a suggested correction or supporting source.")
    if request and note.strip():
        services.add_review_submission(submitted_on=date.today().isoformat(), district=review_district, crop=target, season=review_season,
                         reviewer=reviewer or "not supplied", note=note.strip())
        st.success("Added to this session as an unauthenticated note; it does not change guidance or evidence status.")
    entries = services.review_submissions()
    if not entries.empty:
        st.markdown("### Session review notes")
        st.dataframe(entries, hide_index=True, width="stretch")
        st.download_button("Export review notes (CSV)", services.csv_bytes(entries), "crop_guidance_review_notes.csv", "text/csv")


def extension_notes_page():
    lang = _lang(); st.title(t("extension", lang))
    st.warning(t("session_only", lang) + " " + t("extension_message", lang))
    with st.form("extension_note_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        visit_date = a.date_input(t("visit_date", lang), value=date.today())
        district = b.selectbox("District", geo.ALL_DISTRICTS, key="extension_district")
        crop = c.selectbox("Crop", list(K.CROPS), key="extension_crop")
        a, b = st.columns(2)
        officer = a.text_input(t("officer", lang))
        farmer_ref = b.text_input(t("farmer_ref", lang))
        issue = st.text_area(t("issue", lang), max_chars=1500)
        action = st.text_area(t("follow_up", lang), max_chars=1500)
        submit = st.form_submit_button(t("add_visit", lang), type="primary")
    if submit:
        if not issue.strip():
            st.error("Enter the farmer-reported question or issue.")
        else:
            services.add_extension_note(visit_date=visit_date.isoformat(), district=district, crop=crop,
                                        officer=officer.strip(), farmer_ref=farmer_ref.strip(),
                                        issue=issue.strip(), action=action.strip())
            st.success("Visit note added to this session.")
    notes = services.extension_notes()
    if not notes.empty:
        st.dataframe(notes, hide_index=True, width="stretch")
        st.download_button("Export visit notes (CSV)", services.csv_bytes(notes), "extension_visit_notes.csv", "text/csv")


def pest_reporting_page():
    lang = _lang(); st.title(t("pest", lang))
    st.warning(t("report_unverified", lang))
    with st.form("pest_report_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        observed = a.date_input(t("observation_date", lang), value=date.today())
        district = b.selectbox("District", geo.ALL_DISTRICTS, key="pest_district")
        crop = c.selectbox(t("affected_crop", lang), list(K.CROPS), key="pest_crop")
        severity = st.select_slider(t("severity", lang), ["Few plants", "Several plants", "Many plants", "Field-wide"])
        description = st.text_area(t("symptoms", lang), max_chars=2000)
        action = st.text_area(t("actions_taken", lang), max_chars=1000)
        submit = st.form_submit_button(t("add_report", lang), type="primary")
    if submit:
        try:
            services.add_pest_report(observed_on=observed.isoformat(), district=district, crop=crop,
                                     severity=severity, description=description.strip(), action=action.strip())
            st.success("Report added to this session. No diagnosis or notification was sent.")
        except ValueError as exc:
            st.error(str(exc))
    reports = services.pest_reports()
    if reports.empty:
        st.info("No crop-health reports in this session yet.")
    else:
        st.dataframe(reports, hide_index=True, width="stretch")
        st.download_button("Export crop-health reports (CSV)", services.csv_bytes(reports), "crop_health_reports.csv", "text/csv")


def feedback_page():
    lang = _lang(); st.title(t("feedback", lang))
    st.info(t("feedback_message", lang))
    context = st.session_state.get("cp_feedback_context")
    with st.form("recommendation_feedback_form", clear_on_submit=True):
        if context:
            crop, district, season = context["crop"], context["district"], context["season"]
            st.caption(f"Recommendation #{context.get('rank') or '—'} · {crop} · {district} · Season {season} · {context.get('evidence_basis', 'Evidence basis not recorded')} · reference {context['recommendation_id']}")
        else:
            st.caption("No recommendation is linked. Submit general feedback, or open this form from a recommendation card to attach its reference.")
            a, b = st.columns(2)
            crops = list(K.CROPS); districts = geo.ALL_DISTRICTS
            crop = a.selectbox("Crop recommendation", crops, index=crops.index(st.session_state.get("_crop")) if st.session_state.get("_crop") in crops else 0)
            district = b.selectbox("District", districts, index=districts.index(st.session_state.get("_district")) if st.session_state.get("_district") in districts else 0, key="feedback_district")
            seasons = list(K.SEASONS)
            season = st.selectbox(t("season", lang), seasons, index=seasons.index(st.session_state.get("_season")) if st.session_state.get("_season") in seasons else 0)
        rating = st.radio(t("rating", lang), ["useful", "not useful", "unclear", "unsafe"], horizontal=True)
        message = st.text_area(t("what_to_know", lang), max_chars=1500)
        submit = st.form_submit_button(t("add_feedback", lang))
    if submit:
        recommendation_id = context["recommendation_id"] if context else None
        services.add_feedback(recommendation_id=recommendation_id, crop=crop, district=district, season=season,
                              rating=rating, message=message.strip(), submitted_on=date.today().isoformat())
        st.session_state.pop("cp_feedback_context", None)
        st.success("Feedback added to this session.")
    feedback = services.recommendation_feedback()
    if feedback.empty:
        st.info("No feedback submitted in this session yet.")
    else:
        st.dataframe(feedback, hide_index=True, width="stretch")
        st.download_button("Export feedback (CSV)", services.csv_bytes(feedback), "recommendation_feedback.csv", "text/csv")


def _request_weather_forecast(latitude, longitude):
    """Keep slow provider requests visibly separate from the rendered result."""
    with st.spinner("Requesting forecast from Open-Meteo…"):
        return weather_service.get_forecast(latitude, longitude)


def weather_page():
    lang = _lang(); st.title(t("weather_climate", lang))
    st.caption("Forecasts are model estimates for the farm coordinates you enter. The district list's total and province distribution match NISR's 2022 boundary-service metadata; district names have not been compared record-by-record. Sector selection and point-in-boundary matching are not yet implemented.")
    with st.form("weather_forecast_form"):
        district = st.selectbox("District (context only)", geo.ALL_DISTRICTS, key="weather_district")
        st.caption(f"Province reference: {geo.DISTRICT_TO_PROVINCE[district]} · administrative metadata: {geo.ADMIN_REFERENCE_VINTAGE} (checked {geo.ADMIN_METADATA_CHECKED_ON}).")
        st.warning("Enter the coordinates of your farm. The coordinates are checked against the NISR boundary layer's rectangular extent, but CropPulse does not yet verify that the point falls inside Rwanda or the selected district. Coordinates are sent to Open-Meteo when you request a forecast.")
        a, b = st.columns(2)
        latitude = a.text_input("Farm latitude", placeholder="For example: -2.50", key="weather_latitude")
        longitude = b.text_input("Farm longitude", placeholder="For example: 29.90", key="weather_longitude")
        requested = st.form_submit_button("Get 7-day forecast", type="primary")
    if requested:
        forecast = _request_weather_forecast(latitude.strip(), longitude.strip())
        st.session_state["weather_forecast_result"] = forecast
        st.session_state["weather_forecast_request"] = (district, latitude.strip(), longitude.strip())
    current_request = (district, latitude.strip(), longitude.strip())
    saved_request = st.session_state.get("weather_forecast_request")
    if saved_request and current_request != saved_request:
        st.session_state.pop("weather_forecast_result", None)
        st.session_state.pop("weather_forecast_request", None)
    forecast = st.session_state.get("weather_forecast_result")
    if forecast:
        if forecast.get("status") == "available":
            st.success("Forecast available · model forecast · not a current observation")
        elif forecast.get("status") == "stale":
            age = forecast.get("cache_age_seconds")
            age_label = f" Cached forecast age: {age // 3600} h {(age % 3600) // 60} min." if isinstance(age, int) else " Cached forecast age is unknown."
            st.warning("STALE FORECAST. This is not current provider data." + age_label)
        else:
            st.error(forecast.get("message", "Forecast unavailable."))
        if forecast.get("status") in ("available", "stale"):
            retrieved = forecast.get("retrieved_at", "Unknown")
            st.caption(f"Retrieved: {retrieved} (UTC) · Source: {forecast.get('source', 'Unknown')} · {forecast.get('attribution', '')}")
            st.caption(f"Location: provider grid point {forecast.get('coordinates', {}).get('latitude')}, {forecast.get('coordinates', {}).get('longitude')} · selected district {district} (farmer-selected context, not verified).")
            st.info(forecast.get("message", ""))
            rows = forecast.get("daily_forecast", [])
            if rows:
                display = [{"Forecast date": row.get("date"), "Maximum temperature (°C)": row.get("temperature_max_c"),
                            "Minimum temperature (°C)": row.get("temperature_min_c"), "Precipitation sum (mm/day)": row.get("precipitation_sum_mm")} for row in rows]
                st.dataframe(pd.DataFrame(display), hide_index=True, width="stretch")
            else:
                st.warning("The provider returned no daily forecast rows.")
    else:
        st.info("No forecast requested. Enter farm coordinates to continue. Forecasts are not used in CropPulse recommendations.")
    st.markdown("### " + t("local_observation", lang))
    st.caption("Enter a reading you personally observed from a gauge or thermometer. These are not official climate records or a forecast.")
    with st.form("weather_observation_form", clear_on_submit=True):
        observed = st.date_input(t("observation_date", lang), value=date.today())
        has_rain = st.checkbox(t("rain_gauge", lang), key="weather_has_rain")
        rainfall = st.number_input("Rainfall (mm)", min_value=0.0, value=0.0, disabled=not has_rain)
        has_temp = st.checkbox(t("temperature_readings", lang), key="weather_has_temp")
        a, b = st.columns(2)
        temp_min = a.number_input(t("min_temp", lang), value=0.0, disabled=not has_temp)
        temp_max = b.number_input(t("max_temp", lang), value=0.0, disabled=not has_temp)
        source = st.text_input(t("observation_source", lang))
        submit = st.form_submit_button(t("add_local_observation", lang))
    if submit:
        try:
            services.add_weather_observation(observed_on=observed.isoformat(), district=district,
                                             rainfall_mm=rainfall if has_rain else None,
                                             temperature_min_c=temp_min if has_temp else None,
                                             temperature_max_c=temp_max if has_temp else None,
                                             source=source.strip())
            st.success("Observation added to this session as unverified user-entered data.")
        except ValueError as exc:
            st.error(str(exc))
    observations = services.weather_observations()
    if not observations.empty:
        st.dataframe(observations, hide_index=True, width="stretch")
        st.download_button("Export local observations (CSV)", services.csv_bytes(observations), "weather_observations.csv", "text/csv")
    st.caption("The planning checklist remains available without weather. Confirm sowing timing with local observations and qualified extension advice.")


def cooperative_page():
    lang = _lang(); st.title(t("cooperative_log", lang))
    st.warning("Session-only planning aid. Use aggregate counts; do not enter member names, phone numbers, or other personal data. It is not shared with a cooperative.")
    with st.form("cooperative_activity_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        date_recorded = a.date_input(t("meeting_date", lang), value=date.today())
        district = b.selectbox(t("district", lang), geo.ALL_DISTRICTS, key="coop_district")
        crop = c.selectbox(t("crop", lang), list(K.CROPS), key="coop_crop")
        a, b, c = st.columns(3)
        season = a.selectbox(t("season", lang), list(K.SEASONS), key="coop_season")
        members = b.number_input(t("members_reached", lang), min_value=0, step=1)
        area = c.number_input(t("area_discussed", lang), min_value=0.0, step=0.1)
        topic = st.text_area(t("shared_issue", lang), max_chars=1500)
        action = st.text_area(t("agreed_next", lang), max_chars=1000)
        submit = st.form_submit_button(t("add_coop_activity", lang))
    if submit:
        try:
            services.add_cooperative_note(activity_date=date_recorded.isoformat(), district=district, crop=crop,
                                          season=season, members_reached=int(members), area_ha=float(area),
                                          topic=topic.strip(), action=action.strip())
            st.success("Activity added to this session.")
        except ValueError as exc:
            st.error(str(exc))
    notes = services.cooperative_notes()
    if notes.empty:
        st.info("No cooperative activities in this session yet.")
    else:
        st.dataframe(notes, hide_index=True, width="stretch")
        st.download_button(t("export_coop", lang), services.csv_bytes(notes), "cooperative_activity_log.csv", "text/csv")
