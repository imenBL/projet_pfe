# Phase 2 — Data Understanding

> Status: Collection DONE — EDA **IN PROGRESS** (notebook + report scaffold ready; user fills verdicts after running it)
> Maps to project_plan.md: PHASE 0 (Data Infrastructure) + PHASE 1 (EDA)
> CRISP-DM rule: this phase must reach DONE before Phase 3 (Data Preparation) starts. No pragmatic shortcuts.
> Deliverables: notebook `notebooks/01_eda_phase1.ipynb` and report `reports/phase1-eda/SUMMARY.md`.

## Goal
Catalog every data source, confirm coverage and grain match the project scope, and characterize the `gold_24k` time series and its candidate predictors before building features.

## Data sources inventory

| Source           | Table (`public.`)     | Grain   | Coverage              | Module                                          |
|------------------|-----------------------|---------|-----------------------|-------------------------------------------------|
| Web scrapers     | `raw_prices`          | Daily   | 12 countries          | `data_collection/Gold_scraper.py` + `Silver_scraper.py` (+ `data_cleaning/merge_metals.py`) |
| GDELT (BigQuery) | `geopo_data`          | Daily   | All countries         | `data_collection/Gdelt_Project.py`              |
| FRED API         | `macro_data`          | Monthly | USA only              | `data_collection/fredAPI.py`                    |
| Yahoo Finance    | `vix_oil_data`        | Daily   | USA only (^VIX, CL=F) | `data_collection/yahoo_finance.py`              |
| World Bank xlsx  | `reserves_gold`       | Annual  | All countries         | `db_settings.insert_excel()` ← `Reserves_Gold.xlsx` |

Centralized tables hold all countries; **filtering to USA happens at the feature-build step (Phase 3)**, never by deleting rows from source tables.

`raw_prices` merges gold and silver (gold karats + `silver_price`, with `devise` per country); `gold_21k` was dropped at source. The `dim_date` table was removed — calendar features are derived in pandas. **Target schema** (migration in progress — see `03-data-preparation.md`): `DATE` date columns everywhere, plus a new `date` column on `reserves_gold` for temporal alignment.

## Inputs (from Phase 1)
- Scope contract: USA / gold 24K / USD / 2017→today / Stage 1 only.

## Tasks

### Collection (DONE — project_plan.md PHASE 0)
- [x] Scrape gold + silver prices (12 countries, 2017–today) and merge into `raw_prices`.
- [x] Pull GDELT geopolitical events into `geopo_data`.
- [x] Pull FRED macro series into `macro_data`.
- [x] Pull `^VIX` and `CL=F` from Yahoo into `vix_oil_data`.
- [x] Load `Reserves_Gold.xlsx` into `reserves_gold`.

### EDA (TODO — project_plan.md PHASE 2)
- [ ] Visualize gold 24K price trend (USA, 2017 → today).
- [ ] Correlation matrix: `gold_24k` vs every exogenous feature.
- [ ] Stationarity tests on `gold_24k`: ADF and KPSS.
- [ ] STL decomposition: trend + seasonality + residual.
- [ ] Overlay geopolitical event spikes onto price moves.
- [ ] Missing-value analysis per source table; define imputation strategy (forward-fill for monthly/annual sources, decision for weekend/holiday gaps in daily price series).

## Outputs (for Phase 3)
- EDA report (notebook or markdown) summarizing trend, seasonality, correlations, stationarity verdict, and the imputation strategy chosen for each source.
- Confirmed list of usable predictors (should match `ALL_EXOG_FEATURES` from `project_plan.md`; flag any predictor with unworkable missingness).

## Acceptance criteria (gate to Phase 3)
- [ ] EDA report exists and covers all 6 EDA tasks above.
- [ ] Imputation strategy is documented per source (consistent with forward-fill rules in Phase 3).
- [ ] No surprises in coverage: every source has data spanning at least `2017-01-01 → today` for USA.

## Decisions (carry into Phase 3 — Data Preparation)
- **Weekend / holiday gold-price gaps: forward-fill.** This decision propagates into the Phase 3 imputation strategy.

## Open questions
- Does GDELT have any USA-day gaps inside 2017→today that would require imputation?

## EDA artifacts
- Notebook: [`notebooks/01_eda_phase1.ipynb`](../notebooks/01_eda_phase1.ipynb) — visuals stay inline; run manually.
- Report: [`reports/phase1-eda/SUMMARY.md`](../reports/phase1-eda/SUMMARY.md) — text-only verdicts and tables. User fills the placeholder sections after running the notebook, then ticks the acceptance-criteria boxes above and flips this Status header to **DONE**.
