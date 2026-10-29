import pandas as pd
from utils.priority_analysis import classify, compute_priority


def _s(ys, area=100.0):
    return pd.DataFrame({"district": "A", "crop": "M", "season": "A", "year": range(2021, 2021 + len(ys)), "area_ha": area, "production_t": [y * area for y in ys]})


def test_cv_used_with_enough_periods():
    r = compute_priority(_s([2, 3, 2, 3, 2.9]), 2025).iloc[0]
    assert r.basis.startswith("Change + variability") and r.cv_pct > 15


def test_zero_baseline_not_misleading():
    r = compute_priority(_s([0.0, 2.0]), 2022).iloc[0]
    assert pd.isna(r["pct_change"]) and r.category == "Insufficient data"


def test_rules_override_changes_category():
    df = _s([2.0, 2.0, 1.8])  # -10%
    assert compute_priority(df, 2023).category.iloc[0] == "Watch"
    strict = {"Elevated": {"drop_pct": -5.0, "cv_pct": 99.0}, "Watch": {"drop_pct": -2.0, "cv_pct": 99.0}}
    assert compute_priority(df, 2023, rules=strict).category.iloc[0] == "Elevated"
    assert classify(-1.0, None) == "Stable"


def test_missing_values_not_zero():
    df = _s([2.0, 2.0, 2.0]); df.loc[1, "production_t"] = float("nan")
    r = compute_priority(df, 2023).iloc[0]
    assert r.periods_used == 2  # the missing year is excluded, not zero-filled


def test_seasons_are_never_mixed():
    a = _s([2.0, 2.0, 2.0]); b = _s([1.0, 1.0, 0.5]); b["season"] = "B"
    r = compute_priority(pd.concat([a, b]), 2023).set_index("season")
    assert r.loc["A", "reference_yield"] == 2.0 and r.loc["A", "category"] == "Stable"
    assert r.loc["B", "reference_yield"] == 1.0 and r.loc["B", "category"] == "Elevated"


def test_partial_production_not_divided_by_full_area():
    base = _s([2.0, 2.0])
    cur = pd.DataFrame({"district": "A", "crop": "M", "season": "A", "year": 2022, "area_ha": [10.0, 10.0], "production_t": [20.0, float("nan")]})
    r = compute_priority(pd.concat([base[base.year == 2021], cur]), 2022).iloc[0]
    assert r.current_yield == 2.0  # 20 t / 10 ha (the pair with data), not 20 t / 20 ha
