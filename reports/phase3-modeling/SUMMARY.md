# Phase 3 — Modeling Summary (USA / gold 24K / 1-step-ahead)

> **Status:** 🔧 IN PROGRESS — delivered as academic notebooks in `models/`. ARIMA, simple ML
> (LinearRegression, DecisionTree), ensemble/advanced (XGBoost, LightGBM, Prophet) and an
> LSTM are all trained, evaluated, and compared. **TFT still deferred.**
> Maps to: `refactor/04-modeling.md` + `refactor/05-evaluation.md`, `project_plan.md` PHASE 3.
> Verified 2026-05-28.

## Deliverables

Six notebooks in `models/` (run top to bottom) + one shared helper `models/utils.py`:

| Notebook | Content |
|----------|---------|
| `01_preprocessing.ipynb` | Series viz, STL decomposition, **ADF** (level/log/returns), log+differencing, ACF/PACF → conclusion `d = 1`. |
| `02_arima.ipynb` | Univariate ARIMA, **(p,d,q) by AIC**, walk-forward 1-step forecast. |
| `03_simple_model.ipynb` | LinearRegression + DecisionTree, tuned with **GridSearchCV + TimeSeriesSplit**. |
| `04_modele_d_ensemble.ipynb` | XGBoost + LightGBM (RandomizedSearch + TimeSeriesSplit) + **Prophet** (1-step walk-forward). |
| `05_LSTM.ipynb` | PyTorch LSTM on past returns (sequence prep, early stopping). |
| `06_comparison.ipynb` | Aggregates all predictions → comparison table + best-model plot. |

`utils.py` guarantees every notebook uses the **same** data, split, target and metrics.
Each model writes aligned test predictions to `models/predictions/<name>.csv`.

## Method (locked, identical across models)

- **Target:** next-day log-return `ret_next = ln(y_{t+1}/y_t)` → reconstruct price
  `ŷ = y_t·e^{r̂}`; ARIMA/Prophet model the level natively. **Metrics on the $/g price scale.**
- **Split:** chronological **70/15/15** (1 691 / 363 / 363). Test = **2024-12-31 → 2026-05-21**
  (the 2024–26 bull run). Leakage-safe; never shuffled.
- **Reproducibility:** `SEED = 42`. Deps pinned (`torch 2.12.0`, `prophet 1.3.0`, sklearn/xgb/lgbm).

## Results (test set, price scale)

| model | MAE | RMSE | MAPE % | R² | skill vs RW | dir. acc. |
|-------|-----|------|--------|-----|-------------|-----------|
| **LSTM** | **1.3498** | **2.1047** | 1.0426 | 0.9923 | **+0.003** | 0.576 |
| ARIMA (0,1,0) | 1.3554 | 2.1075 | 1.0472 | 0.9923 | 0.000 | 0.364 |
| RandomWalk (ref) | 1.3554 | 2.1075 | 1.0472 | 0.9923 | 0.000 | — |
| DecisionTree | 1.3540 | 2.1089 | 1.0455 | 0.9923 | −0.001 | 0.568 |
| LightGBM | 1.4872 | 2.1848 | 1.1478 | 0.9917 | −0.075 | 0.435 |
| LinearRegression | 1.7158 | 2.4051 | 1.2944 | 0.9900 | −0.302 | 0.457 |
| XGBoost | 1.7727 | 2.4528 | 1.3691 | 0.9896 | −0.355 | 0.435 |
| Prophet | 4.0509 | 5.9487 | 3.0677 | 0.9387 | −6.967 | 0.466 |

## Interpretation

- **Nothing robustly beats the random walk at h = 1.** ARIMA again collapses to **(0,1,0)** (= RW).
  The LSTM is *nominally* best but its skill over RW is **+0.3 %** — inside the noise band.
- **`skill_vs_RW` is the honest metric.** Price-scale R² ≈ 0.99 for everyone is an artifact of
  the trend (today ≈ tomorrow); it does not measure forecasting skill.
- **The tuned trees and linear model do *worse* than RW** (negative skill): with no real daily
  signal, time-series CV picks configurations that fit noise. (Note: this differs from a
  heavily-shrunk/early-stopped tree, which would simply collapse to ≈ RW.)
- **Prophet is far worse** (−6.97 skill): even 1-step, its trend+seasonality fit injects bias on
  a near-efficient daily series — Prophet is built for longer horizons.
- **Directional accuracy** above 0.5 (LSTM 0.58, DecisionTree 0.57) largely reflects the
  bull-market drift, not genuine timing skill.

## Best model (this iteration)

**LSTM**, by lowest test RMSE — stated with the explicit caveat that it is **statistically tied
with the random walk**. ARIMA(0,1,0) remains the honest baseline. The real lesson for the
interpretation phase: at a 1-day horizon on an efficient market, model *family* matters far less
than **problem framing** (horizon, feature frequency).

## Artifacts
- `models/predictions/*.csv` (date, y_t, actual, pred — 363 aligned test rows each).
- `reports/phase3-modeling/comparison_table.{md,csv}`, `best_model_pred_vs_actual.png`.

## Deferred / next
- **TFT** (still deferred). **Multivariate LSTM** (feed all 24 features) is the natural extension.
- Longer horizons (t+5 / t+21) where low-frequency macro/geo features can contribute.
- The **interpretation write-up** is done: `interpretation/03_modeling.md` (French) — an expert,
  section-by-section read of every notebook, why each model behaves as it does, and a
  **model-selection guide keyed to the series' behaviour**.
