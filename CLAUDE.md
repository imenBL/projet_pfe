# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`project_plan.md` is the authoritative spec for this project (Projet de Fin d'Études — PFE). The constraints below are extracted from it and **must not be violated** without an explicit user request. When project_plan.md disagrees with this file, project_plan.md wins.

Phase-level checklists live in `refactor/<NN>-<phase>.md` (CRISP-DM breakdown — Business Understanding → Data Understanding → Data Preparation → Modeling → Evaluation → Deployment). When working on a specific phase, open the matching file and use its **Tasks** list and **Acceptance criteria** as the source of truth. Start at [`refactor/README.md`](refactor/README.md).

## Hard scope constraints (Stage 1 only)

The user has explicitly stated: *"Propre et focalisé exclusivement sur l'Étape 1"* — clean and focused exclusively on Stage 1. Anything that doesn't serve Stage 1 is out of scope.

- **Target metal**: gold only. Not silver. `silver_price` is excluded from the modeling pipeline.
- **Target karat**: `gold_24k` only. The columns `gold_22k`, `gold_18k`, `gold_14k`, `gold_10k` are explicitly excluded — drop them during feature-build, do not engineer features from them, do not include them in EDA correlations targeting `y`. (`gold_21k` was dropped at source and no longer exists in `raw_prices`.)
- **Target country**: USA only. Source tables hold 12 countries; **filter to USA at the feature-build step**, do not delete other countries from source tables.
- **Currency**: USD only.
- **Period**: `2017-01-01` → today (`DATE_START = "2017-01-01"`, `DATE_END` = dynamic current date).
- **Stage 2** (all other countries, prices-only) is **out of scope** — do not add code, schemas, or features for it. Don't generalize "for future stages" unless asked.
- **Target variable**: column named `y` in `ml.us_gold_features_daily`, equal to `gold_24k` in USD.

## Authoritative feature spec

These names, windows, and formulas come straight from project_plan.md. **Do not invent additional features, rename them, or change window sizes** without explicit instruction. The exact lists are also encoded as Python constants at the bottom of `project_plan.md` — treat them as the contract.

### Engineered (from the gold price series itself)

| Feature       | Formula                                              | Window |
|---------------|------------------------------------------------------|--------|
| `y_lag_1`     | `y(t-1)`                                             | 1 day  |
| `y_lag_7`     | `y(t-7)`                                             | 7 days |
| `y_lag_30`    | `y(t-30)`                                            | 30 days |
| `y_ma_7`      | `mean(y[t-6 : t])`                                   | 7-day rolling avg |
| `y_ma_30`     | `mean(y[t-29 : t])`                                  | 30-day rolling avg |
| `y_vol_30`    | `std( ln(y_t / y_{t-1}) )` over the last 30 days     | 30-day rolling std of log-returns |

Constants: `LAG_WINDOWS = [1, 7, 30]`, `MA_WINDOWS = [7, 30]`, `VOL_WINDOW = 30`.

### Exogenous (joined in from source tables)

- **`MACRO_FEATURES`** (FRED, monthly → **forward-filled to daily**): `fed_rate`, `real_rate`, `cpi`, `gdp`, `dxy`, `unemployment`. Source FRED series IDs are in `data_collection/fredAPI.py` (`FEDFUNDS`, `REAINTRATREARAT10Y`, `CPIAUCSL`, `GDP`, `DTWEXBGS`, `UNRATE`).
- **`MARKET_FEATURES`** (Yahoo Finance, daily): `vix`, `oil_price` (tickers `^VIX` and `CL=F`).
- **`GEO_FEATURES`** (GDELT, daily, **filter `country = 'USA'`**): `total_events`, `political_events`, `war_intensity`, `crisis_index`, `political_pressure`.
- **`RESERVE_FEATURE`** (World Bank, annual → **forward-filled to daily**): `gold_reserves`.

`ALL_EXOG_FEATURES = MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES + RESERVE_FEATURE` (14 columns).

### Calendar

`CALENDAR_FEATURES = ["month", "quarter", "day_of_week", "is_month_end"]` — **derived in pandas** from the `date` column at feature-build time. (The `dim_date` table was removed from the pipeline.)

## Modeling rules (Phase 3, when reached)

- **Split**: chronological **70 / 15 / 15** (train / val / test). **Never shuffle**; never use random splits.
- **Models to compare** (in this order — baseline first): ARIMA / SARIMA (univariate) → XGBoost / LightGBM (full feature set) → LSTM → Temporal Fusion Transformer.
- **Metrics**: `EVAL_METRICS = ["MAE", "RMSE", "MAPE", "R2"]`. Report all four for every model.
- **Interpretability**: SHAP feature importance is required for the final model selection.

## Phase status (CRISP-DM ordering, from project_plan.md)

CRISP-DM order is **canonical and non-negotiable** for this project: Data Understanding (EDA) must complete before Data Preparation begins. The user has explicitly directed: *"no pragmatic shortcuts."* Do **not** start the feature-table build, schema fixes, or ISO3 standardization before the EDA report exists and Phase 1 acceptance criteria are met. **Phase 1 is now complete (gate satisfied)**, so Phase 2 may proceed.

| Phase | Scope                                          | Status |
|-------|------------------------------------------------|--------|
| 0     | Data infrastructure (scrapers, APIs, DB setup) | **DONE** |
| 1     | EDA (trend viz, correlation, ADF/KPSS, STL, geopolitical-spike analysis, missing-value strategy) | **DONE** |
| 2     | Data prep + feature engineering → `ml.us_gold_features_daily` | **TODO — next up** |
| 3     | Modeling (ARIMA → XGBoost/LightGBM → LSTM → TFT, SHAP, best-model selection) | TODO |
| 4     | Results & reporting (model-comparison table, predicted-vs-actual plots, SHAP plots, PFE report, optional REST API / dashboard) | TODO |

When asked "what's next", the answer is **Phase 2 — Data Preparation**. Phase 1 (EDA) is **complete** — all 6 EDA tasks done and verified; verdicts live in `reports/phase1-eda/SUMMARY.md` and the full contract in `refactor/02-data-understanding.md`. The Phase-2 checklist (build `ml.us_gold_features_daily`) lives in `refactor/03-data-preparation.md`.

**Phase 1 is complete; Phase 2 (Data Preparation) is unblocked.** Phase 2 builds `ml.us_gold_features_daily` per the checklist in `refactor/03-data-preparation.md` (drop non-24K karats and silver, ISO3 country codes, `timestamp → DATE`, join + forward-fill, compute lags / MAs / volatility, derive calendar features in pandas). (The `timestamp → DATE` column conversion has already been started as a standalone schema fix.)

## Running the pipeline

The repo ships a Python venv at `projet/` (gitignored). Use it directly. Dependencies are pinned in `requirements.txt` at the repo root (and also listed informally in `fichier.txt`): pandas, numpy, scipy, sqlalchemy, psycopg2, openpyxl, yfinance, beautifulsoup4, requests, fredapi, google-cloud-bigquery, matplotlib, seaborn, statsmodels.

```powershell
# Run the orchestrator (PowerShell)
.\projet\Scripts\python.exe main.py
```

`main.py` is the single entry point and now runs the **full pipeline** end-to-end: it scrapes gold + silver, merges them (`data_cleaning/merge_metals.merge_gold_silver`), inserts the merged `raw_prices`, then collects and inserts GDELT, Yahoo Finance, World Bank reserves, and FRED. There are no tests, linters, or build steps configured.

## Database (`metals_db`, PostgreSQL)

Hardcoded in `db_settings.py`: `postgres` / `admin` on `localhost:5432`. Schemas defined by project_plan.md:

- **`public`** (`DB_SCHEMA_SOURCE`) — source-of-truth tables, all countries:
  `raw_prices` (daily gold **and** silver prices merged, 12 countries, `devise` populated per country) · `geopo_data` (daily, all countries) · `macro_data` (monthly, USA) · `vix_oil_data` (daily, USA) · `reserves_gold` (annual, all countries). The `dim_date` table was removed — calendar features are derived in pandas.
- **`ml`** (`DB_SCHEMA_ML`) — `ml.us_gold_features_daily` is the Stage-1 training table (one row = one day, target column = `y`). **This table does not exist yet** — Phase 2 (Data Preparation) builds it.

The DDL in `db_settings.create_tables()` is **not idempotent** for most tables (no `IF NOT EXISTS` except `reserves_gold`) — calling it twice will error.

**Implementation status (schema migration in progress).** The target schema uses `DATE` for every date column and adds a `date` column to `reserves_gold` for temporal alignment. Not yet fully realized in the live DB: `raw_prices`, `macro_data`, and `vix_oil_data` still store `timestamp` (the `timestamp → DATE` conversion is the first Data-Preparation fix, already started); `reserves_gold` still has no `date` column; `macro_data` columns are still mixed-case (`CPI/GDP/DXY/Unemployment`) and `vix_oil_data` still uses `"Date"` + `oil` (target: lowercase `date` + `oil_price`).

## Architecture

The codebase is a **data-ingestion pipeline** feeding the warehouse. Modeling code does not exist yet.

```
main.py                       # Orchestrator — scrape → merge → DB inserts (full pipeline)
db_settings.py                # PostgreSQL connection (SQLAlchemy + psycopg2), DDL, insert_* helpers
data_cleaning/
  merge_metals.py             # Cleans + merges gold & silver into raw_prices (FR month names, devise mapping, float parsing)
data_collection/              # One module per upstream data source
  Gold_scraper.py             #   exchange-rates.org HTML scrape (12 countries × 2017–2026)
  Silver_scraper.py           #   same site, silver — merged into raw_prices but excluded from Stage-1 modeling
  Gdelt_Project.py            #   GDELT events via BigQuery → daily geopolitical indices per country
  fredAPI.py                  #   FRED macro series
  yahoo_finance.py            #   ^VIX and CL=F (crude oil) close prices
Reserves_Gold.xlsx            # World Bank gold reserves — loaded via db_settings.insert_excel()
notebooks/                    # EDA notebooks (Phase-1 work) + cleaning.ipynb
project_plan.md               # SPEC — authoritative source for scope, schema, features, and phases
```

### Data flow

1. **Collect** — `data_collection/*` returns DataFrames (no I/O beyond upstream API calls).
2. **Clean + merge** — `data_cleaning/merge_metals.merge_gold_silver(gold_df, silver_df)` converts French dates (`janv.`, `févr.`, …) to datetime, maps each country to its `devise`, parses prices to float, and merges gold + silver into one `raw_prices` frame.
3. **Insert** — `db_settings.insert_*(df)` writes via `df.to_sql(..., if_exists="append")`. Schema is created by `init_database()` → `create_tables()`.

### Known pitfalls in current code

- `db_settings.insert_Fred_Api_data` writes to table **`macro_data`**, but `create_tables()` declares **`macroeconomic_data`** — the DDL table is never used; the live table is `macro_data`. Reconcile the name (Data-Preparation cleanup).
- `db_settings.create_tables()` issues DDL on a connection that is **never committed** (SQLAlchemy 2.0 autobegin), so the declared types don't take effect — `to_sql(..., if_exists="append")` then (re)creates the tables with pandas-inferred types. That's why `raw_prices`/`macro_data`/`vix_oil_data` are `timestamp` despite the DDL saying `DATE`.
- `raw_prices.date` is currently `timestamp`; target is `DATE` (conversion already started). `raw_prices.country` is still the French slug (`etats-unis`, …) — Data Preparation standardizes it to ISO3.
- `macro_data` columns are mixed-case (`CPI/GDP/DXY/Unemployment`) and `vix_oil_data` uses `"Date"` + `oil`; the feature spec expects lowercase `cpi/gdp/dxy/unemployment` and `oil_price` — rename during Data Preparation.
- The `dim_date` table is no longer built or present; calendar features are derived in pandas.
- GDELT credentials live in `gdelt-key.json` (gitignored). `data_collection/Gdelt_Project.py` sets `GOOGLE_APPLICATION_CREDENTIALS` to an absolute Windows path — change it if running elsewhere.
- The FRED API key is hardcoded in `data_collection/fredAPI.py`. Don't rotate it in committed code; if exposed, regenerate via the FRED portal.
- Gold reserves come from `Reserves_Gold.xlsx` via `db_settings.insert_excel()` (there is no World Bank API collector in the new pipeline).


### Implementation rules

Make surgical changes only.
Do not duplicate functionality — always prefer modifying and reusing existing logic.
Add new functions only when equivalent logic does not already exist.
Before writing code that makes a non-obvious choice, ask: “Why this and not the alternative?” If you cannot answer, investigate until you can — do not implement first and justify later.
If neighboring code follows a different pattern than what you intend to introduce, determine why before deviating — those decisions are often load-bearing, not stylistic.
Do not take a bug report’s suggested fix at face value; verify that it targets the correct architectural layer.
Implementation and fixes must be done according to best practices and industry and engineering standards.
For any ambiguity, uncertainty, or architectural decision, ask the user before proceeding.
This project is a final-year educational project, so ensure it is implemented rapidly and does not need to be production-ready.
