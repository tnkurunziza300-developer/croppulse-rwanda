"""Rwanda administrative reference: 5 provinces (incl. City of Kigali), 30 districts.

NISR-hosted District Boundary 2022 service metadata checked on 2026-10-18.
Its reported total and province distribution match the list below. The list has
not been compared record-by-record with the service and is not loaded dynamically.
Sector identifiers and point-in-polygon validation are not implemented.
"""
import re
import pandas as pd

ADMIN_REFERENCE_SOURCE_URL = "https://gis-server.statistics.gov.rw/server/rest/services/Hosted/District_Boundary_2022/FeatureServer/0"
ADMIN_REFERENCE_VINTAGE = "NISR district boundaries updated by 2022 Census mapping"
ADMIN_METADATA_CHECKED_ON = "2026-10-18"

PROVINCE_DISTRICTS = {
    "Eastern": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
    "Southern": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Western": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
    "Northern": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "City of Kigali": ["Gasabo", "Kicukiro", "Nyarugenge"],
}
DISTRICT_TO_PROVINCE = {d: p for p, ds in PROVINCE_DISTRICTS.items() for d in ds}
ALL_DISTRICTS = sorted(DISTRICT_TO_PROVINCE)
ALIASES: dict = {}  # reviewed source-name variants only (alias -> canonical). Empty until a variant is documented.
PROVINCE_ALIASES = {"kigali city": "City of Kigali", "city of kigali": "City of Kigali", "kigali": "City of Kigali"}
_LOOKUP = {d.lower(): d for d in ALL_DISTRICTS}


def _key(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def normalize_district(name, aliases=None):
    """Case/whitespace normalisation + reviewed aliases. Returns canonical name or None (never guesses)."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    k = _key(name)
    if k in _LOOKUP:
        return _LOOKUP[k]
    al = {_key(a): c for a, c in {**ALIASES, **(aliases or {})}.items()}
    c = al.get(k)
    return c if c in DISTRICT_TO_PROVINCE else None


def normalize_province(name):
    k = _key(name).replace(" province", "")
    for p in PROVINCE_DISTRICTS:
        if k == p.lower():
            return p
    return PROVINCE_ALIASES.get(k)


def coverage_label(n_valid: int) -> str:
    if n_valid <= 0:
        return "Unknown geographic coverage"
    if n_valid == len(ALL_DISTRICTS):
        return "Rwanda-wide dataset (all 30 districts present)"
    return f"Partial district coverage ({n_valid} of {len(ALL_DISTRICTS)} districts)"


def geography_report(valid_districts, unknown_names=()) -> dict:
    valid = sorted(set(valid_districts))
    return {"n_valid": len(valid), "valid": valid, "missing_districts": [d for d in ALL_DISTRICTS if d not in valid],
            "unknown": sorted(set(map(str, unknown_names))), "coverage_label": coverage_label(len(valid)),
            "by_province": {p: sum(d in valid for d in ds) for p, ds in PROVINCE_DISTRICTS.items()}}
