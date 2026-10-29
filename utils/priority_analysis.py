"""Transparent, rule-based priority indicator on SAME-SEASON series (district × crop × season).
Thresholds are provisional analytical settings, not NISR classifications. This is not a forecast."""
import numpy as np, pandas as pd
from utils.metrics import pct_change

MIN_PERIODS = 4
RULES = {"Elevated": {"drop_pct": -15.0, "cv_pct": 25.0}, "Watch": {"drop_pct": -8.0, "cv_pct": 15.0}}
COLS = ["district", "crop", "season", "current_yield", "reference_yield", "reference_year", "abs_change", "pct_change",
        "periods_used", "cv_pct", "basis", "category"]


def classify(change, cv, rules=None):
    rules = rules or RULES
    if change is None and cv is None:
        return "Insufficient data"
    for name in ("Elevated", "Watch"):
        r = rules[name]
        if (change is not None and change <= r["drop_pct"]) or (cv is not None and cv >= r["cv_pct"]):
            return name
    return "Stable"


def compute_priority(df: pd.DataFrame, year: int, min_periods: int = MIN_PERIODS, rules=None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=COLS)
    ok = df["production_t"].notna() & (df["area_ha"] > 0)  # yield only from complete production+area pairs
    d = df.assign(p=df["production_t"].where(ok), a=df["area_ha"].where(ok)).groupby(["district", "crop", "season", "year"]).agg(
        p=("p", lambda s: s.sum(min_count=1)), a=("a", lambda s: s.sum(min_count=1))).reset_index()
    d["y"] = np.where(d.a > 0, d.p / d.a, np.nan)
    rows = []
    for (dist, crop, seas), g in d.dropna(subset=["y"]).groupby(["district", "crop", "season"]):
        g = g.sort_values("year"); hist = g[g.year <= year]
        cur, prev = g[g.year == year], g[g.year < year].tail(1)
        if cur.empty or prev.empty:
            rows.append((dist, crop, seas, np.nan, np.nan, None, np.nan, np.nan, len(hist), np.nan,
                         "No comparable earlier period in the same season", "Insufficient data"))
            continue
        c, b = float(cur.y.iloc[0]), float(prev.y.iloc[0]); pc = pct_change(c, b)
        cv = float(hist.y.std(ddof=1) / hist.y.mean() * 100) if len(hist) >= min_periods else None
        basis = f"Change + variability (n={len(hist)})" if cv is not None else f"Change-only (n={len(hist)} < {min_periods})"
        rows.append((dist, crop, seas, c, b, int(prev.year.iloc[0]), c - b, np.nan if pc is None else pc, len(hist),
                     np.nan if cv is None else cv, basis, classify(pc, cv, rules)))
    out = pd.DataFrame(rows, columns=COLS)
    out["_o"] = out.category.map({"Elevated": 0, "Watch": 1, "Stable": 2, "Insufficient data": 3})
    return out.sort_values(["_o", "pct_change"]).drop(columns="_o").reset_index(drop=True)
