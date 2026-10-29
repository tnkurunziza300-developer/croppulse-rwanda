import numpy as np, pandas as pd, pytest
from utils.metrics import abs_change, aggregate, change_table, pct_change
from utils.filters import apply_filters
from utils.exports import to_csv_bytes
import io


def _df():
    return pd.DataFrame({"district": ["A", "A", "B", "B"], "crop": ["M"] * 4, "season": ["A"] * 4, "year": [2023, 2024, 2023, 2024],
                         "area_ha": [10.0, 10.0, 10.0, 10.0], "production_t": [10.0, 15.0, 0.0, 5.0]})


def test_change_table_values_and_zero_baseline():
    t = change_table(_df(), ["district"], "production_t", 2024, 2023).set_index("district")
    assert t.loc["A", "absolute_change"] == 5 and t.loc["A", "pct_change"] == pytest.approx(50)
    assert t.loc["B", "absolute_change"] == 5 and pd.isna(t.loc["B", "pct_change"])  # zero baseline


def test_abs_change_missing():
    assert abs_change(np.nan, 1) is None and abs_change(3, 1) == 2


def test_filters_and_export_match():
    f = apply_filters(_df(), districts=["A"])
    assert set(f.district) == {"A"} and len(apply_filters(_df())) == 4 and apply_filters(_df(), crops=["X"]).empty
    back = pd.read_csv(io.BytesIO(to_csv_bytes(f)))
    assert len(back) == len(f) and back.production_t.sum() == f.production_t.sum()


def test_aggregate_empty():
    assert aggregate(_df().iloc[0:0], "district").empty
