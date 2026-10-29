import hashlib, json
import pandas as pd, pytest
import utils.data_loader as dl


def _row(**k):
    r = dict(district="Huye", crop="Maize", season="A", year=2024, area_ha=10.0, production_t=20.0); r.update(k); return r


def test_alias_columns_extra_columns_and_province_derived():
    raw = pd.DataFrame([{"district": " huye", "crop": "Maize", "season": "a", "year": 2024, "cultivated_area_ha": 10, "production_tonnes": 20, "extra": "x"}])
    d, rep = dl.clean(raw)
    assert d.district.iloc[0] == "Huye" and d.province.iloc[0] == "Southern" and d.province_source.iloc[0] == "derived"
    assert d.season.iloc[0] == "A" and "extra" in d and d.yield_t_ha.iloc[0] == 2.0


def test_quarantine_reasons():
    raw = pd.DataFrame([_row(), _row(district="Atlantis"), _row(season="D"), _row(year="abc"), _row(province="Northern"),
                        _row(production_unit="kg", district="Rubavu")])
    d, rep = dl.clean(raw)
    q = rep["quarantine"]
    assert len(d) == 1 and len(q) == 5
    joined = " ".join(q.reason)
    for s in ("unknown district", "invalid season", "invalid year", "province conflicts", "incompatible production unit"):
        assert s in joined
    assert rep["geography"]["unknown"] == ["Atlantis"]


def test_exact_duplicates_dropped_but_categories_kept():
    raw = pd.DataFrame([_row(farmer_type="SSF"), _row(farmer_type="SSF"), _row(farmer_type="LSF")])
    d, rep = dl.clean(raw)
    assert len(d) == 2 and rep["duplicates_removed"] == 1 and rep["key_conflicts"] == 0


def test_key_conflict_flagged_not_deleted():
    d, rep = dl.clean(pd.DataFrame([_row(production_t=20), _row(production_t=25)]))
    assert len(d) == 2 and rep["key_conflicts"] == 2


def test_missing_required_columns_raises():
    with pytest.raises(ValueError):
        dl.clean(pd.DataFrame({"district": ["Huye"]}))


def _setup(tmp_path, monkeypatch, manifest=True, good_hash=True):
    (tmp_path / "data" / "verified").mkdir(parents=True)
    monkeypatch.setattr(dl, "ROOT", tmp_path)
    p = tmp_path / "data" / "verified" / "s.csv"
    pd.DataFrame([_row(), _row(year=2023)]).to_csv(p, index=False)
    if manifest:
        e = {"file": "s.csv", "title": "t", "publisher": "NISR", "source_url": "u", "reference_period": "2023-2024", "retrieved_at": "2026-01-01",
             "units": "t, ha", "sha256": hashlib.sha256(p.read_bytes()).hexdigest() if good_hash else "0" * 64}
        (tmp_path / "data" / "verified" / "MANIFEST.json").write_text(json.dumps({"files": [e]}))


def test_validated_requires_manifest_and_checksum(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch); assert dl.load_data()[1]["state"] == "validated"


def test_folder_alone_is_not_validated(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, manifest=False); assert dl.load_data()[1]["state"] == "pending"


def test_checksum_mismatch_is_pending(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, good_hash=False)
    s = dl.load_data()[1]; assert s["state"] == "pending" and "checksum" in s["message"]
