# Phase 2 — Data Understanding

> Status: ✅ DONE — all 6 EDA tasks complete; verdicts recorded in `reports/phase1-eda/SUMMARY.md`, verified against the re-run notebook outputs.
> Maps to project_plan.md: PHASE 0 (Data Infrastructure) + PHASE 1 (EDA)
> CRISP-DM rule: this phase must reach DONE before Phase 3 (Data Preparation) starts. No pragmatic shortcuts.
> Deliverables: notebook `notebooks/01_eda_phase1_copieeee.ipynb` and report `reports/phase1-eda/SUMMARY.md`.

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

### EDA (DONE — project_plan.md PHASE 2)
- [x] Visualize gold 24K price trend (USA, 2017 → today). — 2 448 rows, 2017-01-02→2026-05-22, 36.98→144.99 $/g (~3.9×).
- [x] Correlation matrix: `gold_24k` vs every exogenous feature. — 13 features ranked (Pearson + Spearman); top co-trend gdp/cpi. `gold_reserves` dropped (spurious co-trend, see re-iteration note).
- [x] Stationarity tests on `gold_24k`: ADF and KPSS. — `log_returns` is stationary by both (target locked).
- [x] STL decomposition: trend + seasonality + residual. — trend-dominated (σ 27.55 vs seasonal 3.45).
- [x] Overlay geopolitical event spikes onto price moves. — 68 spike days; post-spike uplift non-significant (p = 0.15).
- [x] Missing-value analysis per source table; define imputation strategy (forward-fill for monthly/annual sources, decision for weekend/holiday gaps in daily price series).

## Outputs (for Phase 3)
- EDA report (notebook or markdown) summarizing trend, seasonality, correlations, stationarity verdict, and the imputation strategy chosen for each source.
- Confirmed list of usable predictors (should match `ALL_EXOG_FEATURES` from `project_plan.md`; flag any predictor with unworkable missingness).

## Acceptance criteria (gate to Phase 3)
- [x] EDA report exists and covers all 6 EDA tasks above. — `reports/phase1-eda/SUMMARY.md`.
- [x] Imputation strategy is documented per source (consistent with forward-fill rules in Phase 3). — forward-fill for all sources; GDELT needs none (0% missing).
- [x] No surprises in coverage: every source has data spanning at least `2017-01-01 → today` for USA. — prices 2017-01-02→2026-05-22; exogenous sources span 2016→2026.

## EDA re-iteration (T+30 pivot, no reserves)
Triggered after Phase-3 (T+1) modeling showed every model tied to a random walk. The notebook `01_eda_phase1_copieeee.ipynb` was re-iterated with a light in-notebook cleaning block and an extended analysis; the persisted (main) cleaning is the **next step**.
- **Import scope:** four source tables only — `raw_prices`, `geopo_data`, `macro_data`, `vix_oil_data`. `reserves_gold` is no longer loaded; `gold_reserves` is dropped from the Stage-1 feature set (spurious co-trend). Exogenous list is now **13** features.
- **Cleaning block:** dates → datetime; the three exogenous tables filtered from **2014-01-01** (forward-fill warm-up); `usa_features` built from `raw_prices` (USD) keeping `gold_24k` only, raw values as-is (no per-day median dedup); numerical exogenous columns merged + forward-filled onto the gold trading-day grid, restricted to ≥ 2017.
- **Added analyses:** explicit null / dtype / `describe` checks; ACF / PACF (autocorrelation); plus the existing trend, stationarity (ADF/KPSS), STL (trend/seasonality/residual), correlation (multivariate), and geopolitical-spike sections.
- **Horizon:** re-framed **T+1 → T+30** (target-agnostic: level `y(t+30)` and 30-day cumulative log-return both shown). Target representation locked at the modeling step.

## Decisions (carry into Phase 3 — Data Preparation)
- **Weekend / holiday gold-price gaps: forward-fill.** This decision propagates into the Phase 3 imputation strategy.
- **`gold_reserves` dropped from the Stage-1 feature set.** Source table retained; `USA_cleaning.py` / `models/utils.py` / `ml.us_gold_features_daily` aligned in the main cleaning step.

## Open questions (resolved)
- ~~Does GDELT have any USA-day gaps inside 2017→today that would require imputation?~~ **Resolved:** No. GDELT USA coverage is fully dense (3 797 daily rows, 2016-01-01→2026-05-24, 0% missing across all 5 columns) — no imputation needed.
- ~~**Carried to Phase 2 (open):** trading-day calendar — NYSE business days (~252/yr) vs every calendar day forward-filled (365/yr).~~ **Resolved in Phase 2:** NYSE trading days (grid = observed USA price dates). See `refactor/03-data-preparation.md` § Decisions locked.

## EDA artifacts
- Notebook: [`notebooks/01_eda_phase1_copieeee.ipynb`](../notebooks/01_eda_phase1_copieeee.ipynb) — visuals stay inline; run manually.
- Report: [`reports/phase1-eda/SUMMARY.md`](../reports/phase1-eda/SUMMARY.md) — text-only verdicts and tables, filled from the re-run notebook outputs and verified. Acceptance-criteria boxes above are ticked and the Status header is **DONE**.
