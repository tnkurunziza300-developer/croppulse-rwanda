import pandas as pd
import utils.data_loader as dl
from utils.data_validation import validate


def test_missing_columns_reported():
    v = validate(pd.DataFrame({"district": ["A"]}))
    assert "crop" in v["missing_columns"] and v["warnings"]


def test_warnings_for_bad_values():
    df, report = dl.clean(pd.DataFrame({"district": ["Huye", "Huye"], "crop": ["M", "M"], "season": ["A", "A"],
                                        "year": [2024, 2023], "area_ha": [0, 1], "production_t": [2, -1]}))
    w = " ".join(validate(df)["warnings"])
    assert "area" in w
    assert len(report["quarantine"]) == 1 and "negative production" in report["quarantine"].iloc[0]["reason"]


def test_invalid_csv_and_missing_columns(tmp_path, monkeypatch):
    (tmp_path / "data" / "verified").mkdir(parents=True)
    monkeypatch.setattr(dl, "ROOT", tmp_path)
    p = tmp_path / "data" / "verified" / "x.csv"
    p.write_text("")  # empty file
    assert dl.load_data()[1]["state"] == "unavailable"
    p.write_text("a,b\n1,2\n")  # wrong schema
    df, st_ = dl.load_data()
    assert st_["state"] == "unavailable" and "Missing required columns" in st_["message"]


def test_demo_mode_is_labelled(tmp_path, monkeypatch):
    # Keep this demo-mode assertion independent of any locally installed verified data.
    monkeypatch.setattr(dl, "ROOT", tmp_path)
    df, st_ = dl.load_data()
    assert st_["state"] == "demo" and (df["data_origin"] == dl.SAMPLE_LABEL).all()
