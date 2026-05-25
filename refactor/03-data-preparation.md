# Phase 3 — Data Preparation

> Status: **TODO — gated on Phase 2 (EDA).** Exception: the `timestamp → DATE` schema fix is already in progress; the feature-table build itself stays gated on EDA.
> Maps to project_plan.md: PHASE 2 (Data Preparation & Feature Engineering)
> CRISP-DM rule: do not start any task below until Phase 2 (Data Understanding) reaches DONE — EDA report and imputation strategy must exist first. No pragmatic shortcuts.

## Goal
Produce `ml.us_gold_features_daily`: a Stage-1, model-ready table with one row per day (USA), target column `y = gold_24k` in USD, plus all engineered, exogenous, and calendar features.

## Inputs (from Phase 2)
- All 5 source tables populated: `public.raw_prices`, `public.geopo_data`, `public.macro_data`, `public.vix_oil_data`, `public.reserves_gold`. (No `dim_date` table — calendar features are derived in pandas.)
- **EDA report from Phase 2 (Data Understanding) — REQUIRED**, including:
  - Trend / seasonality / stationarity verdict on `gold_24k`.
  - Correlation findings vs every exogenous feature.
  - **Imputation strategy** per source (weekend/holiday gold gaps = forward-fill; decision recorded in `02-data-understanding.md` § Decisions).
- Phase 2 acceptance criteria all ticked. Do not proceed otherwise.

## Tasks (from project_plan.md PHASE 2)

- [ ] Keep only `gold_24k` — exclude `gold_22k`, `gold_18k`, `gold_14k`, `gold_10k`, and `silver_price` from the modeling path. (`gold_21k` no longer exists; `silver_price` now lives in the same `raw_prices` table.)
- [ ] Standardize `country_code` to ISO3 across all tables. Current French slugs in `raw_prices.country` (`etats-unis`, `tunisie`, `france`, …) must map to ISO3 codes (`USA`, `TUN`, `FRA`, …).
- [~] **In progress** — Convert date column types from `timestamp` to `DATE` on `raw_prices`, `macro_data`, and `vix_oil_data` (the first Data-Preparation fix, already started). Also rename `macro_data` columns to lowercase (`CPI/GDP/DXY/Unemployment` → `cpi/gdp/dxy/unemployment`) and `vix_oil_data` `"Date"/oil` → `date/oil_price`.
- [ ] Build `ml.us_gold_features_daily`:
    - [ ] Filter: `country_code = 'USA'` (target = `gold_24k`; there is no `metals` column anymore).
    - [ ] Join `macro_data` — forward-fill monthly → daily.
    - [ ] Join `vix_oil_data` — daily.
    - [ ] Join `geopo_data` — filter `country = 'USA'`, daily.
    - [ ] Join `reserves_gold` — forward-fill annual → daily (use the new `date` column once added).
    - [ ] Compute `y_lag_1`, `y_lag_7`, `y_lag_30`.
    - [ ] Compute `y_ma_7`, `y_ma_30`.
    - [ ] Compute `y_vol_30` (rolling std of log-returns).
    - [ ] Derive calendar features in pandas (`month`, `quarter`, `day_of_week`, `is_month_end`) from the `date` column.

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

## Acceptance criteria (gate to Phase 4)
- [ ] Table `ml.us_gold_features_daily` exists in schema `ml`.
- [ ] Row count equals the number of distinct dates in the USA price series within `[2017-01-01, today]` (per the trading-day convention chosen in Phase 2).
- [ ] Target column `y` is non-null for every row (or the missing-day policy is documented and consistent).
- [ ] No nulls in `y_lag_*`, `y_ma_*`, `y_vol_30` after the warm-up window (first 30 rows).
- [ ] All 14 exogenous columns present and forward-filled per the rules above.
- [ ] All 4 calendar columns present.
- [ ] `country_code` standardized to ISO3 in every source table.
- [ ] `raw_prices.date` is type `DATE` (converted from `timestamp`).

## Open questions
- Trading-day calendar: use NYSE business days, or every calendar day forward-filled? — decision affects row count and the meaning of `y_lag_1`. Lock this in Phase 2 EDA.
