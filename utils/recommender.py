"""Explainable crop-decision engine.

Candidate windows, zone fit, altitude ranges and water requirements come from an
unverified CropPulse knowledge pack. They are provisional planning rules, not
verified Rwanda agronomic evidence. Ranking uses that provisional zone fit;
NISR history is descriptive context only and never ranks or excludes crops.
Hard constraints retain the existing configured range checks; unknown inputs
never trigger an exclusion. This ordering is not a probability of success.
"""
from datetime import date
from hashlib import sha256
import re
import numpy as np, pandas as pd
import knowledge as K
from utils.agronomy_knowledge import farmer_facing_guidance_for
from utils import geography as geo
from utils.metrics import aggregate, pct_change

MIN_PERIODS, ALT_MARGIN = 4, 200
GUIDANCE_SOURCE = K.GUIDANCE_SOURCE
FIT_WORDS = {3: "favorable", 2: "possible", 1: "limited"}
CANNOT_ASSESS = ["Verified crop-by-district planting guidance, soil requirements, water thresholds, and altitude limits are not loaded; the current CropPulse guide is provisional",
                 "Soil suitability for your plot: no plot-level soil test or verified soil requirement is loaded",
                 "Weather at your field: a separate point forecast is available, but it is not used to rank or time crops",
                 "Market prices and profitability"]


def validate_inputs(district, season, elevation=None):
    e = []
    if geo.normalize_district(district) is None:
        e.append(f"'{district}' is not a recognised Rwandan district.")
    if season not in K.SEASONS:
        e.append(f"'{season}' is not a valid season (A, B or C).")
    if elevation is not None and not 800 <= elevation <= 4600:
        e.append("Elevation must be between 800 and 4,600 m.")
    return e


def history(df, district, crop, season):
    if df is None or df.empty or "production_t" not in df:
        a = pd.DataFrame(columns=["year", "yield_t_ha"])
    else:
        d = df[(df.district == district) & (df.crop == crop) & (df.season == season)]
        a = aggregate(d, "year").dropna(subset=["yield_t_ha"]).sort_values("year") if len(d) else pd.DataFrame(columns=["year", "yield_t_ha"])
    y = [float(v) for v in a.yield_t_ha]; n = len(y)
    cv = float(np.std(y, ddof=1) / np.mean(y) * 100) if n >= MIN_PERIODS and np.mean(y) > 0 else None
    return {"n_periods": n, "years": [int(v) for v in a.year], "yields": y, "change_pct": pct_change(y[-1], y[-2]) if n >= 2 else None, "cv_pct": cv}


def _has_validated_nisr_provenance(status):
    """A generic 'validated' state alone does not establish NISR provenance."""
    if status.get("state") != "validated":
        return False
    return any(
        isinstance(source, dict)
        and "national institute of statistics of rwanda" in str(source.get("publisher", "")).casefold()
        and ("seasonal agricultural survey" in str(source.get("title", "")).casefold()
             or re.search(r"\bsas\b", str(source.get("title", "")).casefold()))
        and re.fullmatch(r"[0-9a-fA-F]{64}", str(source.get("sha256", "")))
        for source in status.get("provenance", [])
    )


def recommend(df, status, district, season, elevation=None, irrigation="Unknown", water="Unknown", month=None):
    errs = validate_inputs(district, season, elevation)
    base = {"errors": errs, "results": [], "no_window": [], "cannot_assess": CANNOT_ASSESS, "data_note": status.get("message", "")}
    if errs:
        return base
    district = geo.normalize_district(district); zone = K.DISTRICTS[district][0]; month = month or date.today().month
    context_token = sha256(f"{district}|{season}|{month}|{elevation}|{irrigation}|{water}|{status.get('state')}|{status.get('message')}".encode("utf-8")).hexdigest()[:12]
    state = status.get("state")
    # Unverified, incomplete, or warning datasets may still be shown as context,
    # but must not change crop ordering or trigger data-backed risk claims.
    nisr_source_checked = _has_validated_nisr_provenance(status)
    for crop, c in K.CROPS.items():
        if season not in c["plant"]:
            base["no_window"].append(crop); continue
        fit = c["suit"][zone]; reasons = [f"The provisional CropPulse guide places {crop} in its '{FIT_WORDS[fit]}' category for the broad {K.ZONES[zone]} grouping. This grouping is not an official agroecological classification."]; risks, viol, ev = [], [], []
        if elevation is None:
            risks.append("Elevation unknown: altitude fit was not checked.")
        else:
            lo, hi = c["alt"]
            if elevation < lo - ALT_MARGIN or elevation > hi + ALT_MARGIN:
                viol.append(f"The supplied elevation ({elevation:,.0f} m) is outside the unverified CropPulse guide range ({lo:,}–{hi:,} m). This is a provisional rule, not a verified Rwanda exclusion threshold.")
            elif not lo <= elevation <= hi:
                risks.append(f"The supplied elevation ({elevation:,.0f} m) is near the edge of the unverified CropPulse guide range ({lo:,}–{hi:,} m).")
            else:
                reasons.append(f"The supplied elevation ({elevation:,.0f} m) falls within the unverified CropPulse guide range ({lo:,}–{hi:,} m). This range has not been validated for your plot.")
        need = c["water"]
        if need == "High":
            if water == "Low" and irrigation != "Yes":
                viol.append("The provisional guide labels this crop high-water; reported water availability is low and irrigation is not reported. This rule is not a verified crop-specific water threshold.")
            elif irrigation == "Yes":
                reasons.append("Irrigation is reported; the provisional guide classifies this crop as high-water. Field supply and crop-specific needs are not verified.")
            else:
                risks.append("The provisional guide classifies this crop as high-water; irrigation or adequate water availability has not been confirmed.")
        elif need == "Medium" and water == "Low" and irrigation != "Yes":
            risks.append("Reported low water may conflict with the guide's unverified medium-water category; no yield effect is estimated.")
        h = history(df, district, crop, season); n = h["n_periods"]
        if n == 0:
            ev.append("No yield records for this district, crop and season in the loaded dataset.")
        else:
            qualifier = (" NISR estimates are not independently verified; these are descriptive historical context only, not agronomic decision evidence."
                         if nisr_source_checked else " Source provenance is not verified; shown for context only, not as agronomic decision evidence.")
            ev.append(f"{n} period(s) {h['years'][0]}–{h['years'][-1]}; latest calculated yield {h['yields'][-1]:.2f} t/ha." + qualifier)
            if n < MIN_PERIODS:
                ev.append(f"Historical variability is not calculated: {n} period(s) are below the {MIN_PERIODS}-period minimum.")
        if nisr_source_checked and n:
            evidence_basis = f"The NISR source file passed CropPulse checksum and structural checks, with {n} district/crop/season periods available. The survey estimates are not independently verified; they are descriptive historical context only and do not establish suitability, predict future yield, or affect this crop's rank."
        else:
            evidence_basis = "Suitability and rank are based on the provisional CropPulse guide, not validated agronomic evidence. No validated NISR district/crop/season history is available for this comparison."
        steps = ["Confirm varieties and planting dates with your extension officer.", "Get a local soil test.", "Check the weather forecast before sowing."]
        if n < MIN_PERIODS:
            steps.append("Collect more seasons of records for this district to judge stability.")
        res = dict(recommendation_id=f"rec_{context_token}_{crop.lower().replace(' ', '_')}", crop=crop, rw=c["rw"], fit=fit,
                   water_need=need, altitude_m_range=list(c["alt"]),
                   status="Excluded by a provisional CropPulse rule" if viol else {3: "Provisional guide fit: favorable", 2: "Provisional guide fit: possible", 1: "Provisional guide fit: limited"}[fit],
                   rank=None, reasons=reasons, risks=risks, violations=viol, evidence=ev, history=h, evidence_basis=evidence_basis, used_stats=False,
                   history_context_available=bool(nisr_source_checked and n),
                   window="Provisional CropPulse calendar months (not a verified planting recommendation): " + ", ".join(K.MONTHS[m - 1] for m in c["plant"][season]),
                   weak="The relative position rests on provisional general guidance; it is not a prediction of success.",
                   next_steps=steps, source=GUIDANCE_SOURCE,
                   evidence_record={"crop": crop, "district": district, "zone": K.ZONES[zone], "season": season,
                                    "guidance_source": GUIDANCE_SOURCE, "guidance_verification": "Provisional; no approved source-backed rule is available for this scope",
                                    "source_reference": None, "source_publication_date": None,
                                    "rule_status": "provisional_only", "approved_guidance": farmer_facing_guidance_for(crop, district, season),
                                    "source_applicability": f"Broad CropPulse grouping {K.ZONES[zone]} for district {district}; not an official zone mapping",
                                    "evidence_status": "provisional", "data_state": state, "statistics_used_for_ranking": False,
                                    "statistics_use": "Descriptive historical context only",
                                    "statistics_source": status.get("message", "No dataset provenance supplied"),
                                    "last_reviewed": None, "limitations": CANNOT_ASSESS.copy() + [
                                        "CropPulse zone fit, planting months, altitude ranges, and water categories are not locally verified.",
                                        "No crop-specific verified source record is available for this district and season."]})
        base["results"].append(res)
    ok = sorted([r for r in base["results"] if not r["violations"]], key=lambda r: (-r["fit"], r["crop"]))
    for i, r in enumerate(ok, 1):
        r["rank"] = i
    base["results"] = ok + [r for r in base["results"] if r["violations"]]
    return base
