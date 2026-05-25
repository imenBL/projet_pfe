# Phase 2 — Data Understanding

> Status: Collection DONE — EDA **IN PROGRESS** (notebook + report scaffold ready; user fills verdicts after running it)
> Maps to project_plan.md: PHASE 0 (Data Infrastructure) + PHASE 1 (EDA)
> CRISP-DM rule: this phase must reach DONE before Phase 3 (Data Preparation) starts. No pragmatic shortcuts.
> Deliverables: notebook `notebooks/01_eda_phase1.ipynb` and report `reports/phase1-eda/SUMMARY.md`.

## Goal
Catalog every data source, confirm coverage and grain match the project scope, and characterize the `gold_24k` time series and its candidate predictors before building features.

## Data sources inventory

| Source           | Table (`public.`)     | Grain   | Coverage              | Collector module                                |
|------------------|-----------------------|---------|-----------------------|-------------------------------------------------|
| Web scrapers     | `cleaned_prices`      | Daily   | 12 countries          | `Collector/Gold_scraper.py` (+ `cleaner_prices.py`) |
| GDELT (BigQuery) | `geopolitical_data`   | Daily   | All countries         | `Collector/Gdelt_Project.py`                    |
| FRED API         | `macroeconomic_data`  | Monthly | USA only              | `Collector/fredAPI.py`                          |
| Yahoo Finance    | `vix_oil_data`        | Daily   | USA only (^VIX, CL=F) | `Collector/yahoo_finance.py`                    |
| World Bank xlsx  | `reserves_gold`       | Annual  | All countries         | `database.insert_excel()` ← `Reserves_Gold.xlsx` |
| Internal         | `dim_date`            | Daily   | 2016 → today          | `database.insert_date()`                        |

Centralized tables hold all countries; **filtering to USA happens at the feature-build step (Phase 3)**, never by deleting rows from source tables.

## Inputs (from Phase 1)
- Scope contract: USA / gold 24K / USD / 2017→today / Stage 1 only.

## Tasks

### Collection (DONE — project_plan.md PHASE 0)
- [x] Scrape gold prices (12 countries, 2017–today).
- [x] Pull GDELT geopolitical events into `geopolitical_data`.
- [x] Pull FRED macro series into `macroeconomic_data`.
- [x] Pull `^VIX` and `CL=F` from Yahoo into `vix_oil_data`.
- [x] Load `Reserves_Gold.xlsx` into `reserves_gold`.
- [x] Populate `dim_date`.

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
