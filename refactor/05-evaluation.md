# Phase 5 — Evaluation

> Status: **IN PROGRESS** — all implemented models (ARIMA, LinearRegression, DecisionTree, XGBoost, LightGBM, Prophet, LSTM) scored on one holdout with identical metrics in `06_comparison.ipynb`; best model named (LSTM, ≈ random walk). TFT scoring pending; SHAP carried over from the earlier `.py` iteration. See [`reports/phase3-modeling/SUMMARY.md`](../reports/phase3-modeling/SUMMARY.md).
> Maps to project_plan.md: PHASE 3 (Evaluation + Interpretability) + PHASE 4 (Model comparison table)

## Goal
Score every model on the same holdout test set, surface feature importance for the winning model, and select the final model with documented justification.

## Inputs (from Phase 4)
- Trained models and aligned test-set predictions for ARIMA/SARIMA, XGBoost/LightGBM, LSTM, TFT.

## Required metrics (every model, no exceptions)

| Metric | Definition                                       |
|--------|--------------------------------------------------|
| MAE    | Mean absolute error                              |
| RMSE   | Root mean squared error                          |
| MAPE   | Mean absolute percentage error                   |
| R²     | Coefficient of determination on the test set    |

`EVAL_METRICS = ["MAE", "RMSE", "MAPE", "R2"]`. All four must be reported for every model.

## Tasks
- [x] Compute MAE / RMSE / MAPE / R² for every model on the test set. — `models/utils.py:evaluate`; all 7 models + RandomWalk reference (+ skill-vs-RW & directional accuracy).
- [x] Build the model-comparison table (one row per model, columns = the metrics). — `06_comparison.ipynb` → `reports/phase3-modeling/comparison_table.{md,csv}`.
- [x] Plot predicted vs actual `gold_24k` over the test window. — inline per notebook + `best_model_pred_vs_actual.png`.
- [~] SHAP feature importance for the winning ML model. — produced in the earlier `.py` iteration (LightGBM: `dxy`, `y_ma_7`, `y_ma_30`, `fed_rate`, `y_lag_1`); not regenerated in the notebooks (nominal best is the LSTM, where TreeExplainer doesn't apply).
- [~] Pick a single final model and write a short justification. — **LSTM** by lowest test RMSE, but **statistically tied with the random walk** (see SUMMARY); final cross-lineup pick pending TFT.

## Outputs (for Phase 6)
- Model-comparison table (CSV or markdown).
- Predicted-vs-actual plot per model.
- SHAP summary plot for the final model.
- Final model artifact tagged as "production".
- Selection memo (≤ 1 page).

## Acceptance criteria (gate to Phase 6)
- [ ] All 4 metrics computed for every model.
- [ ] Comparison table checked in.
- [ ] SHAP plots exist for the final model.
- [ ] A single final model is named and justified.

## Open questions
- Tie-breaker rule if two models are within metric noise on the test set (prefer simpler? prefer better SHAP story?).
