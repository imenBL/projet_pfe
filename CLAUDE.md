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
- **Forecast horizon**: **T+30** (~one month / 30 trading days ahead). The earlier T+1 framing collapsed to a random walk; the T+30 target representation (price level `y(t+30)` vs cumulative log-return) is locked at the modeling step.
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
- (`gold_reserves` / `RESERVE_FEATURE` was **dropped** from the Stage-1 feature set — flagged as a spurious co-trend feature in EDA. The `reserves_gold` source table is retained for other stages; it is simply not joined into the feature set.)

`ALL_EXOG_FEATURES = MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES` (13 columns).

### Calendar

`CALENDAR_FEATURES = ["month", "quarter", "day_of_week", "is_month_end"]` — **derived in pandas** from the `date` column at feature-build time. (The `dim_date` table was removed from the pipeline.)

## Modeling rules (Phase 3, when reached)

- **Forecast horizon**: **T+30** (one month). The completed t+1 run is retained only as the random-walk baseline that motivated the pivot; the T+30 target representation is locked when the modeling step is re-run.
- **Split**: chronological **70 / 15 / 15** (train / val / test). **Never shuffle**; never use random splits.
- **Models to compare** (in this order — baseline first): ARIMA / SARIMA (univariate) → XGBoost / LightGBM (full feature set) → LSTM → Temporal Fusion Transformer.
- **Metrics**: `EVAL_METRICS = ["MAE", "RMSE", "MAPE", "R2"]`. Report all four for every model.
- **Interpretability**: SHAP feature importance is required for the final model selection.

## Phase status (CRISP-DM ordering, from project_plan.md)

CRISP-DM order is **canonical and non-negotiable** for this project: Data Understanding (EDA) must complete before Data Preparation begins. The user has explicitly directed: *"no pragmatic shortcuts."* Do **not** start the feature-table build, schema fixes, or ISO3 standardization before the EDA report exists and Phase 1 acceptance criteria are met. **Phases 1 and 2 are now complete (gates satisfied)**, so Phase 3 (Modeling) may proceed.

| Phase | Scope                                          | Status |
|-------|------------------------------------------------|--------|
| 0     | Data infrastructure (scrapers, APIs, DB setup) | **DONE** |
| 1     | EDA (trend viz, correlation, ADF/KPSS, STL, geopolitical-spike analysis, missing-value strategy) | **DONE** |
| 2     | Data prep + feature engineering → `ml.us_gold_features_daily` | **DONE** |
| 3     | Modeling (ARIMA → XGBoost/LightGBM → LSTM → TFT, SHAP, best-model selection) | **IN PROGRESS** (notebooks in `models/`: ARIMA, LinReg, DecisionTree, XGBoost, LightGBM, Prophet, LSTM done; TFT deferred) |
| 4     | Results & reporting (model-comparison table, predicted-vs-actual plots, SHAP plots, PFE report, optional REST API / dashboard) | TODO |

**Active iteration — T+30 pivot.** The t+1 modeling found **daily gold is ~a random walk at h=1** (every model tied to the naive baseline; see `reports/phase3-modeling/`). Acting on that, the project is pivoting to **T+30** and the EDA (`notebooks/01_eda_phase1_copieeee.ipynb`) was re-iterated: it now has a light in-notebook cleaning block (4 source tables, no `reserves_gold`, `usa_features`), extended analysis (null/type/describe, ACF/PACF), and a target-agnostic T+30 framing section. **When asked "what's next"**, the answer is the **main cleaning step** (`notebooks/cleaning.ipynb` / `USA_cleaning.py`): align the persisted code to T+30 and drop `gold_reserves` from `USA_cleaning.py` / `models/utils.py` / rebuild `ml.us_gold_features_daily`, then re-run the modeling at T+30 (lock the level-vs-return target there). The Phase-3 t+1 results stand as the random-walk baseline. Expert read-throughs: `interpretation/01_eda_phase1.md` and `interpretation/03_modeling.md` (French).

**Phase 3 (Modeling) — delivered as academic notebooks in `models/`.** Six notebooks, run in order (`01_preprocessing` → `02_arima` → `03_simple_model` → `04_modele_d_ensemble` → `05_LSTM` → `06_comparison`), all sharing **`models/utils.py`** (one load + chronological 70/15/15 split + price-scale metrics) and writing aligned test predictions to `models/predictions/<name>.csv`. Execute headlessly with `.\projet\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace models\<nb>.ipynb`. Locked decisions: **t+1, return-based** forecasting (predict next-day log-return, reconstruct price; metrics on the $/g scale — leakage-safe, avoids the tree extrapolation trap); univariate ARIMA; `SEED = 42`; LSTM in **PyTorch** (TensorFlow has no Python-3.14 build). Result: daily gold is **near a random walk** at h=1 — ARIMA = (0,1,0); the LSTM is nominally best but tied with the random walk; tuned trees/LinReg/Prophet do worse. **Deferred:** TFT. The old `modeling/` `.py` package was retired in favour of the notebooks. `data_access.load_features()` reads `ml.us_gold_features_daily`.

**T+30 pivot — code alignment pending.** The t+1, return-based framing above is now the baseline; the project is moving to **T+30**. The EDA notebook and specs/docs already reflect this (and drop `gold_reserves`), but the persisted modeling code is **not yet aligned**: `models/utils.py` still has `TARGET = "ret_next"` (shift(-1)) and `RESERVE_FEATURE` in `FEATURE_COLUMNS`, and `ml.us_gold_features_daily` still carries `gold_reserves` — all aligned in the next (main cleaning) step. There is also an **experimental `models_medium/`** directory (`utils_h.py` + `models_h.py`: T+30/T+60, direct price-level target, RW-with-drift benchmark, Diebold-Mariano, conformal intervals) that is **not** wired into the workflow and has no notebooks/report — leave it untouched; review (adopt / rebuild / remove) at the T+30 modeling step.

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

- Make surgical changes only.
- Do not duplicate functionality — always prefer modifying and reusing existing logic.
- Add new functions only when equivalent logic does not already exist.
- Do not take a bug report’s suggested fix at face value; verify that it targets the correct architectural layer.
- For any ambiguity, uncertainty, or architectural decision, ask the user before proceeding.
- This project is an academic final-year education project, so keep the implementation reasonably       simple, maintainable, and aligned with educational project standards. Avoid over-engineering, excessive abstraction, or unnecessarily sophisticated enterprise patterns unless clearly required.