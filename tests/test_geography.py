import pandas as pd
from utils import geography as geo


def test_30_districts_5_provinces():
    assert len(geo.ALL_DISTRICTS) == 30 and len(set(geo.ALL_DISTRICTS)) == 30
    assert {p: len(d) for p, d in geo.PROVINCE_DISTRICTS.items()} == {"Eastern": 7, "Southern": 8, "Western": 7, "Northern": 5, "City of Kigali": 3}
    assert geo.DISTRICT_TO_PROVINCE["Gasabo"] == "City of Kigali" and geo.DISTRICT_TO_PROVINCE["Musanze"] == "Northern"


def test_normalisation_never_guesses():
    assert geo.normalize_district("  huye ") == "Huye" and geo.normalize_district("NYA  GATARE") is None
    assert geo.normalize_district("Nyagatar") is None and geo.normalize_district(None) is None


def test_documented_alias_only():
    assert geo.normalize_district("Foo", {"Foo": "Huye"}) == "Huye"
    assert geo.normalize_district("Foo", {"Foo": "NotADistrict"}) is None


def test_province_normalisation_and_coverage_labels():
    assert geo.normalize_province("Kigali City") == "City of Kigali" and geo.normalize_province("northern province") == "Northern"
    assert geo.coverage_label(30).startswith("Rwanda-wide") and "Partial" in geo.coverage_label(10) and "Unknown" in geo.coverage_label(0)
    assert geo.geography_report(["Huye"], ["Zzz"])["unknown"] == ["Zzz"]
