"""Data loading + cleaning. Verified CSVs in data/verified/ take priority over the demo sample."""
import hashlib, json
import re
from pathlib import Path
from utils import geography as geo
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
COLUMN_ALIASES = {"cultivated_area_ha": "area_ha", "production_tonnes": "production_t"}
VALID_SEASONS = {"A", "B", "C"}
DIMENSIONS = ["farmer_type", "cropping_system"]
OK_PROD_UNITS = {"t", "tonne", "tonnes"}
OK_AREA_UNITS = {"ha", "hectare", "hectares"}
MANIFEST_REQUIRED = ["title", "publisher", "source_url", "reference_period", "retrieved_at", "sha256", "units"]
REQUIRED = ["district", "crop", "season", "year", "area_ha", "production_t"]
SAMPLE_LABEL = "DEMONSTRATION DATA — ILLUSTRATIVE ONLY; NOT OFFICIAL RWANDA STATISTICS."
DISTRICTS = ["Musanze", "Huye", "Nyagatare", "Rubavu", "Kayonza", "Rusizi", "Gicumbi", "Muhanga", "Bugesera", "Nyanza"]  # all valid Rwanda districts
CROPS = {"Maize": 1.8, "Beans": 0.9, "Cassava": 9.0, "Irish potato": 10.0, "Sorghum": 1.2, "Banana": 8.0}


def make_sample(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for d in DISTRICTS:
        dm = rng.uniform(0.8, 1.2)
        for c, base in CROPS.items():
            for y in range(2021, 2026):
                for s in ("A", "B"):
                    area = rng.uniform(500, 6000) * (1.2 if s == "A" else 0.9)
                    yl = base * dm * rng.normal(1, 0.12) * (0.97 if s == "B" else 1)
                    if (d, c, y) == ("Nyagatare", "Maize", 2025):
                        yl *= 0.7  # deliberate illustrative drop so the demo shows a flag
                    rows.append((d, c, s, y, round(area, 1), round(area * yl, 1)))
    df = pd.DataFrame(rows, columns=REQUIRED)
    df.loc[rng.choice(df.index, 8, replace=False), "production_t"] = np.nan
    df = df.drop(rng.choice(df.index, 15, replace=False)).reset_index(drop=True)
    df["data_origin"] = SAMPLE_LABEL
    return df


def clean(raw: pd.DataFrame, aliases=None):
    """Returns (clean_df, report). Invalid records are QUARANTINED with reasons, not deleted silently.
    Only exact duplicate rows are dropped; rows sharing a key but differing elsewhere are kept and flagged."""
    df = raw.rename(columns=COLUMN_ALIASES).copy()
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Expected: {REQUIRED}.")
    for c in ("district", "crop", "season"):
        df[c] = df[c].astype(str).str.strip()
    df["season"] = df["season"].str.upper()
    for c in ("year", "area_ha", "production_t", "harvested_area_ha"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    reasons = pd.Series("", index=df.index)

    def flag(mask, msg):
        nonlocal reasons
        reasons = reasons.where(~mask, reasons + msg + "; ")

    canon = df["district"].map(lambda x: geo.normalize_district(x, aliases))
    flag(canon.isna(), "unknown district")
    flag(~df["season"].isin(VALID_SEASONS), "invalid season (expected A, B or C)")
    flag(df["year"].isna() | (df["year"] < 1990) | (df["year"] > 2100), "invalid year")
    given = pd.Series(False, index=df.index)
    if "province" in df:
        given = df["province"].notna() & (df["province"].astype(str).str.strip() != "")
        flag(given & (df["province"].map(geo.normalize_province) != canon.map(geo.DISTRICT_TO_PROVINCE)), "province conflicts with district")
    if "production_unit" in df:
        u = df["production_unit"]; flag(u.notna() & ~u.astype(str).str.strip().str.lower().isin(OK_PROD_UNITS), "incompatible production unit")
    if "area_unit" in df:
        u = df["area_unit"]; flag(u.notna() & ~u.astype(str).str.strip().str.lower().isin(OK_AREA_UNITS), "incompatible area unit")
    flag(df["area_ha"].notna() & (df["area_ha"] < 0), "negative cultivated area")
    flag(df["production_t"].notna() & (df["production_t"] < 0), "negative production")
    bad = reasons != ""
    quarantine = raw[bad].assign(reason=reasons[bad])
    unknown = df.loc[canon.isna(), "district"].unique()
    df = df[~bad].copy()
    df["district"] = canon[~bad]
    df["province"] = df["district"].map(geo.DISTRICT_TO_PROVINCE)
    df["province_source"] = np.where(given[~bad], "provided", "derived")
    df["year"] = df["year"].astype(int)
    n0 = len(df)
    df = df.drop_duplicates()
    key = ["district", "crop", "season", "year"] + [c for c in DIMENSIONS if c in df]
    df["key_conflict"] = df.duplicated(subset=key, keep=False)
    df["yield_t_ha"] = np.where(df["area_ha"] > 0, df["production_t"] / df["area_ha"], np.nan)
    return df.reset_index(drop=True), {"duplicates_removed": n0 - len(df), "key_conflicts": int(df["key_conflict"].sum()),
                                       "quarantine": quarantine, "geography": geo.geography_report(df["district"].unique(), unknown)}


def _manifest(files):
    p = ROOT / "data" / "verified" / "MANIFEST.json"
    if not p.exists():
        return {}, ["No MANIFEST.json: provenance cannot be checked."]
    try:
        entries = {e.get("file"): e for e in json.loads(p.read_text()).get("files", [])}
    except Exception as e:  # noqa: BLE001
        return {}, [f"MANIFEST.json unreadable: {e}"]
    issues = []
    listed = {name for name in entries if name}
    actual = {f.name for f in files}
    for name in sorted(listed - actual):
        issues.append(f"{name}: manifest lists a file that is not present")
    for f in files:
        e = entries.get(f.name)
        if not e:
            issues.append(f"{f.name}: not listed in manifest")
        elif [k for k in MANIFEST_REQUIRED if not e.get(k)]:
            issues.append(f"{f.name}: manifest missing {[k for k in MANIFEST_REQUIRED if not e.get(k)]}")
        elif not (re.search(r"\b(t|tonne|tonnes)\b", str(e["units"]).lower()) and
                  re.search(r"\b(ha|hectare|hectares)\b", str(e["units"]).lower())):
            issues.append(f"{f.name}: manifest units must declare production in tonnes and area in hectares")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != str(e["sha256"]).lower():
            issues.append(f"{f.name}: checksum does not match manifest")
    return entries, issues


DEMO_PROVENANCE = {"title": "Synthetic demonstration dataset", "publisher": "Generated by the CropPulse team (random, seed 7)",
                   "source_url": "n/a", "reference_period": "2021–2025 (synthetic)", "retrieved_at": "n/a",
                   "limitations": "Random numbers. Not NISR data. Not representative of any real district or crop."}


def load_data():
    """Returns (df, status). state: demo | pending | warning | validated | unavailable.
    'validated' requires a complete manifest, matching checksums, no quarantined rows and no validation warnings."""
    from utils.data_validation import validate
    files = sorted((ROOT / "data" / "verified").glob("*.csv"))
    try:
        if files:
            raw = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
            df, rep = clean(raw)
            entries, issues = _manifest(files)
            warns = validate(df)["warnings"]
            if "data_origin" not in df:
                df["data_origin"] = "Provenance " + ("declared in manifest: " + ", ".join(entries) if entries else "unverified")
            state = "pending" if issues else ("warning" if (warns or len(rep["quarantine"])) else "validated")
            msg = {"pending": "Official-source data loaded; validation pending. " + " ".join(issues),
                   "warning": "Dataset contains validation warnings or quarantined records.",
                   "validated": "Source and manifest checks passed CropPulse's structural validation; the named publisher remains the authority for the original estimates."}[state]
            return df, {"state": state, "message": msg, "provenance": list(entries.values()), **rep}
        path = ROOT / "data" / "sample" / "sample_crops.csv"
        df, rep = clean(pd.read_csv(path) if path.exists() else make_sample())
        df["data_origin"] = SAMPLE_LABEL
        return df, {"state": "demo", "message": SAMPLE_LABEL, "provenance": [DEMO_PROVENANCE], **rep}
    except Exception as e:  # noqa: BLE001 - surfaced to the user
        return pd.DataFrame(columns=REQUIRED), {"state": "unavailable", "message": f"Could not read data: {e}"}
