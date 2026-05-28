"""
USA_cleaning.py
===============

Phase 2 — Data Preparation & Feature Engineering (Stage 1: USA / gold 24K / USD).

Reads the raw source tables via `data_access`, cleans each to the Stage-1 slice,
and assembles the model-ready feature table `ml.us_gold_features_daily`
(one row per USA trading day, target `y = gold_24k` in USD, plus the engineered,
exogenous, and calendar features mandated by project_plan.md).

Locked decisions (this phase):
- Date window: exogenous sources extracted from SOURCE_START (2016-01-01) for
  forward-fill warm-up; the feature table starts at the first gold trading day
  (>= DATE_START = 2017-01-01).
- Calendar grid: NYSE trading days = the distinct dates actually observed in the
  USA gold series (they already encode NYSE holidays). `y_lag_1` = previous
  trading day. Row count == distinct USA price dates in [DATE_START, today].
- Outliers: built on RAW gold_24k (no capping). `cap_gold_outliers()` is provided
  but intentionally NOT wired into the default build — see the module docstring's
  "Outlier handling (deferred)" note and refactor/03-data-preparation.md.

Run standalone:
    .\\projet\\Scripts\\python.exe USA_cleaning.py
"""

import numpy as np
import pandas as pd
from sqlalchemy import Date, text

from db_settings import get_engine
import data_access

# =========================================================
# Stage-1 contract (mirrors the constants in project_plan.md)
# =========================================================

SOURCE_START = "2016-01-01"   # exogenous extraction floor (ffill warm-up)
DATE_START = "2017-01-01"     # feature-table floor (first gold day is 2017-01-02)
COUNTRY_CODE = "USA"

LAG_WINDOWS = [1, 7, 30]
MA_WINDOWS = [7, 30]
VOL_WINDOW = 30

ENGINEERED_FEATURES = ["y_lag_1", "y_lag_7", "y_lag_30", "y_ma_7", "y_ma_30", "y_vol_30"]
MACRO_FEATURES = ["fed_rate", "real_rate", "cpi", "gdp", "dxy", "unemployment"]
MARKET_FEATURES = ["vix", "oil_price"]
GEO_FEATURES = ["total_events", "political_events", "war_intensity",
                "crisis_index", "political_pressure"]
RESERVE_FEATURE = ["gold_reserves"]
CALENDAR_FEATURES = ["month", "quarter", "day_of_week", "is_month_end"]

ORDERED_COLUMNS = (
    ["date", "country_code", "y"]
    + ENGINEERED_FEATURES
    + MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES + RESERVE_FEATURE
    + CALENDAR_FEATURES
)

# live macro_data ships mixed-case columns; map to the lowercase contract
_MACRO_RENAME = {"CPI": "cpi", "GDP": "gdp", "DXY": "dxy", "Unemployment": "unemployment"}

# FRED indexes each series by its REFERENCE period, but the figure is only published
# weeks later. Re-stamp each series to a conservative publication-availability date
# (calendar months added to the reference date) before forward-fill, so a value is
# never visible before it was public (look-ahead leak fix). Monthly series publish
# ~1 month after the period; quarterly GDP's advance estimate lands ~1 month after the
# quarter ends (~4 months after the quarter-START stamp); DXY (DTWEXBGS) is daily and
# effectively same-day. A fully exact fix would use ALFRED real-time vintages.
_MACRO_PUB_LAG_MONTHS = {
    "fed_rate": 1, "real_rate": 1, "cpi": 1, "unemployment": 1, "gdp": 4, "dxy": 0,
}

ML_SCHEMA = "ml"
ML_TABLE = "us_gold_features_daily"


# =========================================================
# Per-source cleaning
# Each returns a frame keyed by a proper datetime `date` column.
# =========================================================

def clean_prices(df):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["devise"] == "USD"]
    df = df.groupby("date", as_index=False)["gold_24k"].median()  # one row/day (dedup)
    return df.sort_values("date").reset_index(drop=True)


def clean_macro(df):
    """USA macro features, re-stamped to publication-availability dates (leak-safe).

    The live `macro_data` ships mixed-case columns and dates each value at its FRED
    REFERENCE period. We rename to the lowercase contract, coerce to numeric, then
    shift each series forward by its publication lag (`_MACRO_PUB_LAG_MONTHS`) so the
    grid-level forward-fill never exposes a figure before it was public. Each column
    keeps its native cadence (monthly / quarterly / daily); forward-fill in
    build_features_frame() propagates each one independently.
    """
    df = df.rename(columns=_MACRO_RENAME).copy()
    df["date"] = pd.to_datetime(df["date"])
    cols = []
    for col in MACRO_FEATURES:
        obs = pd.DataFrame({
            "date": df["date"],
            col: pd.to_numeric(df[col], errors="coerce"),  # live values are stored as text
        }).dropna(subset=[col])
        lag = _MACRO_PUB_LAG_MONTHS.get(col, 0)
        if lag:
            obs["date"] = obs["date"] + pd.DateOffset(months=lag)
        cols.append(obs.set_index("date")[col])
    macro = pd.concat(cols, axis=1).sort_index()
    macro = macro[macro.index >= SOURCE_START].reset_index()
    return macro.sort_values("date").reset_index(drop=True)


def clean_vix_oil(df):
    df = df.copy()
    df = df.rename(columns={"Date": "date", "oil": "oil_price"})
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= SOURCE_START]
    return df.sort_values("date").reset_index(drop=True)


def clean_geopo(df):
    df = df.copy()
    df = df[df["country"] == COUNTRY_CODE]
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= SOURCE_START]
    df = df[["date"] + GEO_FEATURES]  # drop country/other cols so it maps 1:1 to GEO_FEATURES
    return df.sort_values("date").reset_index(drop=True)


def clean_reserves(df):
    df = df.copy()
    df = df[df["country_code"] == COUNTRY_CODE]
    # World Bank publishes year-Y reserves ~mid Y+1; stamp at Jul-1 of Y+1 so the
    # forward-fill never exposes a year's figure before it was available (leak fix).
    df["date"] = pd.to_datetime(df["year"].astype(int) + 1, format="%Y") + pd.DateOffset(months=6)
    df = df.rename(columns={"value": "gold_reserves"})
    df = df[["date", "gold_reserves"]]
    return df.sort_values("date").reset_index(drop=True)


# =========================================================
# Helpers
# =========================================================

def _ffill_to_grid(df, grid):
    """Align a date-keyed frame onto the trading-day grid by forward-fill.

    Sparse sources (monthly macro on month-starts, annual reserves on Jan-1) and
    daily sources with holiday gaps rarely land exactly on trading days. We union
    the source dates with the grid, forward-fill, then select the grid — so every
    trading day inherits the most recent prior observation. A plain reindex(grid)
    would null any value not already on a trading-day date.
    """
    s = df.set_index("date").sort_index()
    s = s[~s.index.duplicated(keep="first")]
    return s.reindex(s.index.union(grid)).ffill().reindex(grid)


def cap_gold_outliers(prices, q=0.995):
    """DEFERRED / OFF BY DEFAULT — winsorize gold_24k at the q-th upper quantile.

    Phase 1 flagged the series max (173.62 $/g) as an implausible scraping error
    (real peak ~90-95 $/g). This helper is provided as one candidate fix but is
    intentionally NOT called by build_us_gold_features_daily(); the table is built
    on raw gold_24k. See refactor/03-data-preparation.md for the full option list.
    """
    out = prices.copy()
    out["gold_24k"] = out["gold_24k"].clip(upper=out["gold_24k"].quantile(q))
    return out


# =========================================================
# Feature-table build
# =========================================================

def build_features_frame():
    """Assemble the in-memory `ml.us_gold_features_daily` frame (no DB write)."""
    prices = clean_prices(data_access.load_raw_prices())
    macro = clean_macro(data_access.load_macro_data())
    vix_oil = clean_vix_oil(data_access.load_vix_oil())
    geopo = clean_geopo(data_access.load_geopo())
    reserves = clean_reserves(data_access.load_reserves())

    # Trading-day grid: USA price dates within [DATE_START, today]
    today = pd.Timestamp.today().normalize()
    prices = prices[(prices["date"] >= DATE_START) & (prices["date"] <= today)]
    grid = pd.DatetimeIndex(sorted(prices["date"].unique()), name="date")

    df = pd.DataFrame(index=grid)
    df["y"] = prices.set_index("date")["gold_24k"]

    # Engineered features — shifts/rolls run on the trading-day grid
    for w in LAG_WINDOWS:
        df[f"y_lag_{w}"] = df["y"].shift(w)
    for w in MA_WINDOWS:
        df[f"y_ma_{w}"] = df["y"].rolling(w).mean()
    log_ret = np.log(df["y"] / df["y"].shift(1))
    df["y_vol_30"] = log_ret.rolling(VOL_WINDOW).std()

    # Exogenous features — forward-filled onto the grid
    df[MACRO_FEATURES] = _ffill_to_grid(macro, grid)
    df[MARKET_FEATURES] = _ffill_to_grid(vix_oil, grid)
    df[GEO_FEATURES] = _ffill_to_grid(geopo, grid)
    df[RESERVE_FEATURE] = _ffill_to_grid(reserves, grid)

    # Calendar features — derived in pandas from the date index
    df["month"] = df.index.month
    df["quarter"] = df.index.quarter
    df["day_of_week"] = df.index.dayofweek
    df["is_month_end"] = df.index.is_month_end.astype(int)

    df["country_code"] = COUNTRY_CODE
    df = df.reset_index()  # `date` becomes a column
    return df[ORDERED_COLUMNS]


def write_features_table(df):
    """Create schema `ml` (idempotent, committed) and replace the feature table."""
    engine = get_engine()
    with engine.begin() as conn:  # begin() commits — avoids the create_tables() no-commit pitfall
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {ML_SCHEMA}"))
    df.to_sql(
        ML_TABLE,
        engine,
        schema=ML_SCHEMA,
        if_exists="replace",   # derived table: replace makes re-runs idempotent
        index=False,
        dtype={"date": Date},  # write a true DATE column (timestamp -> DATE)
    )


def build_us_gold_features_daily():
    """End-to-end Phase-2 build: clean -> engineer -> join -> write, then summarize."""
    df = build_features_frame()
    write_features_table(df)

    warmup = df[ENGINEERED_FEATURES].isna().any(axis=1).sum()
    print(f"Wrote {ML_SCHEMA}.{ML_TABLE}: {len(df)} rows x {len(df.columns)} cols")
    print(f"  date range : {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"  y nulls    : {df['y'].isna().sum()}")
    print(f"  warm-up rows with engineered nulls: {warmup}")
    exog = MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES + RESERVE_FEATURE
    print(f"  exog nulls : {int(df[exog].isna().sum().sum())} (across {len(exog)} columns)")
    return df


if __name__ == "__main__":
    build_us_gold_features_daily()
