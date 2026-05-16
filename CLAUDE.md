# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`project_plan.md` is the authoritative spec for this project (Projet de Fin d'Études — PFE). The constraints below are extracted from it and **must not be violated** without an explicit user request. When project_plan.md disagrees with this file, project_plan.md wins.

Phase-level checklists live in `refactor/<NN>-<phase>.md` (CRISP-DM breakdown — Business Understanding → Data Understanding → Data Preparation → Modeling → Evaluation → Deployment). When working on a specific phase, open the matching file and use its **Tasks** list and **Acceptance criteria** as the source of truth. Start at [`refactor/README.md`](refactor/README.md).

## Hard scope constraints (Stage 1 only)

The user has explicitly stated: *"Propre et focalisé exclusivement sur l'Étape 1"* — clean and focused exclusively on Stage 1. Anything that doesn't serve Stage 1 is out of scope.

- **Target metal**: gold only. Not silver. `silver_price` is excluded from the modeling pipeline.
- **Target karat**: `gold_24k` only. The columns `gold_22k`, `gold_21k`, `gold_18k`, `gold_14k`, `gold_10k` are explicitly excluded — drop them during feature-build, do not engineer features from them, do not include them in EDA correlations targeting `y`.
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

- **`MACRO_FEATURES`** (FRED, monthly → **forward-filled to daily**): `fed_rate`, `real_rate`, `cpi`, `gdp`, `dxy`, `unemployment`. Source FRED series IDs are in `Collector/fredAPI.py` (`FEDFUNDS`, `REAINTRATREARAT10Y`, `CPIAUCSL`, `GDP`, `DTWEXBGS`, `UNRATE`).
- **`MARKET_FEATURES`** (Yahoo Finance, daily): `vix`, `oil_price` (tickers `^VIX` and `CL=F`).
- **`GEO_FEATURES`** (GDELT, daily, **filter `country = 'USA'`**): `total_events`, `political_events`, `war_intensity`, `crisis_index`, `political_pressure`.
- **`RESERVE_FEATURE`** (World Bank, annual → **forward-filled to daily**): `gold_reserves`.

`ALL_EXOG_FEATURES = MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES + RESERVE_FEATURE` (14 columns).

### Calendar

`CALENDAR_FEATURES = ["month", "quarter", "day_of_week", "is_month_end"]` — pulled from `dim_date`.

## Modeling rules (Phase 3, when reached)

- **Split**: chronological **70 / 15 / 15** (train / val / test). **Never shuffle**; never use random splits.
- **Models to compare** (in this order — baseline first): ARIMA / SARIMA (univariate) → XGBoost / LightGBM (full feature set) → LSTM → Temporal Fusion Transformer.
- **Metrics**: `EVAL_METRICS = ["MAE", "RMSE", "MAPE", "R2"]`. Report all four for every model.
- **Interpretability**: SHAP feature importance is required for the final model selection.

## Phase status (CRISP-DM ordering, from project_plan.md)

CRISP-DM order is **canonical and non-negotiable** for this project: Data Understanding (EDA) must complete before Data Preparation begins. The user has explicitly directed: *"no pragmatic shortcuts."* Do **not** start the feature-table build, schema fixes, or ISO3 standardization before the EDA report exists and Phase 1 acceptance criteria are met.

| Phase | Scope                                          | Status |
|-------|------------------------------------------------|--------|
| 0     | Data infrastructure (scrapers, APIs, DB setup) | **DONE** |
| 1     | EDA (trend viz, correlation, ADF/KPSS, STL, geopolitical-spike analysis, missing-value strategy) | **TODO — next up** |
| 2     | Data prep + feature engineering → `ml.us_gold_features_daily` | **TODO — gated on Phase 1** |
| 3     | Modeling (ARIMA → XGBoost/LightGBM → LSTM → TFT, SHAP, best-model selection) | TODO |
| 4     | Results & reporting (model-comparison table, predicted-vs-actual plots, SHAP plots, PFE report, optional REST API / dashboard) | TODO |

When asked "what's next", the answer is **Phase 1 — EDA**. The verbatim checklist from `project_plan.md`:

1. Gold 24K price trend visualization (USA, 2017 → today).
2. Correlation matrix: `gold_24k` vs all exogenous features.
3. Stationarity tests: ADF / KPSS on the `gold_24k` series.
4. Trend + seasonality decomposition (STL).
5. Geopolitical event spikes vs gold-price movements.
6. Missing-values analysis and imputation strategy.

See `refactor/02-data-understanding.md` for the full Phase-1 contract (inputs, tasks, outputs, acceptance criteria).

**Phase 2 (Data Preparation) is gated on Phase 1.** Only once the EDA report exists and Phase-1 acceptance criteria are met, Phase 2 builds `ml.us_gold_features_daily` per the checklist in `refactor/03-data-preparation.md` (drop non-24K karats and silver, ISO3 country codes, `TEXT → DATE`, join + forward-fill, compute lags / MAs / volatility, attach calendar features). Do not pre-start any of those tasks in parallel with Phase 1.

## Running the pipeline

The repo ships a Python venv at `projet/` (gitignored). Use it directly — there is no `requirements.txt` or `pyproject.toml`; dependencies are listed informally in `fichier.txt` (pandas, sqlalchemy, psycopg2-binary, openpyxl, yfinance, beautifulsoup4, fredapi, google-cloud-bigquery, matplotlib, seaborn, scipy).

```powershell
# Run the orchestrator (PowerShell)
.\projet\Scripts\python.exe main.py
```

`main.py` is the single entry point. **Most of it is commented out** by design — uncomment the relevant block to run a specific collector/cleaner stage. Only `insert_date(...)` runs by default. There are no tests, linters, or build steps configured.

## Database (`metals_db`, PostgreSQL)

Hardcoded in `database.py`: `postgres` / `admin` on `localhost:5432`. Schemas defined by project_plan.md:

- **`public`** (`DB_SCHEMA_SOURCE`) — source-of-truth tables, all countries:
  `cleaned_prices` (daily prices, 12 countries) · `geopolitical_data` (daily, all countries) · `macroeconomic_data` (monthly, USA) · `vix_oil_data` (daily, USA) · `reserves_gold` (annual, all countries) · `dim_date` (2016 → today).
- **`ml`** (`DB_SCHEMA_ML`) — `ml.us_gold_features_daily` is the Stage-1 training table (one row = one day, target column = `y`). **This table does not exist yet** — Phase 1 builds it.

The DDL in `create_tables()` is **not idempotent** for most tables (no `IF NOT EXISTS` except `reserves_gold`) — calling it twice will error.

## Architecture

The codebase is a **data-ingestion pipeline** feeding the warehouse. Modeling code does not exist yet.

```
main.py                  # Orchestrator — calls collectors → cleaner → DB inserts
database.py              # PostgreSQL connection (SQLAlchemy + psycopg2), DDL, insert_* helpers
cleaner_prices.py        # Normalizes scraped prices (French month names, devise extraction, float parsing)
Collector/               # One module per upstream data source (the canonical collectors)
  Gold_scraper.py        #   exchange-rates.org HTML scrape (12 countries × 2017–2026)
  Silver_scraper.py      #   same site, silver — NOT used in Stage 1
  Gdelt_Project.py       #   GDELT events via BigQuery → daily geopolitical indices per country
  fredAPI.py             #   FRED macro series
  yahoo_finance.py       #   ^VIX and CL=F (crude oil) close prices
  World_Bank_API.py      #   inflation / interest / FX — NOT the source for reserves_gold
Gold/, Cleaning/         # LEGACY one-off scripts (per-country CSV scrapers/cleaners). Not on the pipeline path.
Reserves_Gold.xlsx       # World Bank gold reserves — loaded via database.insert_excel(), NOT World_Bank_API.py
EDA.ipynb, EDA1.ipynb,   # Exploratory notebooks
test.ipynb
project_plan.md          # SPEC — authoritative source for scope, schema, features, and phases
```

### Data flow

1. **Collect** — `Collector/*` returns DataFrames (no I/O beyond upstream API calls).
2. **Clean** — `cleaner_prices.clean_data(df)` converts French dates (`janv.`, `févr.`, …) to `YYYY-MM-DD`, extracts ISO currency code into `devise`, and parses prices to float.
3. **Insert** — `database.insert_*(df)` writes via `df.to_sql(..., if_exists="append")`. Schema is created by `init_database()` → `create_tables()`.

### Known pitfalls in current code

- `database.insert_raw_data` writes to table `raw_data`, but the DDL creates `raw_prices`. Same mismatch: `insert_cleaned_data` writes `cleaned_data` vs. table `cleaned_prices`; `cleaner_prices.load_raw_data` reads `raw_data`. project_plan.md names `cleaned_prices` as the source of truth — reconcile to that.
- `cleaned_prices.date` is `TEXT`, not `DATE` — Phase 1 must fix.
- `cleaned_prices.country` is the French slug — Phase 1 must standardize to ISO3.
- GDELT credentials live in `gdelt-key.json` (gitignored). `Collector/Gdelt_Project.py` sets `GOOGLE_APPLICATION_CREDENTIALS` to an absolute Windows path — change it if running elsewhere.
- The FRED API key is hardcoded in `Collector/fredAPI.py`. Don't rotate it in committed code; if exposed, regenerate via the FRED portal.
- `Collector/World_Bank_API.py` pulls inflation / interest / FX — **not** gold reserves. Reserves come from `Reserves_Gold.xlsx` via `database.insert_excel()`.


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
