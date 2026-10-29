import pandas as pd
from utils import recommender as R
from utils.exports import build_decision_brief

DEMO = {"state": "demo", "message": "demo"}
OFFICIAL = {"state": "validated", "message": "ok", "provenance": [{
    "title": "NISR SAS district crop area and production",
    "publisher": "National Institute of Statistics of Rwanda (NISR)",
    "sha256": "a" * 64,
}]}


def _hist(crop, ys, season="A", district="Huye"):
    return pd.DataFrame({"district": district, "crop": crop, "season": season, "year": range(2021, 2021 + len(ys)), "area_ha": 100.0, "production_t": [y * 100 for y in ys]})


def names(out): return [r["crop"] for r in out["results"] if r["rank"]]


def test_input_validation():
    assert R.recommend(pd.DataFrame(), DEMO, "Atlantis", "A")["errors"] and R.recommend(pd.DataFrame(), DEMO, "Huye", "Z")["errors"]
    assert R.recommend(pd.DataFrame(), DEMO, "Huye", "A", elevation=10)["errors"]


def test_unknown_inputs_exclude_nothing_and_are_disclosed():
    out = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10)
    assert "Rice" in names(out) and all(not r["violations"] for r in out["results"])
    rice = next(r for r in out["results"] if r["crop"] == "Rice")
    assert any("not been confirmed" in x for x in rice["risks"]) and any("Elevation unknown" in x for x in rice["risks"])


def test_elevation_hard_constraint():
    out = R.recommend(pd.DataFrame(), DEMO, "Musanze", "A", elevation=2600.0, month=10)
    assert "Maize" not in names(out) and "Irish potato" in names(out)
    assert any(r["crop"] == "Maize" and r["violations"] for r in out["results"])


def test_water_constraint_and_irrigation_override():
    low = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", irrigation="No", water="Low", month=10)
    assert "Rice" not in names(low)
    assert "Rice" in names(R.recommend(pd.DataFrame(), DEMO, "Huye", "A", irrigation="Yes", water="Low", month=10))


def test_historical_statistics_are_context_only_and_never_affect_crop_ranking():
    df = _hist("Beans", [1.0, 1.1, 1.0, 1.2, 1.1])
    base = names(R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10))
    assert names(R.recommend(df, DEMO, "Huye", "A", month=10)) == base
    pending = R.recommend(df, {"state": "pending", "message": "pending"}, "Huye", "A", month=10)
    assert names(pending) == base
    beans = next(r for r in pending["results"] if r["crop"] == "Beans")
    assert "not as agronomic decision evidence" in " ".join(beans["evidence"])
    assert names(R.recommend(df, {"state": "warning", "message": "warning"}, "Huye", "A", month=10)) == base
    official = R.recommend(df, OFFICIAL, "Huye", "A", month=10)
    assert names(official) == base
    beans = next(r for r in official["results"] if r["crop"] == "Beans")
    assert beans["history_context_available"] and not beans["used_stats"]
    assert "historical context only" in beans["evidence_basis"]
    assert "not independently verified" in beans["evidence_basis"]


def test_insufficient_periods_and_evidence_basis_wording():
    r = next(x for x in R.recommend(_hist("Maize", [2, 2, 2]), OFFICIAL, "Huye", "A", month=10)["results"] if x["crop"] == "Maize")
    assert r["history"]["cv_pct"] is None and not r["used_stats"]
    assert "variability is not calculated" in " ".join(r["evidence"])
    assert "confidence" not in r
    low = next(x for x in R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10)["results"])
    assert "provisional CropPulse guide" in low["evidence_basis"] and "not a prediction of success" in low["weak"]


def test_recommendations_identify_missing_source_provenance_and_provisional_applicability():
    result = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10)["results"][0]
    evidence = result["evidence_record"]
    assert result["status"].startswith("Provisional guide fit:")
    assert evidence["evidence_status"] == "provisional"
    assert evidence["source_reference"] is None and evidence["source_publication_date"] is None
    assert evidence["statistics_used_for_ranking"] is False
    assert "not an official zone mapping" in evidence["source_applicability"]
    assert evidence["rule_status"] == "provisional_only"
    assert evidence["approved_guidance"] == []


def test_generic_validated_state_does_not_claim_nisr_provenance_or_verified_estimates():
    status = {"state": "validated", "message": "generic structural checks passed", "provenance": []}
    result = next(item for item in R.recommend(_hist("Maize", [1.0]), status, "Huye", "A", month=10)["results"] if item["crop"] == "Maize")
    assert result["history_context_available"] is False
    assert result["evidence_record"]["rule_status"] == "provisional_only"
    assert result["evidence_record"]["approved_guidance"] == []
    assert "not independently verified" not in result["evidence_basis"]
    assert "Source provenance is not verified" in " ".join(result["evidence"])


def test_existing_rule_exclusion_is_retained_but_labelled_as_provisional():
    result = R.recommend(pd.DataFrame(), DEMO, "Musanze", "A", elevation=2600, month=10)
    maize = next(r for r in result["results"] if r["crop"] == "Maize")
    assert maize["violations"] and maize["status"] == "Excluded by a provisional CropPulse rule"


def test_observed_decline_flagged_for_official_data():
    r = next(x for x in R.recommend(_hist("Maize", [2, 2, 2, 2, 1.4]), OFFICIAL, "Huye", "A", month=10)["results"] if x["crop"] == "Maize")
    assert not any("Observed decline" in x for x in r["risks"])
    assert r["history"]["change_pct"] < 0 and r["history"]["cv_pct"] is not None
    assert "historical context only" in r["evidence_basis"]


def test_results_follow_inputs_and_are_deterministic():
    a = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10); b = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10)
    assert names(a) == names(b) and names(a) != names(R.recommend(pd.DataFrame(), DEMO, "Nyagatare", "A", month=10))
    assert "Wheat" not in names(R.recommend(pd.DataFrame(), DEMO, "Huye", "C", month=7))  # no Season C window


def test_brief_matches_results_and_discloses_demo():
    out = R.recommend(pd.DataFrame(), DEMO, "Huye", "A", month=10)
    md = build_decision_brief(out, "Huye", "A", "none", DEMO)
    assert "Huye" in md and "Season A" in md and names(out)[0] in md and "not a probability" in md and "demo" in md
