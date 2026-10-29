"""Planning pages for everyday users."""
from datetime import date
import pandas as pd, plotly.express as px, plotly.graph_objects as go, streamlit as st
import knowledge as K
from utils import geography as geo
from views import card, fig_style
from utils.i18n import t

NOTE = "CropPulse crop-guide values are approximate and have not been locally verified or approved by a qualified Rwanda specialist. Soil, variety, water and local conditions matter; confirm with an agricultural extension officer before acting."
STARS = {1: "★☆☆", 2: "★★☆", 3: "★★★"}


def _pick(container, label, options, key, state, default):
    v = st.session_state.get(state, default)
    r = container.selectbox(label, options, index=options.index(v) if v in options else 0, key=key)
    st.session_state[state] = r
    return r


def district_box(c, k): return _pick(c, t("district", st.session_state.get("cp_language", "en")), geo.ALL_DISTRICTS, f"d_{k}", "_district", "Huye")
def crop_box(c, k, label="Crop"):
    label = t("crop", st.session_state.get("cp_language", "en")) if label == "Crop" else label
    return _pick(c, label, list(K.CROPS), f"c_{k}", "_crop", "Maize")
def season_box(c, k): return _pick(c, t("season", st.session_state.get("cp_language", "en")), list(K.SEASONS), f"s_{k}", "_season", K.season_for(date.today().month))


def _go(label, key, page, crop=None, district=None, recommendation=None):
    pages = st.session_state.get("_pages")
    if pages and st.button(label, key=key):
        if crop: st.session_state["_crop"] = crop
        if district: st.session_state["_district"] = district
        if page == "feedback" and recommendation:
            st.session_state["cp_feedback_context"] = {
                "recommendation_id": recommendation["recommendation_id"],
                "crop": recommendation["crop"],
                "district": recommendation["evidence_record"]["district"],
                "season": recommendation["evidence_record"]["season"],
                "rank": recommendation.get("rank"),
                "evidence_basis": recommendation.get("evidence_basis"),
            }
        st.switch_page(pages[page])


def _card(r, d, status, i):
    with st.container(border=True):
        h = st.columns([5, 3, 3]); h[0].markdown(f"### #{r['rank']} {r['crop']} ({r['rw']})"); h[1].markdown(f"**{r['status']}**"); h[2].markdown("**Evidence basis**")
        st.caption(r["evidence_basis"])
        st.write(f"**Planting window:** {r['window']}")
        for x in r["reasons"]: st.write("• " + x)
        for x in r["risks"]: st.write("⚠ " + x)
        if r["weak"]: st.caption(r["weak"])
        with st.expander("Evidence, sources and next steps"):
            h = r["history"]; demo = status["state"] == "demo"
            for x in r["evidence"]: st.write("• " + x)
            if h["n_periods"] >= 2:
                f = px.line(pd.DataFrame({"Year": h["years"], "Yield (t/ha)": h["yields"]}), x="Year", y="Yield (t/ha)", markers=True,
                            title=f"{r['crop']} in {d}: calculated yield" + (" (DEMONSTRATION DATA)" if demo else ""), color_discrete_sequence=["#14532d"])
                st.plotly_chart(fig_style(f), width="stretch", key=f"ev_{i}")
            st.write("**Planting guidance source:** " + r["source"]); st.write("**Next steps:** " + " ".join(r["next_steps"]))
            evr = r.get("evidence_record", {})
            if evr:
                st.caption(f"Applicability: {evr.get('crop')} · {evr.get('district')} ({evr.get('zone')}) · Season {evr.get('season')}. Guidance: {evr.get('guidance_verification')}. External source/date: not recorded. NISR statistics used for ranking: {evr.get('statistics_used_for_ranking')}.")
                if evr.get("approved_guidance"):
                    for rule in evr["approved_guidance"]:
                        st.write(f"**Approved for defined scope · {rule['category'].replace('_', ' ')}:** {rule.get('recommendation') or 'See source details.'}")
                        st.caption(f"{rule['geography']['type']}: {', '.join(rule['geography'].get('scope', [])) or 'Rwanda-wide'} · Seasons {', '.join(rule['season_scope'])} · Revalidate by {rule['revalidate_by']}")
                        for ref in rule["source_references"]:
                            st.markdown(f"[{ref.get('organization')}: {ref.get('title')} · {ref['locator']}]({ref.get('url')}) — {ref['paraphrase']}")
                else:
                    st.info("No approved, source-backed agronomic rule is loaded for this crop, district, and season. This comparison uses provisional CropPulse rules; NISR statistics are historical context only.")
                if evr.get("data_state") in ("pending", "warning", "demo"):
                    st.warning("The loaded statistics are not fully validated; they may be visible here as context but did not affect ranking.")
            _go("Open full crop guide", f"g_{i}", "analytics", r["crop"], d)
            _go("Build a detailed field plan", f"cp_{i}", "crop_plan", r["crop"], d)
            _go("Give feedback", f"fb_{i}", "feedback", r["crop"], d, r)


def decisions(df, status):
    from utils import recommender as R
    from utils.data_loader import SAMPLE_LABEL
    from utils.exports import build_decision_brief
    month = date.today().month; cur = K.season_for(month)
    lang = st.session_state.get("cp_language", "en")
    hero = "<div class='hero'><h2>" + t("hero_heading", lang) + "</h2><p>" + t("hero", lang) + "</p></div>"
    st.markdown(hero, unsafe_allow_html=True)
    st.write("")
    if status["state"] == "demo": st.warning(SAMPLE_LABEL + " Statistics shown are illustrations and do not affect the ranking.")
    c = st.columns(2); d = district_box(c[0], "dec")
    seas = c[1].selectbox(t("season", lang), list(K.SEASONS), index=list(K.SEASONS).index(st.session_state.get("_season", cur)), format_func=lambda s: f"Season {s}: {K.SEASONS[s]}", key="s_dec"); st.session_state["_season"] = seas
    with st.expander(t("conditions", lang)):
        e = st.columns(3); known = e[0].checkbox(t("know_elevation", lang)); elev = e[0].number_input(t("elevation", lang), 800, 4600, 1700, disabled=not known)
        irr = e[1].radio(t("irrigation", lang), ["Unknown", "Yes", "No"], horizontal=True); water = e[2].selectbox(t("water_availability", lang), ["Unknown", "Low", "Medium", "High"])
    out = R.recommend(df, status, d, seas, float(elev) if known else None, irr, water, month)
    if out["errors"]: st.error(" ".join(out["errors"])); return
    z = K.DISTRICTS[d][0]; st.subheader(f"{d} · {geo.DISTRICT_TO_PROVINCE[d]} Province · {K.ZONES[z]} · Season {seas}")
    st.caption(f"Today: {date.today():%d %B %Y} (Season {cur}). Data: {out['data_note']}")
    ranked = [r for r in out["results"] if r["rank"]]
    if not ranked: st.info(f"No crop remains after the current provisional calendar and rule checks for Season {seas}. This does not establish that other crops cannot be grown locally.")
    for i, r in enumerate(ranked): _card(r, d, status, i)
    ex = [r for r in out["results"] if not r["rank"]]
    if ex:
        with st.expander(f"Excluded by provisional rules ({len(ex)})"):
            for r in ex: st.write(f"**{r['crop']}**: " + " ".join(r["violations"]))
    if out["no_window"]:
        with st.expander("Crops with no month entry in the provisional guide"):
            st.write(", ".join(out["no_window"]))
            st.caption("No entry is not evidence that a crop is unsuitable in your location.")
    with st.expander(t("cannot_assess", lang)):
        for x in out["cannot_assess"]: st.write("• " + x)
    inputs = f"elevation {elev if known else 'unknown'} m; irrigation {irr}; water {water}"
    st.download_button(t("download_brief", lang), build_decision_brief(out, d, seas, inputs, status), f"decision_brief_{d}_{seas}.md", "text/markdown")
    st.caption("Ranking follows the provisional CropPulse zone-guide category, then crop name. NISR statistics are historical context only and do not affect crop suitability or rank. This is not a probability of success. " + NOTE)


def crop_guide(heading=True):
    if heading: st.title("Crop Guide")
    st.caption("Provisional CropPulse guide entries for one crop. They are not locally verified recommendations.")
    k = crop_box(st, "guide"); v = K.CROPS[k]
    st.subheader(f"{k} · {v['rw']}")
    c = st.columns(4)
    card(c[0], "Indicative duration (unverified)", f"{v['days'][0]}-{v['days'][1]} d", "guide estimate; perennial first harvest later" if v["perennial"] else "guide estimate from planting")
    card(c[1], "Altitude range (unverified)", f"{v['alt'][0]}-{v['alt'][1]} m", "CropPulse guide range"); card(c[2], "Relative water category (unverified)", v["water"], "CropPulse guide")
    s = v["seed"]; card(c[3], "Indicative planting material (unverified) / ha", f"{s[0]:,}-{s[1]:,}", s[2])
    y = pd.DataFrame({"Broad CropPulse grouping": [K.ZONES[z] for z in "HWCE"], "Guide category (1-3)": [v["suit"][z] for z in "HWCE"]})
    fit_chart = px.bar(y, x="Guide category (1-3)", y="Broad CropPulse grouping", orientation="h", title="Unverified CropPulse guide categories (not local suitability findings)", color_discrete_sequence=["#3f9e5a"], range_x=[0, 3])
    fit_chart.update_xaxes(tickmode="array", tickvals=[1, 2, 3], ticktext=["Limited (provisional)", "Possible (provisional)", "Favorable (provisional)"])
    st.plotly_chart(fig_style(fit_chart), width="stretch")
    if v["ys"]:
        st.write(f"**Unverified CropPulse yield estimates (not NISR observations or a yield forecast):** smallholder {v['ys'][0]}-{v['ys'][1]} t/ha; with good practice {v['yg'][0]}-{v['yg'][1]} t/ha.")
    st.write("**Indicative planting months from the unverified CropPulse guide:** " + "; ".join(f"Season {s}: " + ", ".join(K.MONTHS[m - 1] for m in ms) for s, ms in v["plant"].items()))
    for t in v["tips"]:
        st.write("• " + t)
    st.info(NOTE)


def calendar():
    st.title("Season Calendar"); st.caption("Calendar symbols: P = planting, \u25b2 = growing, H = harvest (approximate). Entries come from the unverified CropPulse guide; they are not locally approved dates or a weather forecast. Source: " + K.GUIDANCE_SOURCE + ".")
    c = st.columns(2); d = district_box(c[0], "cal"); only = c[1].checkbox("Only crops with a possible or favorable provisional guide category", value=True)
    z = K.DISTRICTS[d][0]; keys = [k for k, v in K.CROPS.items() if (v["suit"][z] >= 2 or not only)]
    m = K.calendar_matrix(keys); sym = {0: "", 1: "P", 2: "▲", 3: "H"}
    fig = go.Figure(go.Heatmap(z=list(m.values()), x=K.MONTHS, y=keys, text=[[sym[x] for x in r] for r in m.values()], texttemplate="%{text}",
                               colorscale=[[0, "#f3f0e6"], [0.34, "#1d4ed8"], [0.67, "#9ccf9f"], [1, "#b45309"]], zmin=0, zmax=3, showscale=False, xgap=2, ygap=2,
                               hovertemplate="%{y} · %{x}<extra></extra>"))
    fig.update_yaxes(autorange="reversed"); fig.update_layout(height=60 + 38 * len(keys), title=f"Calendar for the {K.ZONES[z]} zone")
    st.plotly_chart(fig_style(fig), width="stretch"); st.info("This calendar filters using CropPulse's broad, unverified zone categories and season entries. A blank month or omitted crop is not evidence that it cannot be grown locally. " + NOTE)


def planner():
    st.title("Farm Planner"); st.caption("Indicative seed and harvest estimates are calculated from the unverified CropPulse guide, not a local yield forecast. You supply any prices and costs.")
    a = st.columns(3); d = district_box(a[0], "pl"); k = crop_box(a[1], "pl"); seas = season_box(a[2], "pl")
    b = st.columns(4); val = b[0].number_input("Field size", min_value=0.0, value=0.5, step=0.1); unit = b[1].selectbox("Unit", ["hectares (ha)", "are (100 m²)", "square metres"])
    lvl = b[2].selectbox("Management", ["smallholder", "good practice"]); price = b[3].number_input("Price you expect (RWF/kg)", min_value=0.0, value=0.0, step=10.0)
    cost = st.number_input("Total expected cost (RWF)", min_value=0.0, value=0.0, step=1000.0)
    ha = K.to_ha(val, unit); z = K.DISTRICTS[d][0]; e = K.estimate(k, ha, lvl); fit = K.CROPS[k]["suit"][z]
    if val <= 0:
        st.info("Enter a field size above zero."); return
    if fit == 1:
        st.warning(f"The provisional CropPulse guide assigns {k} its limited category for the broad {K.ZONES[z]} grouping. This is not a verified local suitability finding.")
    st.write(f"**Provisional CropPulse planting window:** {K.window_status(k, seas, date.today().month)}; indicative harvest {K.harvest_text(k, seas, date.today().month)}. These are guide estimates, not locally verified dates or a forecast.")
    c = st.columns(3); s = e["seed"]
    card(c[0], "Indicative planting material (guide estimate)", f"{s[0]:,.0f}-{s[1]:,.0f}", s[2] + f" for {ha:.3f} ha")
    h = e["harvest_kg"]; card(c[1], "Indicative harvest range (unverified)", "n/a" if h is None else f"{h[0]:,.0f}-{h[1]:,.0f} kg", "CropPulse guide estimate, " + lvl if h else "no estimate: long-term cash crop")
    if h and price > 0:
        card(c[2], "Indicative gross income", f"{h[0] * price:,.0f}-{h[1] * price:,.0f}", f"RWF from your price and an unverified harvest estimate; net of entered cost: {h[0] * price - cost:,.0f} to {h[1] * price - cost:,.0f}")
    else:
        card(c[2], "Indicative gross income", "n/a", "enter a price per kg")
    md = f"# Farm plan\n- District: {d} ({K.ZONES[z]})\n- Crop: {k}, Season {seas}\n- Field: {val} {unit} ({ha:.3f} ha)\n- Planting material: {s[0]:,.0f}–{s[1]:,.0f} {s[2]}\n- Harvest range: {'n/a' if h is None else f'{h[0]:,.0f}–{h[1]:,.0f} kg'}\n\n**Estimate limits:** Planting material and harvest range come from the unverified CropPulse guide; the harvest range is not a local yield forecast. Any income calculation uses your entered price and these indicative values.\n\n{NOTE}\n"
    st.download_button("Download my plan (Markdown)", md, f"plan_{d}_{k}.md", "text/markdown"); st.info(NOTE)


def districts(heading=True):
    if heading: st.title("District Map")
    st.caption("All 30 districts. Dots show approximate district centres; colors show provisional CropPulse guide categories for broad groupings, not verified district suitability.")
    k = crop_box(st, "map", "Show provisional guide category for crop"); v = K.CROPS[k]
    df = pd.DataFrame([dict(district=d, province=geo.DISTRICT_TO_PROVINCE[d], zone=K.ZONES[z], lat=la, lon=lo, fit=v["suit"][z], s=1) for d, (z, la, lo) in K.DISTRICTS.items()])
    df["Provisional guide category"] = df.fit.map({3: "Favorable (provisional)", 2: "Possible (provisional)", 1: "Limited (provisional)"})
    fn = getattr(px, "scatter_map", None)
    kw = dict(lat="lat", lon="lon", color="Provisional guide category", size="s", size_max=14, hover_name="district", hover_data={"province": True, "zone": True, "s": False, "lat": False, "lon": False, "Provisional guide category": False}, zoom=6.6, center={"lat": -1.95, "lon": 29.9}, color_discrete_map={"Favorable (provisional)": "#14532d", "Possible (provisional)": "#b45309", "Limited (provisional)": "#9ca3af"}, category_orders={"Provisional guide category": ["Favorable (provisional)", "Possible (provisional)", "Limited (provisional)"]})
    fig = fn(df, map_style="carto-positron", **kw) if fn else px.scatter_mapbox(df, mapbox_style="carto-positron", **kw)
    fig.update_layout(height=520); st.plotly_chart(fig_style(fig), width="stretch")
    st.dataframe(df[["district", "province", "zone", "Provisional guide category"]].sort_values(["Provisional guide category", "district"]), hide_index=True, width="stretch")
    st.caption("Map colors show provisional CropPulse guide categories for broad groupings; they are not verified district suitability. Zones are not an official classification. " + NOTE)
