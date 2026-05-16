# Phase 3 — Data Preparation

> Status: **TODO — gated on Phase 2 (EDA) completion**
> Maps to project_plan.md: PHASE 2 (Data Preparation & Feature Engineering)
> CRISP-DM rule: do not start any task below until Phase 2 (Data Understanding) reaches DONE — EDA report and imputation strategy must exist first. No pragmatic shortcuts.

## Goal
Produce `ml.us_gold_features_daily`: a Stage-1, model-ready table with one row per day (USA), target column `y = gold_24k` in USD, plus all engineered, exogenous, and calendar features.

## Inputs (from Phase 2)
- All 6 source tables populated: `public.cleaned_prices`, `public.geopolitical_data`, `public.macroeconomic_data`, `public.vix_oil_data`, `public.reserves_gold`, `public.dim_date`.
- **EDA report from Phase 2 (Data Understanding) — REQUIRED**, including:
  - Trend / seasonality / stationarity verdict on `gold_24k`.
  - Correlation findings vs every exogenous feature.
  - **Imputation strategy** per source (weekend/holiday gold gaps = forward-fill; decision recorded in `02-data-understanding.md` § Decisions).
- Phase 2 acceptance criteria all ticked. Do not proceed otherwise.

## Tasks (verbatim from project_plan.md PHASE 2)

- [ ] Keep only `gold_24k` — exclude `gold_22k`, `gold_21k`, `gold_18k`, `gold_14k`, `gold_10k`, and `silver_price` from the modeling path.
- [ ] Standardize `country_code` to ISO3 across all tables. Current French slugs in `cleaned_prices.country` (`etats-unis`, `tunisie`, `france`, …) must map to ISO3 codes (`USA`, `TUN`, `FRA`, …).
- [ ] Fix date column types: `cleaned_prices.date` is currently `TEXT` → convert to `DATE`.
- [ ] Build `ml.us_gold_features_daily`:
    - [ ] Filter: `country_code = 'USA'` AND `metals = 'gold'`.
    - [ ] Join `macroeconomic_data` — forward-fill monthly → daily.
    - [ ] Join `vix_oil_data` — daily.
    - [ ] Join `geopolitical_data` — filter `country = 'USA'`, daily.
    - [ ] Join `reserves_gold` — forward-fill annual → daily.
    - [ ] Compute `y_lag_1`, `y_lag_7`, `y_lag_30`.
    - [ ] Compute `y_ma_7`, `y_ma_30`.
    - [ ] Compute `y_vol_30` (rolling std of log-returns).
    - [ ] Add calendar features from `dim_date`.

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

### Calendar (from `dim_date`)
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
- [ ] `cleaned_prices.date` is type `DATE` (not `TEXT`).

## Open questions
- Trading-day calendar: use NYSE business days, or every calendar day forward-filled? — decision affects row count and the meaning of `y_lag_1`. Lock this in Phase 2 EDA.
