import numpy as np, pandas as pd


def pct_change(cur, base):
    """None when the baseline is zero/missing — never a misleading percentage."""
    if cur is None or base is None or pd.isna(cur) or pd.isna(base) or base == 0:
        return None
    return float((cur - base) / base * 100)


def abs_change(cur, base):
    return None if (cur is None or base is None or pd.isna(cur) or pd.isna(base)) else float(cur - base)


def aggregate(df: pd.DataFrame, by) -> pd.DataFrame:
    """Totals use all non-missing values. Yield uses ONLY records where production and area (>0) are both present,
    so partial production is never divided by complete area. `yield_pairs` shows how many records backed the yield."""
    ok = df["production_t"].notna() & (df["area_ha"] > 0)
    d = df.assign(_yp=df["production_t"].where(ok), _ya=df["area_ha"].where(ok), _ok=ok.astype(int))
    s = lambda c: (lambda x: x.sum(min_count=1))
    g = d.groupby(by, dropna=False).agg(production_t=("production_t", s(0)), area_ha=("area_ha", s(0)),
                                        observations=("production_t", "count"), yield_pairs=("_ok", "sum"),
                                        _yp=("_yp", s(0)), _ya=("_ya", s(0))).reset_index()
    g["yield_t_ha"] = np.where(g["_ya"] > 0, g["_yp"] / g["_ya"], np.nan)
    return g.drop(columns=["_yp", "_ya"])


def change_table(df: pd.DataFrame, keys, metric: str, cur_year: int, base_year: int) -> pd.DataFrame:
    a = aggregate(df, keys + ["year"])
    cur = a[a.year == cur_year].set_index(keys)[metric].rename("current")
    base = a[a.year == base_year].set_index(keys)[metric].rename("previous")
    t = pd.concat([base, cur], axis=1).reset_index()
    t["absolute_change"] = [abs_change(c, b) for c, b in zip(t.current, t.previous)]
    t["pct_change"] = [pct_change(c, b) for c, b in zip(t.current, t.previous)]
    return t
