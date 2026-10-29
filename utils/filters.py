import pandas as pd


def apply_filters(df: pd.DataFrame, districts=None, crops=None, seasons=None) -> pd.DataFrame:
    """Empty/None selection means 'all'. One function feeds every page so charts and KPIs agree."""
    for col, sel in (("district", districts), ("crop", crops), ("season", seasons)):
        if sel:
            df = df[df[col].isin(sel)]
    return df
