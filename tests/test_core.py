import numpy as np, pandas as pd, pytest
from utils.metrics import pct_change, aggregate
from utils.priority_analysis import compute_priority, classify
from utils.data_loader import clean, make_sample
from utils.data_validation import validate


def test_pct_change():
    assert pct_change(110, 100) == pytest.approx(10.0)
    assert pct_change(5, 0) is None and pct_change(5, None) is None and pct_change(np.nan, 3) is None


def test_weighted_yield_and_missing():
    df = pd.DataFrame({"k": [1, 1], "production_t": [10.0, np.nan], "area_ha": [5.0, 5.0]})
    g = aggregate(df, "k").iloc[0]
    assert g.production_t == 10 and g.area_ha == 10 and g.yield_t_ha == 2.0 and g.yield_pairs == 1  # only the complete pair backs the yield


def test_clean_dedup_and_zero_area():
    raw = pd.DataFrame({"district": ["Huye", "Huye"], "crop": ["M", "M"], "season": ["A", "A"], "year": [2024, 2024], "area_ha": [0, 0], "production_t": [1, 1]})
    d, rep = clean(raw)
    assert len(d) == 1 and rep["duplicates_removed"] == 1 and np.isnan(d.yield_t_ha.iloc[0])


def _series(ys):
    return pd.DataFrame({"district": "A", "crop": "M", "season": "A", "year": range(2021, 2021 + len(ys)), "area_ha": 100.0, "production_t": [y * 100 for y in ys]})


def test_priority_insufficient_and_flag():
    assert compute_priority(_series([2.0]), 2021).category.iloc[0] == "Insufficient data"
    r = compute_priority(_series([2.0, 2.0, 1.5]), 2023).iloc[0]
    assert r.category == "Elevated" and r.basis.startswith("Change-only")
    assert classify(None, None) == "Insufficient data"


def test_empty_and_validation():
    assert compute_priority(pd.DataFrame(), 2024).empty
    assert validate(pd.DataFrame())["warnings"]
    df, _ = clean(make_sample())
    assert validate(df)["duplicates"] == 0
