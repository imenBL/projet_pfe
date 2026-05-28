# Phase 4 — Modeling

> Status: **IN PROGRESS** — delivered as academic notebooks in `models/`: ARIMA, LinearRegression, DecisionTree, XGBoost, LightGBM, Prophet and an LSTM (PyTorch) are trained, evaluated and compared. **TFT still deferred.** See [`reports/phase3-modeling/SUMMARY.md`](../reports/phase3-modeling/SUMMARY.md).
> Maps to project_plan.md: PHASE 3 (Modeling)

## Goal
Train and compare forecasting models on `ml.us_gold_features_daily`, in order of complexity, and produce test-set predictions for every model so Phase 5 can score them on the same holdout.

## Inputs (from Phase 3)
- `ml.us_gold_features_daily` meeting all Phase 3 acceptance criteria.

## Split protocol (non-negotiable)

- **Chronological 70 / 15 / 15** (train / validation / test).
- **Never shuffle.** Never use `train_test_split(..., shuffle=True)` or any random/k-fold cross-validation that crosses the time boundary.
- Cut points are computed once from the sorted date column and reused by every model.
- Constants: `TRAIN_RATIO = 0.70`, `VAL_RATIO = 0.15`, `TEST_RATIO = 0.15`.

## Model lineup (run in this order)

1. **Baseline — ARIMA / SARIMA** (univariate on `y` only).
2. **ML — XGBoost / LightGBM** (full feature set).
3. **Deep learning — LSTM**.
4. **Advanced DL — Temporal Fusion Transformer (TFT)**.

Each model is its own notebook in `models/` (`02_arima.ipynb`, `03_simple_model.ipynb`, `04_modele_d_ensemble.ipynb`, `05_LSTM.ipynb`), all sharing `models/utils.py` (one load + split + metrics). For each model, persist:

- The aligned test-set prediction series → `models/predictions/<name>.csv` (date, y_t, actual, pred).
- Metrics + plots rendered inline; the cross-model comparison + best-model plot in `06_comparison.ipynb`.

## Reproducibility
- Fixed `SEED = 42` (numpy / torch / xgboost / lightgbm); ARIMA is deterministic.
- Dependency versions pinned in `requirements.txt` (incl. `torch 2.12.0`, `prophet 1.3.0`).

## Tasks
- [x] Chronological 70/15/15 split utility used by every model. — `models/utils.py:chrono_split`.
- [x] ARIMA baseline trained, test-set predictions saved. — univariate, AIC-selected (0,1,0); walk-forward 1-step (`02_arima.ipynb`).
- [x] Simple ML — LinearRegression + DecisionTree (GridSearchCV + TimeSeriesSplit) (`03_simple_model.ipynb`).
- [x] XGBoost / LightGBM trained, test-set predictions saved (RandomizedSearch + TimeSeriesSplit) (`04_modele_d_ensemble.ipynb`).
- [x] Prophet trained, 1-step walk-forward predictions saved (`04_modele_d_ensemble.ipynb`).
- [x] LSTM trained, test-set predictions saved. — PyTorch, univariate on returns (`05_LSTM.ipynb`).
- [ ] TFT trained, test-set predictions saved. — **deferred**.
- [x] Add `requirements.txt` (pinned versions) for the modeling stack. — incl. torch, prophet, sklearn/xgboost/lightgbm.

## Outputs (for Phase 5)
- Trained model artifact per model family.
- Test-set prediction series per model.
- Training logs (loss curves, hyperparameters).

## Acceptance criteria (gate to Phase 5)
- [~] All model families trained and produced test-set predictions. — ARIMA, LinReg, DecisionTree, XGBoost, LightGBM, Prophet, LSTM done; **TFT deferred**.
- [x] Predictions aligned to the exact test-set dates (no leakage). — all `models/predictions/*.csv` share the 363 test dates (2024-12-31 → 2026-05-21); t+1 return target; split disjoint.
- [x] Random seeds pinned and documented. — `SEED = 42` (numpy/torch/xgboost/lightgbm); ARIMA deterministic.
- [x] `requirements.txt` checked in. — pinned (torch, prophet, sklearn/xgboost/lightgbm, …).

## Decisions locked (Phase 3)
- **Delivery:** academic notebooks in `models/` + shared `models/utils.py` (replaced the earlier `.py` modeling package).
- **Forecast horizon:** pivoting **t+1 → T+30** (~one month). The t+1 run above stands as the **baseline that motivated the pivot** (every model tied to a random walk). The T+30 target representation (price level `y(t+30)` vs cumulative log-return) is **not yet locked** — decided when this step is re-run.
- **Baseline:** pure **univariate ARIMA** (SARIMAX-with-exog out of scope per the "univariate baseline" rule).
- **TFT** deferred (Python 3.14 + Windows DL-install risk). SHAP was produced in the earlier `.py` iteration; not part of the current notebook set (the nominal best model is the LSTM, where TreeExplainer does not apply).

## Pending at this phase (T+30 re-run — next step)
- **Align `models/utils.py`** to T+30 (target + horizon) and drop `gold_reserves` from `FEATURE_COLUMNS`; rebuild `ml.us_gold_features_daily` without `gold_reserves`.
- **Lock the T+30 target representation** (level vs cumulative return) and the change/surprise feature set.
- **Review `models_medium/`** (experimental T+30/T+60: level target, RW-with-drift, Diebold-Mariano, conformal intervals) — adopt, rebuild, or remove.

## Open questions
- ~~Forecast horizon: t+1 only, or multi-step?~~ **Reopened:** pivoting to **T+30**; t+1 retained only as the random-walk baseline.
- ~~Baseline: univariate ARIMA, or SARIMAX with exogenous regressors?~~ **Resolved:** univariate ARIMA.
