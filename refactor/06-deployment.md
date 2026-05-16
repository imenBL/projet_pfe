# Phase 6 — Deployment

> Status: TODO (optional API/dashboard)
> Maps to project_plan.md: PHASE 4 (Results & Reporting)

## Goal
Deliver the PFE report and (optionally) a working interface to serve predictions from the chosen model.

## Inputs (from Phase 5)
- Final model artifact + selection memo.
- Model-comparison table, predicted-vs-actual plots, SHAP plots.

## Tasks

### PFE report (required)
- [ ] **Methodology**: scope, data sources, feature engineering, split protocol, model lineup, evaluation protocol.
- [ ] **Results**: model-comparison table, predicted-vs-actual figures, SHAP-driven discussion of top features.
- [ ] **Conclusions**: what worked, what didn't, recommended next steps (e.g., extending to Stage 2).

### Serving (optional)
- [ ] REST API exposing `POST /predict` for a date or feature payload (FastAPI or Flask).
- [ ] Dashboard (Streamlit / Dash) showing historical actuals + future forecasts.

### Reproducibility
- [ ] Final `requirements.txt` (or `pyproject.toml`) checked in.
- [ ] README describing how to rebuild `ml.us_gold_features_daily` and re-train every model from scratch.

## Outputs
- Final PFE report (PDF + source).
- Optional: deployed API / dashboard with the final model.
- Reproducibility bundle (pinned deps + run instructions).

## Acceptance criteria
- [ ] PFE report covers methodology, results, conclusions.
- [ ] Anyone with database access + the repo can reproduce `ml.us_gold_features_daily` and re-train the final model.
- [ ] If a serving layer is built, it returns predictions consistent with the final model's test-set predictions for the same dates.

## Open questions
- Defense / submission deadline (drives whether the optional API gets built).
