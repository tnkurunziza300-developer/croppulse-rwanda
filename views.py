"""Page layouts. Calculations live in utils/, not here."""
import numpy as np, pandas as pd, plotly.express as px, streamlit as st
from utils.metrics import aggregate, change_table, pct_change
from utils.priority_analysis import compute_priority, RULES, MIN_PERIODS
from utils.data_validation import validate
from utils.exports import to_csv_bytes, build_brief
from utils import geography as geo

GREENS = ["#14532d", "#3f9e5a", "#1d4ed8", "#b45309", "#6b7280", "#7c3aed"]
SRC = lambda df, y: st.markdown(f"<div class='cp-src'>Source: {df['data_origin'].iloc[0]} · Period: {y}</div>", unsafe_allow_html=True)


def card(col, label, value, note="", help=""):
    col.markdown(f"<div class='cp-card' title='{help}'><div class='l'>{label}</div><div class='v'>{value}</div><div class='n'>{note}</div></div>", unsafe_allow_html=True)


def fmt(v, unit="", d=0):
    return "n/a" if v is None or pd.isna(v) else f"{v:,.{d}f}{unit}"


def fmt_pct(v):
    return "n/a (no valid baseline)" if v is None or pd.isna(v) else f"{v:+.1f}%"


def active_rules():
    s = st.session_state
    return {"Elevated": {"drop_pct": s.get("e_drop", -15.0), "cv_pct": s.get("e_cv", 25.0)},
            "Watch": {"drop_pct": s.get("w_drop", -8.0), "cv_pct": s.get("w_cv", 15.0)}}


def _cmp(df, year, metric, cur_val):
    prior = [y for y in df.year.dropna().unique() if y < year]
    if not prior:
        return f"{year}; no earlier period to compare"
    py = max(prior); p = aggregate(df[df.year == py].assign(k=1), "k").iloc[0]
    return f"{year}; {fmt_pct(pct_change(cur_val, p[metric]))} vs {py}"


def _idx(opts, key):
    v = st.session_state.get(key)
    return opts.index(v) if v in opts else 0


def fig_style(f):
    f.update_layout(margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="white", plot_bgcolor="white", font=dict(size=13))
    return f


def show(f, desc):
    st.plotly_chart(fig_style(f), width="stretch")
    st.caption(desc)


def overview(df, year, status):
    st.subheader("Agricultural Intelligence for Rwanda")
    st.write("Explore crop production, yield patterns, seasonal changes, and potential agricultural priorities using transparent analytical methods.")
    st.info(f"**Question:** which crop–district–season combinations show meaningful changes, and how reliable is the evidence?  \n"
            f"**Data:** {status['message']} ({status.get('geography', {}).get('coverage_label', 'unknown coverage')}).  \n"
            "**Limitation:** flags are priorities for investigation, not diagnoses; no causes are tested.")
    with st.expander("How to use CropPulse (2-minute walkthrough)"):
        st.write("1. Check the data status in the sidebar and Data Explorer.  2. Filter by crop, district, season.  3. Compare periods on Crop Intelligence or Seasonal Trends.  "
                 "4. Open Risk & Priority and select a flagged record to see the calculation.  5. Build a brief on Decision Briefs.  6. Verify sources on Methodology.")
    cur = df[df.year == year]
    if cur.empty:
        st.info("No records match the current filters for this year."); return
    tot = aggregate(cur.assign(k=1), "k").iloc[0]
    pr = compute_priority(df, year, rules=active_rules()); flagged = int(pr.category.isin(["Elevated", "Watch"]).sum())
    c = st.columns(5)
    card(c[0], "Total crop production", fmt(tot.production_t, " t"), _cmp(df, year, "production_t", tot.production_t), "Sum of tonnes across crops; a mass total, not nutritional equivalence.")
    card(c[1], "Cultivated area", fmt(tot.area_ha, " ha"), _cmp(df, year, "area_ha", tot.area_ha))
    card(c[2], "Area-weighted yield", fmt(tot.yield_t_ha, " t/ha", 2), _cmp(df, year, "yield_t_ha", tot.yield_t_ha))
    card(c[3], "Districts · crops", f"{cur.district.nunique()} · {cur.crop.nunique()}", f"{year}")
    card(c[4], "Flagged for review", flagged, "Elevated or Watch (see Risk page)")
    st.write("")
    a, b = st.columns(2)
    with a:
        seas = st.selectbox("Season", ["All"] + sorted(cur.season.unique()), key="ov_s")
        d = cur if seas == "All" else cur[cur.season == seas]
        g = aggregate(d, "crop").sort_values("production_t")
        show(px.bar(g, x="production_t", y="crop", orientation="h", title="Production by crop (tonnes)", color_discrete_sequence=[GREENS[0]],
                    labels={"production_t": "Production (t)", "crop": ""}), "Sum of reported production per crop.")
        SRC(df, year)
    with b:
        crop = st.selectbox("Crop for yield trend", sorted(df.crop.unique()), key="ov_c")
        ds = st.multiselect("Compare districts (optional)", sorted(df.district.unique()), key="ov_d")
        t = aggregate(df[(df.crop == crop) & (df.district.isin(ds) if ds else True)], ["year"] + (["district"] if ds else []))
        if t.year.nunique() < 2:
            st.info("A trend needs at least two periods; only one is available.")
        else:
            show(px.line(t, x="year", y="yield_t_ha", color="district" if ds else None, markers=True, title=f"{crop}: yield (t/ha)",
                         labels={"yield_t_ha": "Yield (t/ha)", "year": "Year"}), "Area-weighted yield over the seasons in the current selection (annual aggregate). Use Seasonal Trends for same-season comparisons. Gaps are shown, not filled.")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Highlights")
        top = cur.dropna(subset=["production_t"]).nlargest(1, "production_t")
        if not top.empty:
            r = top.iloc[0]; st.write(f"• Largest production record: **{r.crop}**, {r.district}, season {r.season} {year}: {r.production_t:,.0f} t.")
        ch = pr.dropna(subset=["pct_change"])
        if not ch.empty:
            w = ch.nsmallest(1, "pct_change").iloc[0]
            st.write(f"• Largest yield decline vs {w.reference_year}: **{w.crop}**, {w.district}, Season {w.season}: {w["pct_change"]:+.1f}% ({w.reference_yield:.2f} → {w.current_yield:.2f} t/ha).")
        cc = cur.crop.value_counts().index[0]; yy = aggregate(cur[cur.crop == cc], "district").dropna(subset=["yield_t_ha"])
        if len(yy) > 1:
            hi, lo = yy.loc[yy.yield_t_ha.idxmax()], yy.loc[yy.yield_t_ha.idxmin()]
            st.write(f"• {cc} yield {year}: highest **{hi.district}** ({hi.yield_t_ha:.2f} t/ha), lowest **{lo.district}** ({lo.yield_t_ha:.2f} t/ha).")
        st.write(f"• Records with missing production or area in {year}: **{int(cur[['production_t', 'area_ha']].isna().any(axis=1).sum())}**.")
    with b:
        crop2 = st.selectbox("Crop for district ranking", sorted(df.crop.unique()), key="ov_c2")
        g = aggregate(cur[cur.crop == crop2], "district").dropna(subset=["yield_t_ha"]).sort_values("yield_t_ha")
        if g.empty:
            st.info("No yield data for this crop and period.")
        else:
            show(px.bar(g, x="yield_t_ha", y="district", orientation="h", title=f"{crop2}: yield by district, {year}", color_discrete_sequence=[GREENS[1]],
                        labels={"yield_t_ha": "Yield (t/ha)", "district": ""}), "Ranked bars used because no verified district boundary file is loaded (map omitted).")
    st.markdown("### Farmer information in this session")
    from utils import frontend_services
    own = frontend_services.farm_records()
    quotes = frontend_services.market_quotes()
    x, y, z = st.columns(3)
    x.metric("Session farm reports", len(own))
    y.metric("Harvest reports", int((own.record_type == "Harvest").sum()) if not own.empty else 0)
    z.metric("Session market observations", len(quotes))
    st.caption("User-entered context for this session only. It disappears when the session ends and is not representative or independently verified.")


def crop_intel(df, year, status):
    _o = sorted(df.crop.unique()); crop = st.selectbox("Crop (type to search)", _o, index=_idx(_o, "_crop"), key="intel_crop")
    seas = st.multiselect("Season", sorted(df.season.unique()), default=sorted(df.season.unique()), key="intel_seasons")
    d = df[(df.crop == crop) & df.season.isin(seas)]
    if d.empty:
        st.info("No records for this selection."); return
    cur = aggregate(d[d.year == year].assign(k=1), "k")
    cur = cur.iloc[0] if len(cur) else None
    prev_years = [y for y in sorted(d.year.unique()) if y < year]
    c = st.columns(4)
    if cur is None:
        st.warning(f"No {crop} records in {year}."); return
    card(c[0], "Production", fmt(cur.production_t, " t")); card(c[1], "Area", fmt(cur.area_ha, " ha"))
    card(c[2], "Yield", fmt(cur.yield_t_ha, " t/ha", 2)); card(c[3], "Observations", int(cur.observations), f"{d[d.year == year].district.nunique()} districts")
    if prev_years:
        py = prev_years[-1]; p = aggregate(d[d.year == py].assign(k=1), "k").iloc[0]
        ac = cur.yield_t_ha - p.yield_t_ha; pc = pct_change(cur.yield_t_ha, p.yield_t_ha)
        st.write(f"**Interpretation:** yield changed by **{ac:+.2f} t/ha** ({fmt_pct(pc)}) between {py} and {year}. "
                 "Absolute and percentage change are reported separately; this is an association in the data, not an explanation of cause.")
    t = aggregate(d, "year")
    if len(t) > 1:
        show(px.line(t, x="year", y="yield_t_ha", markers=True, title=f"{crop}: yield trend (t/ha)", color_discrete_sequence=[GREENS[0]]), "Years with no records are not interpolated.")
    g = aggregate(d[d.year == year], "district").sort_values("yield_t_ha", ascending=False)
    st.dataframe(g.rename(columns={"production_t": "Production (t)", "area_ha": "Area (ha)", "yield_t_ha": "Yield (t/ha)"}), width="stretch", hide_index=True)
    st.download_button("Download crop table (CSV)", to_csv_bytes(g, df["data_origin"].iloc[0]), f"{crop}_{year}.csv", "text/csv")
    SRC(df, year)


def district_explorer(df, year, status):
    c1, c2 = st.columns(2)
    metric = c2.selectbox("Metric", ["yield_t_ha", "production_t", "area_ha"], format_func=lambda m: {"yield_t_ha": "Yield (t/ha)", "production_t": "Production (t)", "area_ha": "Area (ha)"}[m], key="district_metric")
    _o = sorted(df.district.unique()); dist = c1.selectbox("District", _o, index=_idx(_o, "_district"), key="district_focus")
    st.caption(f"Province: {geo.DISTRICT_TO_PROVINCE.get(dist, 'Unknown')} (derived from the Rwanda district reference list)")
    d = df[(df.district == dist) & (df.year == year)]
    g = aggregate(d, "crop").sort_values(metric, ascending=False)
    if g.empty:
        st.info("No records for this district and year."); return
    st.markdown(f"#### {dist}: crop ranking, {year}")
    show(px.bar(g, x="crop", y=metric, color_discrete_sequence=[GREENS[0]], title=metric), f"{len(d)} records; coverage {g.crop.nunique()} crops.")
    ref = aggregate(df[df.year == year], "crop")[["crop", "yield_t_ha"]].rename(columns={"yield_t_ha": "selection_yield"})
    t2 = g.merge(ref, on="crop", how="left"); t2["vs_selection_pct"] = [pct_change(a, b) for a, b in zip(t2.yield_t_ha, t2.selection_yield)]
    st.dataframe(t2.round(2), width="stretch", hide_index=True)
    st.caption("Reference = all districts currently selected in the sidebar filters (not a national statistic).")
    st.markdown("#### Compare districts")
    crop = st.selectbox("Crop", sorted(df.crop.unique()), key="district_compare_crop"); sel = st.multiselect("Districts", sorted(df.district.unique()), default=[dist], key="district_compare_list")
    if len(sel) < 2:
        st.info("Select two or more districts to compare."); return
    t = aggregate(df[(df.crop == crop) & df.district.isin(sel)], ["district", "year"])
    show(px.line(t, x="year", y=metric, color="district", markers=True, title=f"{crop}: {metric}"), "Same crop, metric and units across districts.")


def seasonal(df, year, status):
    c = st.columns(3)
    crop = c[0].selectbox("Crop", sorted(df.crop.unique()), key="seasonal_crop"); metric = c[1].selectbox("Metric", ["production_t", "area_ha", "yield_t_ha"], key="seasonal_metric")
    seas = c[2].selectbox("Season", sorted(df.season.unique()), key="seasonal_season")
    d = df[(df.crop == crop) & (df.season == seas)]
    base = year - 1
    if base not in d.year.values:
        st.info(f"No {base} data for season {seas}; year-on-year comparison unavailable."); return
    t = change_table(d, ["district"], metric, year, base)
    t["pct_change"] = t["pct_change"].astype(float)
    st.dataframe(t, width="stretch", hide_index=True)
    st.caption(f"Season {seas}, {base} → {year}. Blank % = zero or missing baseline. Possible causes (rainfall, inputs, pests) are hypotheses and are not tested here.")
    miss = t[t.current.isna() | t.previous.isna()].district.tolist()
    if miss:
        st.warning("Missing in one of the two periods (not treated as zero): " + ", ".join(miss))
    mv = t.dropna(subset=["pct_change"])
    if not mv.empty:
        w = mv.loc[mv["pct_change"].abs().idxmax()]
        st.write(f"**Largest change:** {crop} in {w.district}, {metric}: {w.previous:,.2f} → {w.current:,.2f} ({w['pct_change']:+.1f}%) between {base} and {year}, season {seas}. "
                 "Limitation: two points only; no explanatory variables are loaded, so causes remain hypotheses.")
    st.markdown("#### Cross-season comparison within the same year (not a year-on-year change)")
    st.dataframe(aggregate(df[(df.crop == crop) & (df.year == year)], "season").round(2), width="stretch", hide_index=True)
    s = aggregate(df[df.crop == crop], ["year", "season"])
    show(px.line(s, x="year", y=metric, color="season", markers=True, title=f"{crop}: {metric} by season"), "Season A and B are not directly interchangeable.")


def risk(df, year, status):
    pr = compute_priority(df, year, rules=active_rules())
    cats = st.multiselect("Category", pr.category.unique().tolist(), default=[x for x in pr.category.unique() if x != "Stable"], key="risk_categories")
    t = pr[pr.category.isin(cats)]
    st.dataframe(t.round(2), width="stretch", hide_index=True)
    st.download_button("Download table (CSV)", to_csv_bytes(t, df["data_origin"].iloc[0]), "priority.csv", "text/csv")
    if t.empty:
        st.info("Nothing matches these filters."); return
    with st.expander("How thresholds work", expanded=False):
        st.write("Adjust the sidebar sliders: stricter thresholds flag fewer records. All pages use the same thresholds.")
    labels = (t.district + " · " + t.crop + " · Season " + t.season).tolist(); pick = st.selectbox("Explain a record", labels, key="risk_record")
    r = t.iloc[labels.index(pick)]
    st.markdown("#### Why this record is flagged")
    st.write(f"**{r.category}** (Season {r.season}, same-season comparison; an observed pattern, not a forecast): {r.basis}. Current yield {fmt(r.current_yield, ' t/ha', 2)} vs {fmt(r.reference_yield, ' t/ha', 2)} in {r.reference_year}; change {fmt_pct(r["pct_change"])}; variability (CV) {fmt(r.cv_pct, '%', 1)}.")
    st.caption(f"Provisional analytical settings, not NISR classifications. Rule: Elevated if change ≤ {active_rules()['Elevated']['drop_pct']}% or CV ≥ {active_rules()['Elevated']['cv_pct']}%; Watch if change ≤ {active_rules()['Watch']['drop_pct']}% or CV ≥ {active_rules()['Watch']['cv_pct']}%. CV needs ≥ {MIN_PERIODS} periods; otherwise change-only. Insufficient evidence is never rated high or low.")
    h = aggregate(df[(df.district == r.district) & (df.crop == r.crop) & (df.season == r.season)], "year")
    st.markdown("**Observations used**"); st.dataframe(h.round(2), width="stretch", hide_index=True)
    with st.expander("Suggested follow-up (investigative, not causal)"):
        st.write("• Verify with other agricultural records\n• Check whether cultivated area changed\n• Consult district agricultural officers\n• Review rainfall/climate records if available")


def data_explorer(df, year, status):
    c = st.columns(4)
    f = df
    for col, k in zip(c, ["district", "crop", "season", "year"]):
        sel = col.multiselect(k.title(), sorted(df[k].unique()), key=f"explorer_filter_{k}"); f = f[f[k].isin(sel)] if sel else f
    q = st.text_input("Search text fields")
    if q:
        f = f[f[["district", "crop"]].apply(lambda s: s.str.contains(q, case=False)).any(axis=1)]
    cols = st.multiselect("Columns", list(f.columns), default=list(f.columns), key="explorer_columns") or list(f.columns)
    f = f[cols]
    st.dataframe(f, width="stretch", hide_index=True)
    st.download_button("Download filtered CSV", to_csv_bytes(f, df["data_origin"].iloc[0]), "filtered.csv", "text/csv")
    v = validate(df)
    st.caption(f"Coverage (current filters): years {v.get('years', 'n/a')}, {v.get('districts', 0)} districts. Units: area in hectares, production in tonnes; a unit column is not present, so unit mix-ups cannot be detected.")
    st.markdown("#### Data quality")
    m = st.columns(3); m[0].metric("Rows", v["rows"]); m[1].metric("Columns", v["cols"]); m[2].metric("Duplicate keys", v["duplicates"])
    st.write(f"Duplicates removed on load: **{status.get('duplicates_removed', 0)}**. Missing values are kept as blanks, never zero.")
    st.dataframe(v["missing"].rename("missing").to_frame(), width="stretch")
    for w in v["warnings"]:
        st.warning(w)
    g = status.get("geography")
    if g:
        st.markdown("#### Rwanda geography validation")
        st.write(f"**{g['coverage_label']}.** Provinces are derived from the verified district mapping.")
        st.dataframe(pd.DataFrame({"province": list(g["by_province"]), "districts_present": list(g["by_province"].values()),
                                   "districts_in_province": [len(geo.PROVINCE_DISTRICTS[p]) for p in g["by_province"]]}), hide_index=True)
        if g["unknown"]:
            st.warning("Unrecognised district names (quarantined): " + ", ".join(g["unknown"]))
    q = status.get("quarantine")
    if q is not None and len(q):
        st.warning(f"{len(q)} records quarantined (not analysed); reasons below.")
        st.dataframe(q, hide_index=True)
    st.markdown("#### Source and provenance"); st.json(status.get("provenance", []))
    st.caption("Dictionary: district, crop, season (A/B), year, area_ha (hectares), production_t (tonnes), yield_t_ha (= production_t ÷ area_ha, derived).")


def briefs(df, year, status):
    c = st.columns(2)
    crop = c[0].selectbox("Crop", sorted(df.crop.unique()), key="brief_crop"); dist = c[1].selectbox("District", ["All districts"] + sorted(df.district.unique()), key="brief_district")
    d = df if dist == "All districts" else df[df.district == dist]
    d = d[d.crop == crop]; cur = aggregate(d[d.year == year].assign(k=1), "k")
    if cur.empty:
        st.info("No records for this selection."); return
    r = cur.iloc[0]; findings = [f"{crop} production in {year}: {r.production_t:,.0f} t over {r.area_ha:,.0f} ha (yield {r.yield_t_ha:.2f} t/ha)."]
    pr = compute_priority(df, year, rules=active_rules()); pr = pr[pr.crop == crop] if dist == "All districts" else pr[(pr.crop == crop) & (pr.district == dist)]
    for _, x in pr[pr.category.isin(["Elevated", "Watch"])].iterrows():
        findings.append(f"{x.district}, Season {x.season}: yield {x["pct_change"]:+.1f}% vs {x.reference_year} → {x.category}.")
    chosen = st.multiselect("Findings to include", findings, default=findings, key="brief_findings")
    md = build_brief(f"Decision brief: {crop}", dist, crop, str(year), chosen, df["data_origin"].iloc[0],
                     ["Associations are not causes.", "Historical data does not guarantee future outcomes.", f"Data status: {status['message']}", "Priority categories use provisional analytical thresholds, not NISR classifications."])
    st.markdown(md); st.download_button("Download brief (Markdown)", md, f"brief_{crop}_{year}.md", "text/markdown")


def methodology(df, year, status):
    st.markdown("""
**Problem.** Agricultural statistics are hard to scan; CropPulse helps users spot patterns and decide what to investigate.
**Users.** Planners, analysts, researchers, development staff, extension officers.

**Data.** Currently: *Illustrative sample data, not official statistics* unless a CSV is placed in `data/verified/`. Intended source: NISR Seasonal Agricultural Survey outputs, converted to the documented schema. Record acquisition date when you add them.

**Calculations.** Yield = production ÷ area. Aggregate yield divides total production by total area using only records where both are present and area > 0 (area-weighted). The area column must match the NISR indicator definition (cultivated vs harvested) before use. Absolute change = current − previous; percentage change is withheld when the baseline is zero or missing.

**Priority rule.** Compare the selected year with the latest earlier year of the same crop, district AND season (seasons are never mixed). With ≥ 4 periods, also compute the coefficient of variation (SD ÷ mean of yields). Elevated: change ≤ −15% or CV ≥ 25%. Watch: change ≤ −8% or CV ≥ 15%. These thresholds are illustrative, adjustable in `utils/priority_analysis.py`, and not validated against NISR standards.

**Missing data.** Never filled with zero. Only exact duplicate rows are dropped; rows sharing a key but differing elsewhere are kept and flagged. Records with unknown districts, invalid seasons (A/B/C only), invalid years, province conflicts or incompatible units are quarantined with reasons, not deleted silently.\n\n**Rwanda validation.** District names are matched case-insensitively to the 30-district reference list; provinces are derived from it. Coverage is reported as Rwanda-wide, partial or unknown. **Trust states:** demonstration, validation pending, warnings, validated (needs a manifest with matching checksum). **Forecasting:** not implemented; the available data do not support a validated model.

**Research questions.** Where did yield change most between comparable periods? Which district–crop series are volatile? Where is evidence too thin to judge?

**Validation.** Required-column check; duplicate-key check; non-positive area and negative production warnings; unit tests for every calculation (`python -m pytest tests`).

**Thresholds.** Adjustable in the sidebar; every page uses the same values.

**Future improvements.** Verified NISR data, district boundaries for a choropleth, rainfall and market covariates, PDF export.

**Recommendation engine.** Crop Decisions applies hard constraints (altitude, water) from your inputs, ranks by guidance fit for the district's zone, then evidence strength, then variability. Statistics influence ranking only when official data (not demonstration data) has 4+ periods. Evidence strength counts available support; it is not a probability. Planting windows are CropPulse-compiled guidance, unverified by RAB/NISR. Soil, weather and prices are not assessed.

**Limitations & ethics.** Flags indicate where to look, not that a location is failing. No causal claims. Briefs are template-generated, not AI-written.
""")
