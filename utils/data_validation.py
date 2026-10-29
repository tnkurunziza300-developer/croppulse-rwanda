import pandas as pd
from utils.data_loader import REQUIRED


def validate(df: pd.DataFrame) -> dict:
    miss_cols = [c for c in REQUIRED if c not in df.columns]
    if df.empty or miss_cols:
        return {"rows": len(df), "cols": df.shape[1], "missing_columns": miss_cols, "missing": pd.Series(dtype=int),
                "duplicates": 0, "warnings": ["Dataset is empty or lacks required columns."]}
    warnings = []
    if (df["area_ha"] <= 0).any():
        warnings.append("Some records have zero or negative cultivated area; yield is left blank for them.")
    if (df["production_t"] < 0).any():
        warnings.append("Negative production values found.")
    if df["year"].isna().any() or df["season"].isin(["", "nan"]).any():
        warnings.append("Records with missing year or season found.")
    dups = int(df["key_conflict"].sum()) if "key_conflict" in df else 0
    if dups:
        warnings.append(f"{dups} records share a district/crop/season/year key but differ elsewhere (kept, not merged); check for unlisted categories.")
    return {"rows": len(df), "cols": df.shape[1], "missing_columns": [], "missing": df.isna().sum(),
            "duplicates": dups, "warnings": warnings, "years": (int(df.year.min()), int(df.year.max())),
            "districts": int(df.district.nunique())}
