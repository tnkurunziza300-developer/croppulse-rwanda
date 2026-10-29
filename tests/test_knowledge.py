import pytest
import knowledge as K
from utils import geography as geo


def test_every_district_has_zone_and_valid_coordinates():
    assert set(K.DISTRICTS) == set(geo.ALL_DISTRICTS) and len(K.DISTRICTS) == 30
    for d, (z, la, lo) in K.DISTRICTS.items():
        assert z in K.ZONES and -3.0 < la < -1.0 and 28.8 < lo < 31.0, d


def test_crops_are_complete():
    for k, v in K.CROPS.items():
        assert set(v["suit"]) == set("HWCE") and all(1 <= s <= 3 for s in v["suit"].values())
        assert v["days"][0] < v["days"][1] and v["alt"][0] < v["alt"][1] and v["plant"], k


def test_season_for_and_window_status():
    assert K.season_for(10) == "A" and K.season_for(1) == "A" and K.season_for(4) == "B" and K.season_for(7) == "C"
    assert "Provisional CropPulse calendar" in K.window_status("Maize", "A", 10)
    assert "lists" in K.window_status("Maize", "A", 6) and "No month entry" in K.window_status("Wheat", "C", 7)


def test_calendar_matrix_shape_and_marks():
    m = K.calendar_matrix(["Maize", "Coffee"])
    assert len(m["Maize"]) == 12 and m["Maize"][8] == 1 and 3 in m["Maize"] and 3 not in m["Coffee"]


def test_area_conversion_and_estimate():
    assert K.to_ha(100, "are (100 m²)") == pytest.approx(1) and K.to_ha(10000, "square metres") == pytest.approx(1)
    e = K.estimate("Maize", 2, "smallholder")
    assert e["harvest_kg"] == (3000.0, 6000.0) and e["seed"][:2] == (40, 50)
    assert K.estimate("Coffee", 1)["harvest_kg"] is None
