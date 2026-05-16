# Phase 1 — Business Understanding

> Status: DONE
> Maps to project_plan.md: "PROJECT DESCRIPTION" + "PROJECT GOALS"

## Goal
Predict daily USA gold 24K prices (in USD) by combining historical prices, macro indicators, market indicators, geopolitical signals, gold reserves, and engineered time-series features. Project type: Projet de Fin d'Études (PFE).

## Scope (hard constraints)

- **Country**: USA only.
- **Metal**: gold only.
- **Karat**: `gold_24k` only.
- **Currency**: USD.
- **Period**: 2017-01-01 → today.
- **Stage**: Stage 1 only. Stage 2 (other countries, prices-only) is **out of scope**.

## Exclusions

The following are explicitly excluded from the modeling pipeline:

- Other karats: `gold_22k`, `gold_21k`, `gold_18k`, `gold_14k`, `gold_10k`.
- `silver_price`.
- All countries other than USA. Other-country rows stay in source tables but are filtered out at feature-build time (Phase 3); do not delete them.

## Primary goal
Build a robust forecasting model for `gold_24k` daily prices for the United States, leveraging both historical price dynamics and the full exogenous feature set (macro + market + geopolitical + reserves).

## Secondary goals

1. Identify the most influential features driving gold prices (SHAP feature importance).
2. Compare multiple forecasting approaches: ARIMA/SARIMA → XGBoost/LightGBM → LSTM → Temporal Fusion Transformer.
3. Keep the pipeline reproducible, versioned, and extensible.

## Inputs
- None (this is the first phase).

## Tasks
- [x] Define scope (country, metal, karat, currency, period).
- [x] Define exclusions.
- [x] Identify data sources and grain (see Phase 2).
- [x] State primary and secondary goals.

## Outputs (for Phase 2)
- This document (scope contract every subsequent phase honors).
- `project_plan.md` (authoritative spec).
- `CLAUDE.md` (Claude's hard-constraint playbook).

## Acceptance criteria
- [x] Scope is unambiguous and written down.
- [x] Exclusions are explicit.
- [x] Success criteria for the final model are agreed in principle (Phase 5 will quantify them with MAE / RMSE / MAPE / R²).

## Open questions
- Quantitative success threshold for "production-quality" model (e.g., target MAPE) — deferred to Phase 5.
