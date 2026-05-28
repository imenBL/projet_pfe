# Phase 2 — Data Preparation Summary (USA / gold 24K / USD / 2017 → today)

> **Status:** ✅ DONE — `ml.us_gold_features_daily` built (**2 448 × 27**) and verified against the live DB on 2026-05-26.
> Maps to: `refactor/03-data-preparation.md`, `project_plan.md` PHASE 2.
> Build code: `USA_cleaning.py` + `data_access.py` (repo root). Run: `.\projet\Scripts\python.exe USA_cleaning.py`.
>
> **Update 2026-05-28 — look-ahead leak fix (rebuilt).** Two exogenous look-ahead leaks
> were corrected and the table rebuilt (still 2 448 × 27, 0 nulls): (1) **FRED macro** was
> dated at its *reference period* and forward-filled — a figure became visible weeks before
> it was published; each series is now re-stamped to a publication-availability date
> (`clean_macro` + `_MACRO_PUB_LAG_MONTHS`: monthly +1 mo, GDP +4 mo, daily DXY +0).
> (2) **World Bank reserves** were stamped at Jan-1 of the *same* year (published ~12 mo
> later); now stamped **Jul-1 of Y+1**. Three latent build bugs blocking the rebuild were
> also fixed: `clean_macro` never applied the mixed-case rename (`KeyError 'cpi'`),
> `clean_prices` dropped its `.median()` aggregation (returned a `SeriesGroupBy`), and
> `clean_geopo` leaked the `country` column into the 5-col `GEO_FEATURES` assignment.

## Scope

Turn the five populated `public` source tables into one Stage-1, model-ready table —
one row per **USA trading day**, target `y = gold_24k` in USD — holding to the hard scope
(USA / gold 24K / USD / 2017→today; silver and non-24K karats excluded).

## What was added

| Artifact | Role |
|----------|------|
| `data_access.py` | Thin, **reusable** DB-read layer. One cached function per source table (`load_raw_prices`, `load_macro_data`, `load_vix_oil`, `load_geopo`, `load_reserves`) returning a DataFrame, so the cleaning module and the upcoming modeling phase share one extraction instead of re-writing `get_engine()` + `pd.read_sql()`. No transformations here. |
| `USA_cleaning.py` | Per-source cleaning (`clean_prices`, `clean_macro`, `clean_vix_oil`, `clean_geopo`, `clean_reserves`), the feature-table build (`build_features_frame` / `build_us_gold_features_daily`), the DB write (`write_features_table`), and a deferred, off-by-default `cap_gold_outliers` helper. |
| `ml.us_gold_features_daily` | New table in schema `ml` of `metals_db`. 2 448 rows × 27 columns. `date` persisted as SQL `DATE`. |

The five source tables in `public` were **not mutated** — all cleaning happens in pandas at
build time, consistent with the CLAUDE.md hard-scope rule ("filter to USA at the feature-build
step, do not delete/rewrite source tables").

## Decisions locked (this phase)

1. **Date window** — exogenous sources are extracted from `2016-01-01` so forward-fill has a
   prior value at the 2017 boundary; the feature table itself starts at the first gold trading
   day (`>= 2017-01-01`, i.e. **2017-01-02**). `DATE_END` is dynamic (today).
2. **Trading-day calendar — NYSE trading days.** The daily grid is the set of distinct dates
   actually observed in the USA gold series (these already encode NYSE holidays). Therefore
   `y_lag_1` = *previous trading day*, and the row count equals the number of distinct USA
   price dates. (Resolves the open question carried from Phase 1.)
3. **Outliers — built on raw `gold_24k`** (no capping); see "Outlier handling (deferred)".
4. **Module layout — a separate loader module** (`data_access.py`) imported by `USA_cleaning.py`.

## Feature dictionary — purpose of each column (27 total)

**Keys & target (3)**

| Column | Purpose |
|--------|---------|
| `date` | Trading day (SQL `DATE`). |
| `country_code` | ISO3 market tag — constant `USA` for this Stage-1 table. |
| `y` | **Target.** `gold_24k` in USD/g — the value to forecast. |

**Engineered — from the price series itself (6)**

| Column | Purpose |
|--------|---------|
| `y_lag_1` | Yesterday's price — short-term autoregressive memory / persistence. |
| `y_lag_7` | Price one trading-week ago — weekly momentum. |
| `y_lag_30` | Price ~one trading-month ago — medium-term level reference. |
| `y_ma_7` | 7-day rolling mean — denoised short-term level. |
| `y_ma_30` | 30-day rolling mean — trend baseline. |
| `y_vol_30` | 30-day rolling std of daily log-returns — recent volatility regime / risk. |

**Exogenous — macro (FRED, monthly/quarterly → forward-filled, 6)**

| Column | Purpose |
|--------|---------|
| `fed_rate` | Fed funds rate — opportunity cost of holding non-yielding gold. |
| `real_rate` | 10y real interest rate — classically the strongest macro driver of gold. |
| `cpi` | Inflation level — gold as an inflation hedge. |
| `gdp` | Output level (quarterly) — macro demand backdrop. |
| `dxy` | US dollar index — gold is USD-priced (classically inverse). |
| `unemployment` | Labour-market slack — recession / risk proxy. |

**Exogenous — market (Yahoo, daily → holiday gaps forward-filled, 2)**

| Column | Purpose |
|--------|---------|
| `vix` | Equity implied volatility — risk-off / safe-haven demand. |
| `oil_price` | Crude (CL=F) — commodity-inflation co-movement. |

**Exogenous — geopolitical (GDELT USA, daily, 5)**

| Column | Purpose |
|--------|---------|
| `total_events` | Volume of recorded US events — overall geopolitical activity. |
| `political_events` | Subset of political events — institutional activity intensity. |
| `war_intensity` | Conflict-tone index — safe-haven trigger. |
| `crisis_index` | Composite crisis signal. |
| `political_pressure` | Political-instability proxy. |

**Exogenous — reserves (World Bank USA, annual → forward-filled, 1)**

| Column | Purpose |
|--------|---------|
| `gold_reserves` | US official gold holdings — structural demand / backing signal. |

**Calendar — derived in pandas (4)**

| Column | Purpose |
|--------|---------|
| `month` | Month 1–12 — seasonal position. |
| `quarter` | Quarter 1–4 — coarse seasonality. |
| `day_of_week` | 0=Mon … 4=Fri on the trading grid — weekday effects. |
| `is_month_end` | 1 if the date is a calendar month-end — rebalancing / settlement effects. |

## How the table is assembled

1. **Grid** = sorted distinct USA price dates in `[2017-01-01, today]` (the NYSE trading-day spine).
2. `y = gold_24k`, then lags / moving averages / volatility computed **on the grid** (so shifts
   count trading days, not calendar days).
3. **Publication-lag re-stamping (leak-safe), then forward-fill onto the grid** (`_ffill_to_grid`):
   each exogenous series is first re-stamped to the date it was actually *available* (FRED macro
   shifted forward by its publication lag; reserves to Jul-1 of Y+1). Its dates are then *unioned*
   with the grid, forward-filled, and re-selected on the grid — so every trading day inherits the
   most recent **already-published** observation. This is required because sparse sources rarely
   land on a trading-day date; a plain `reindex(grid)` would null them. Macro string columns are
   coerced to numeric first.
4. **Calendar** features are derived from the date index; `country_code = 'USA'` is attached.
5. Written with `if_exists="replace"` (idempotent re-runs) and `dtype={"date": DATE}`.

## Acceptance criteria — verification (2026-05-26)

| Criterion | Result |
|-----------|--------|
| Table exists in schema `ml` | ✅ |
| Rows = distinct USA price dates in window | ✅ **2 448** (2017-01-02 → 2026-05-22) |
| `date` SQL type | ✅ `DATE` |
| `y` non-null every row | ✅ 0 nulls |
| `y_lag_*` / `y_ma_*` / `y_vol_30` null only in warm-up | ✅ confined to rows 0–29 |
| 14 exogenous columns present & forward-filled | ✅ 0 nulls after warm-up |
| 4 calendar columns present | ✅ |
| Lag sanity | ✅ a Monday's `y_lag_1` == previous trading day's `y` |
| Macro **leak-free** sanity | ✅ 2023-03-15 `cpi` == the **February** FRED print (released ~mid-March), **not** the March print (published mid-April) |
| Reserves **leak-free** sanity | ✅ 2024-02-01 `gold_reserves` == the **2022** figure (the latest published by then), **not** 2023/2024 |

## Outlier handling (deferred)

Phase 1 flagged the series max (**173.62 $/g**) as an implausible scraping error (real peak
~90–95 $/g). The table is built on the **raw** value for now; `USA_cleaning.cap_gold_outliers()`
(winsorize at the 99.5th percentile) is provided but **off by default**. Candidate fixes to
evaluate later this phase:
- (a) winsorize `gold_24k` at the 99.5th percentile (the provided helper);
- (b) IQR-based upper cap;
- (c) log-space z-score flagging of point outliers;
- (d) targeted correction of the specific 173.62 $/g decimal-shift row.

## Scoping notes (honest status)

- **ISO3 standardization** is emitted in the feature table (`country_code = 'USA'`) and the
  geo/reserves sources are already ISO3, but `raw_prices.country` was **not** rewritten — USA
  is selected at build via `devise = 'USD'`, per the "don't mutate sources" hard-scope rule.
- **`timestamp → DATE`** is realized for the feature table's `date`; the source columns
  (`raw_prices`/`macro_data`/`vix_oil_data`) still store `timestamp`/mixed-case. The source-level
  migration was out of surgical scope and is deferred.

---

_Phase 2 is complete; Phase 3 (Modeling) is unblocked. The feature table `ml.us_gold_features_daily`
is the single training input for Phase 3._
