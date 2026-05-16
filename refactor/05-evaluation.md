# Phase 5 — Evaluation

> Status: TODO
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
- [ ] Compute MAE / RMSE / MAPE / R² for every model on the test set.
- [ ] Build the model-comparison table (one row per model, columns = the 4 metrics).
- [ ] For each model, plot predicted vs actual `gold_24k` over the test window.
- [ ] Compute SHAP feature importance for the winning ML/DL model. SHAP is required for at least the best XGBoost/LightGBM model, and (if feasible) for TFT.
- [ ] Pick a single final model and write a short justification (~1 paragraph: why this one over the runners-up).

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
