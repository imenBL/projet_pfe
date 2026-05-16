# Phase 4 — Modeling

> Status: TODO
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

Each model gets its own notebook or script (e.g., `models/arima.py`, `models/xgboost.py`, …). For each model, persist:

- The trained model artifact (pickle / joblib / state dict).
- The full test-set prediction series, aligned to test-set dates, for Phase 5 evaluation.
- Training log: loss curves and hyperparameters used.

## Reproducibility
- Set a fixed random seed in every model script (numpy / torch / xgboost / lightgbm).
- Pin dependency versions when modeling work begins. The repo currently has no `requirements.txt` — adding it is part of this phase.

## Tasks
- [ ] Implement a chronological 70/15/15 split utility used by every model.
- [ ] ARIMA / SARIMA baseline trained, test-set predictions saved.
- [ ] XGBoost / LightGBM trained, test-set predictions saved.
- [ ] LSTM trained, test-set predictions saved.
- [ ] TFT trained, test-set predictions saved.
- [ ] Add `requirements.txt` (pinned versions) for the modeling stack.

## Outputs (for Phase 5)
- Trained model artifact per model family.
- Test-set prediction series per model.
- Training logs (loss curves, hyperparameters).

## Acceptance criteria (gate to Phase 5)
- [ ] All 4 model families trained and produced test-set predictions.
- [ ] Predictions aligned to the exact test-set dates (no leakage from train or validation).
- [ ] Random seeds pinned and documented.
- [ ] `requirements.txt` checked in.

## Open questions
- Forecast horizon: t+1 only, or multi-step (t+1, t+7, t+30)?
- Baseline: pure univariate ARIMA, or SARIMAX with exogenous regressors?
