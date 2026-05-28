
PROJECT DESCRIPTION
================================================================================

Title:
    Gold Price Prediction for the United States Using Machine Learning
    and Time Series Forecasting

Summary:
    This project is a final-year academic project (Projet de Fin d'Études — PFE)
    that aims to predict gold 24K prices for the United States by combining:

        - Historical gold 24K price data (USA, 2017–Today)
        - Macroeconomic indicators : Fed Rate, Real Rate, CPI, GDP, DXY,
          Unemployment (FRED API, monthly → forward-filled to daily)
        - Market indicators        : VIX (Volatility Index), Crude Oil Price
          (Yahoo Finance, daily)
        - Geopolitical signals     : Total Events, Political Events,
          War Intensity, Crisis Index, Political Pressure
          (GDELT, daily, filtered on USA)
        - Time-series features     : Lags, Moving Averages, Rolling Volatility
          (engineered from the gold price series itself)

    Scope:
        - Country   : United States (USA)
        - Metal     : Gold only
        - Karat     : 24K only (gold_24k) — all other karats excluded
        - Currency  : USD
        - Period    : 2017-01-01 → Today
        - Horizon   : T+30 (forecast ~one month / 30 trading days ahead).
                      The earlier T+1 framing collapsed to a random walk;
                      see PHASE 3 and the NOTES block below.
          
 Note : 
 Two prediction stages are defined: (Now we will Only Focus on Stage 1)
 - Stage 1 : USA, Gold 24K, full feature set (macro + geopolitical + market) 
 - Stage 2 : All other countries, Gold 24K, historical prices only

================================================================================
DATA SOURCES
================================================================================

    Source              Table                   Grain       Coverage
    ──────────────────────────────────────────────────────────────────────────
    Web Scrapers        raw_prices              Daily       12 countries (*)
    GDELT API           geopo_data              Daily       All countries (*)
    FRED API            macro_data              Monthly     USA only
    Yahoo Finance       vix_oil_data            Daily       USA only
    World Bank          reserves_gold           Annual      All countries (*)
    ──────────────────────────────────────────────────────────────────────────
    (*) Tables are centralized for all countries but filtered to USA
        during the feature dataset build step.

    Note:
        - Only gold_24k is retained as the target variable (y).
        - Columns gold_22k, gold_18k, gold_14k, gold_10k and silver_price
          are excluded from the modeling pipeline. (gold_21k was dropped
          at source; gold and silver now share the raw_prices table.)
        - gold_reserves (World Bank) is excluded from the Stage-1 feature set
          (flagged as a spurious co-trend feature in EDA). The reserves_gold
          source table is retained (other stages); it is simply not joined
          into the feature set.
        - dim_date was removed; calendar features are derived in pandas.

================================================================================
DATABASE SCHEMA — metals_db (PostgreSQL)
================================================================================

    [Source of Truth — Centralized Tables]

    public.raw_prices           → Daily gold (+ silver) prices per country
    public.geopo_data           → Daily geopolitical indicators per country
    public.macro_data           → Monthly macro indicators, USA only
    public.vix_oil_data         → Daily VIX + Crude Oil, USA only
    public.reserves_gold        → Annual gold reserves per country
    (dim_date removed — calendar features are derived in pandas at build time)

    [ML Feature Dataset — Schema: ml]

    ml.us_gold_features_daily   → Stage 1 ready-to-train dataset
                                  One row = one day (USA)
                                  Target column = y (gold_24k in USD)

================================================================================
FEATURE ENGINEERING — DEFINITIONS
================================================================================

    Notation:
        y_t = gold_24k price on day t (USD)

    ─── Lag Features ────────────────────────────────────────────────────────
        y_lag_1     = y(t-1)    → Yesterday's price
        y_lag_7     = y(t-7)    → Price 7 days ago  (weekly memory)
        y_lag_30    = y(t-30)   → Price 30 days ago (monthly memory)

        Purpose : Give the model explicit memory of past price levels.
                  Captures short-term momentum and medium-term trend direction.

    ─── Moving Average Features ─────────────────────────────────────────────
        y_ma_7      = mean(y[t-6  : t])    → 7-day rolling average
        y_ma_30     = mean(y[t-29 : t])    → 30-day rolling average

        Purpose : Smooth noise, expose local trend level.
                  (y_t - y_ma_30) = deviation from monthly trend.
                  (y_ma_7 > y_ma_30) = short-term bullish momentum signal.

    ─── Rolling Volatility ──────────────────────────────────────────────────
        y_vol_30    = std( ln(y_t/y_{t-1}) ) over last 30 days

        Purpose : Measure market turbulence over the past month.
                  High volatility → uncertain regime (crises, macro shocks).
                  Low  volatility → stable, more predictable period.

    ─── Exogenous Features ──────────────────────────────────────────────────
        Macro        : fed_rate, real_rate, cpi, gdp, dxy, unemployment
                       (monthly, forward-filled to daily)
        Market       : vix, oil_price
                       (daily)
        Geopolitical : total_events, political_events, war_intensity,
                       crisis_index, political_pressure
                       (daily, USA)
        (gold_reserves was dropped — see the Note under DATA SOURCES.)

    ─── Calendar Features ───────────────────────────────────────────────────
        month, quarter, day_of_week, is_month_end

================================================================================
PROJECT GOALS
================================================================================

    Primary Goal:
        Build a robust forecasting model to predict gold_24k daily prices
        for the United States, leveraging both historical price dynamics
        and a rich set of macroeconomic, market, and geopolitical features.

    Secondary Goals:
        1. Identify the most influential features driving gold prices
           (feature importance via SHAP values).
        2. Compare multiple forecasting approaches (ARIMA baseline,
           XGBoost/LightGBM, LSTM, Temporal Fusion Transformer).
        3. Ensure the full pipeline is reproducible, versioned, and
           extensible for future stages or additional features.

================================================================================
PROJECT PLAN — PHASES & MILESTONES
================================================================================

    CRISP-DM ORDERING (canonical, non-negotiable):
        Phase 0 → Phase 1 (EDA) → Phase 2 (Data Prep) → Phase 3 (Modeling)
                                                      → Phase 4 (Reporting)

    Phase 1 (EDA) MUST complete before Phase 2 (Data Preparation) begins.
    No pragmatic shortcuts. The EDA report (trend, correlation, stationarity,
    decomposition, geopolitical-spike analysis, imputation strategy) is an
    input to Phase 2 — not a parallel or follow-up task.

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  PHASE 0 — Data Infrastructure                                  [DONE] │
    │                                                                         │
    │  [x] Web scraping — gold prices (12 countries, 2017–today)             │
    │  [x] GDELT data collection (geopolitical signals)                       │
    │  [x] FRED API data collection (macro indicators, USA)                   │
    │  [x] Yahoo Finance (VIX + Oil)                                          │
    │  [x] World Bank (gold reserves)                                         │
    │  [x] PostgreSQL database setup (metals_db)                              │
    │  [x] Gold + silver cleaned + merged into raw_prices                     │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  PHASE 1 — Exploratory Data Analysis (EDA)                     [ DONE ]│
    │                                                                         │
    │  [x] Gold 24K price trend visualization (USA, 2017–today)               │
    │  [x] Correlation matrix : gold_24k vs all exogenous features            │
    │  [x] Stationarity tests : ADF / KPSS on gold_24k series                 │
    │  [x] Trend + seasonality decomposition (STL)                            │
    │  [x] Geopolitical event spikes vs gold price movements                  │
    │  [x] Missing values analysis and imputation strategy                    │
    │                                                                         │
    │  Gate: Phase 1 acceptance criteria (see refactor/02-data-               │
    │  understanding.md) must be met before Phase 2 starts.                   │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  PHASE 2 — Data Preparation & Feature Engineering        [ DONE ]      │
    │  ml.us_gold_features_daily built (2 448 x 27) and verified.             │
    │  Code: USA_cleaning.py + data_access.py.                                │
    │  Summary: reports/phase2-dataprep/SUMMARY.md.                           │
    │                                                                         │
    │  [x] Keep only gold_24k — dropped other karats and silver_price         │
    │  [~] country_code ISO3 — emitted 'USA' in table; sources not rewritten  │
    │  [~] Date types/renames — applied in-pandas at build; source ALTER def. │
    │  [x] Build ml.us_gold_features_daily :                                  │
    │        - Filter : country_code = 'USA' (gold_24k)                       │
    │        - Join   : macro_data (forward-fill monthly → daily)             │
    │        - Join   : vix_oil_data (daily)                                  │
    │        - Join   : geopo_data (country = 'USA', daily)                   │
    │        - Compute: y_lag_1, y_lag_7, y_lag_30                           │
    │        - Compute: y_ma_7, y_ma_30                                       │
    │        - Compute: y_vol_30 (rolling std of log-returns)                 │
    │        - Add   : calendar features (in pandas)                          │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  PHASE 3 — Modeling                                    [ IN PROGRESS ]│
    │                                                                         │
    │  [x] Chronological train / validation / test split (70 / 15 / 15 %)    │
    │  [x] Baseline         : ARIMA (univariate; AIC → (0,1,0))               │
    │  [x] ML models        : LinReg, Tree, XGBoost, LightGBM, Prophet        │
    │  [x] Deep Learning    : LSTM (PyTorch)                                  │
    │  [ ] Advanced DL      : Temporal Fusion Transformer (TFT) (deferred)     │
    │  [x] Evaluation       : MAE, RMSE, MAPE, R² (+ skill vs RW)            │
    │  [x] Interpretability : SHAP (earlier .py iteration)                    │
    │  [~] Best model selection (LSTM ≈ random walk)                          │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  PHASE 4 — Results & Reporting                                  [ TODO ]│
    │                                                                         │
    │  [ ] Model comparison table (metrics per model)                         │
    │  [ ] Visualization : predicted vs actual gold_24k prices                │
    │  [ ] SHAP plots : top features driving predictions                      │
    │  [ ] PFE report writing (methodology, results, conclusions)             │
    │  [ ] Optional : REST API / dashboard to serve predictions               │
    └─────────────────────────────────────────────────────────────────────────┘

================================================================================
NOTES — T+30 iteration (EDA re-iteration)
================================================================================

    Why T+30:
        Phase-3 modeling at T+1 found every model statistically tied to a random
        walk (ARIMA → (0,1,0); best skill vs RW ≈ +0.3 %, within noise). The EDA
        was re-iterated to re-frame the problem at T+30 (~one month) where slow
        macro/market/geo features have more room to carry signal. The exact target
        representation (price level y(t+30) vs cumulative log-return ln(y(t+30)/y(t)))
        is intentionally left open and locked at the modeling step.

    gold_reserves dropped — code alignment pending:
        gold_reserves is removed from the Stage-1 feature contract above. The EDA
        notebook and these specs/docs reflect that now. The persisted code still
        carries it and is aligned in the NEXT (main cleaning) step:
        USA_cleaning.py (RESERVE_FEATURE / clean_reserves / the join), models/utils.py
        (FEATURE_COLUMNS), and the built table ml.us_gold_features_daily (rebuild).

    models_medium/ (experimental, not part of the workflow):
        A models_medium/ directory exists (utils_h.py + models_h.py) implementing a
        T+30/T+60 study with a direct price-level target, random-walk-with-drift
        benchmark, Diebold-Mariano test and conformal intervals. It has no notebooks
        or report and is not wired into the CRISP-DM workflow. Left untouched here;
        review (and likely remove or rebuild) when the T+30 modeling step is reached.

================================================================================
PROJECT CONFIGURATION — Constants
================================================================================
"""

# ─── Scope ────────────────────────────────────────────────────────────────────
TARGET_METAL      = "gold"
TARGET_KARAT      = "gold_24k"         # Only column kept as target (y)
TARGET_CURRENCY   = "USD"
DATE_START        = "2017-01-01"
DATE_END          = "Current_date"               # Today (dynamic)

# ─── Country ──────────────────────────────────────────────────────────────────
COUNTRY           = "USA"

# ─── Forecast Horizon ─────────────────────────────────────────────────────────
FORECAST_HORIZON  = 30                 # Trading days ahead (T+30, ~one month).
                                       # Target representation (price level y(t+30)
                                       # vs cumulative log-return) is locked at the
                                       # modeling step — see the NOTES block above.

# ─── Feature Windows ─────────────────────────────────────────────────────────
LAG_WINDOWS       = [1, 7, 30]         # Days
MA_WINDOWS        = [7, 30]            # Days
VOL_WINDOW        = 30                 # Days (rolling std of log-returns)

# ─── Exogenous Features ───────────────────────────────────────────────────────
MACRO_FEATURES    = ["fed_rate", "real_rate", "cpi", "gdp", "dxy", "unemployment"]
MARKET_FEATURES   = ["vix", "oil_price"]
GEO_FEATURES      = ["total_events", "political_events", "war_intensity",
                      "crisis_index", "political_pressure"]
# gold_reserves dropped from the Stage-1 feature set (spurious co-trend in EDA).
ALL_EXOG_FEATURES = MACRO_FEATURES + MARKET_FEATURES + GEO_FEATURES

# ─── Calendar Features ────────────────────────────────────────────────────────
CALENDAR_FEATURES = ["month", "quarter", "day_of_week", "is_month_end"]

# ─── ML Dataset ───────────────────────────────────────────────────────────────
ML_SCHEMA         = "ml"
STAGE1_DATASET    = f"{ML_SCHEMA}.us_gold_features_daily"

# ─── Train / Validation / Test Split (chronological) ─────────────────────────
TRAIN_RATIO       = 0.70
VAL_RATIO         = 0.15
TEST_RATIO        = 0.15

# ─── Evaluation Metrics ───────────────────────────────────────────────────────
EVAL_METRICS      = ["MAE", "RMSE", "MAPE", "R2"]

# ─── Database ─────────────────────────────────────────────────────────────────
DB_NAME           = "metals_db"
DB_SCHEMA_SOURCE  = "public"           # Centralized source-of-truth tables
DB_SCHEMA_ML      = "ml"              # Feature datasets for modeling



RQ :  Propre et focalisé exclusivement sur l'Étape 1.
