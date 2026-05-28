# Phase 3 — Data Preparation

> Status: **DONE** — `ml.us_gold_features_daily` built (2 448 × 27) and verified; see [`reports/phase2-dataprep/SUMMARY.md`](../reports/phase2-dataprep/SUMMARY.md).
> Maps to project_plan.md: PHASE 2 (Data Preparation & Feature Engineering)
> CRISP-DM rule: Phase 2 (Data Understanding / EDA) reached DONE first — EDA report and imputation strategy exist. No pragmatic shortcuts were taken.

## Goal
Produce `ml.us_gold_features_daily`: a Stage-1, model-ready table with one row per day (USA), target column `y = gold_24k` in USD, plus all engineered, exogenous, and calendar features.

## Inputs (from Phase 2)
- All 5 source tables populated: `public.raw_prices`, `public.geopo_data`, `public.macro_data`, `public.vix_oil_data`, `public.reserves_gold`. (No `dim_date` table — calendar features are derived in pandas.)
- **EDA report from Phase 2 (Data Understanding) — REQUIRED**, including:
  - Trend / seasonality / stationarity verdict on `gold_24k`.
  - Correlation findings vs every exogenous feature.
  - **Imputation strategy** per source (weekend/holiday gold gaps = forward-fill; decision recorded in `02-data-understanding.md` § Decisions).
- Phase 2 acceptance criteria all ticked. Do not proceed otherwise.

## Tasks (from project_plan.md PHASE 2) — DONE

- [x] Keep only `gold_24k` — other karats (`gold_22k/18k/14k/10k`) and `silver_price` dropped from the modeling path (`clean_prices` keeps `date` + `gold_24k`).
- [~] Standardize `country_code` to ISO3 — **done at feature-build, not by mutating sources.** The output table carries `country_code = 'USA'`; `geopo_data`/`reserves_gold` are already ISO3; `raw_prices` is selected via `devise = 'USD'` and left untouched (per the CLAUDE.md hard-scope rule: filter at feature-build, do not rewrite source tables).
- [~] Date types + column renames — **applied in-pandas at feature-build**, not as source `ALTER`s. The build parses `date` to datetime, coerces the text-typed macro columns to numeric and lowercases `CPI/GDP/DXY/Unemployment → cpi/gdp/dxy/unemployment`, and maps `vix_oil_data` `Date/oil → date/oil_price`. The persisted `ml.us_gold_features_daily.date` is type `DATE`. Source tables still store `timestamp`/mixed-case — the source-level migration was out of surgical scope and is deferred.
- [x] Build `ml.us_gold_features_daily`:
    - [x] Filter `country_code = 'USA'` (target = `gold_24k`).
    - [x] Join `macro_data` — forward-filled monthly/quarterly → daily.
    - [x] Join `vix_oil_data` — daily (holiday gaps forward-filled).
    - [x] Join `geopo_data` — `country = 'USA'`, daily.
    - [x] Join `reserves_gold` — annual → daily via a `year-01-01` date + forward-fill.
    - [x] Compute `y_lag_1`, `y_lag_7`, `y_lag_30`.
    - [x] Compute `y_ma_7`, `y_ma_30`.
    - [x] Compute `y_vol_30` (rolling std of log-returns).
    - [x] Derive calendar features in pandas (`month`, `quarter`, `day_of_week`, `is_month_end`) from the `date` column.

## Feature spec (authoritative — do not deviate)

### Engineered (from the gold price series itself)

Notation: `y_t` = `gold_24k` price on day `t` (USD).

| Feature    | Formula                                          |
|------------|--------------------------------------------------|
| `y_lag_1`  | `y(t-1)`                                         |
| `y_lag_7`  | `y(t-7)`                                         |
| `y_lag_30` | `y(t-30)`                                        |
| `y_ma_7`   | `mean(y[t-6 : t])`                               |
| `y_ma_30`  | `mean(y[t-29 : t])`                              |
| `y_vol_30` | `std( ln(y_t / y_{t-1}) )` over the last 30 days |

Constants: `LAG_WINDOWS = [1, 7, 30]`, `MA_WINDOWS = [7, 30]`, `VOL_WINDOW = 30`.

### Exogenous (14 columns total)

- **Macro** (FRED, monthly → forward-filled to daily): `fed_rate`, `real_rate`, `cpi`, `gdp`, `dxy`, `unemployment`.
- **Market** (Yahoo, daily): `vix`, `oil_price`.
- **Geo** (GDELT, filter `country = 'USA'`, daily): `total_events`, `political_events`, `war_intensity`, `crisis_index`, `political_pressure`.
- **Reserves** (World Bank, annual → forward-filled to daily): `gold_reserves`.

### Calendar (derived in pandas from the `date` column)
`month`, `quarter`, `day_of_week`, `is_month_end`.

## Outputs (for Phase 4)
- Table `ml.us_gold_features_daily` in PostgreSQL `metals_db`.
- One row per day, USA only, `gold_24k` as target column `y`.
- All engineered, exogenous, and calendar features present.

## Acceptance criteria (gate to Phase 4) — verified 2026-05-26
- [x] Table `ml.us_gold_features_daily` exists in schema `ml`.
- [x] Row count = distinct USA price dates in `[2017-01-01, today]` → **2 448 rows** (2017-01-02 → 2026-05-22).
- [x] Target column `y` non-null for every row (0 nulls).
- [x] No nulls in `y_lag_*`, `y_ma_*`, `y_vol_30` after the warm-up window — nulls confined to rows 0–29.
- [x] All 14 exogenous columns present and forward-filled (0 nulls after warm-up).
- [x] All 4 calendar columns present.
- [~] `country_code` ISO3 — emitted as `'USA'` in the feature table; source tables not rewritten (see Tasks note / hard-scope rule).
- [~] `raw_prices.date` → `DATE` — the feature table's `date` is `DATE`; the source `raw_prices.date` remains `timestamp` (converted in-pandas at read; source `ALTER` deferred).

## Decisions locked (Phase 2)
- **Date window:** exogenous sources extracted from `2016-01-01` (forward-fill warm-up); the feature table starts at the first gold trading day (`>= 2017-01-01`, i.e. 2017-01-02). `DATE_END` = today (dynamic).
- **Trading-day calendar:** **NYSE trading days** — the grid is the set of distinct dates observed in the USA gold series (they already encode NYSE holidays). `y_lag_1` therefore means *previous trading day*, and the row count equals the number of distinct USA price dates.
- **Outliers:** the table is built on **raw `gold_24k`** (no capping) — see below.

## Outlier handling (deferred)
Phase 1 flagged the series max (173.62 $/g) as an implausible scraping error (real peak ~90–95 $/g). The table is built on the raw value for now; `USA_cleaning.cap_gold_outliers()` is provided but **off by default**. Candidate fixes to evaluate later this phase:
- (a) winsorize `gold_24k` at the 99.5th percentile (the provided helper);
- (b) IQR-based upper cap;
- (c) log-space z-score flagging of point outliers;
- (d) targeted correction of the specific 173.62 $/g decimal-shift row.

## Artifacts
- Build code: `USA_cleaning.py` (cleaning + feature build + write) and `data_access.py` (reusable cached DB readers), repo root.
- Output table: `ml.us_gold_features_daily` in `metals_db`.
- Summary: [`reports/phase2-dataprep/SUMMARY.md`](../reports/phase2-dataprep/SUMMARY.md).

## Open questions (resolved)
- ~~Trading-day calendar: NYSE business days vs every calendar day forward-filled?~~ **Resolved:** NYSE trading days (see Decisions locked).
