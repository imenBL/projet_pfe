# Refactor — CRISP-DM phase docs

This folder splits the project into one Markdown file per CRISP-DM phase. Each file owns its phase end-to-end (goal, inputs, tasks, outputs, acceptance criteria), so future work can pick up a phase without re-deriving scope.

`project_plan.md` (repo root) remains the authoritative spec. These docs cite it and never contradict it — when in doubt, `project_plan.md` wins.

`CLAUDE.md` (repo root) is Claude's working playbook with hard constraints extracted from `project_plan.md`.

## CRISP-DM ↔ project_plan.md mapping

CRISP-DM order is **canonical and non-negotiable** for this project. Data Understanding (EDA) precedes Data Preparation. **No pragmatic shortcuts** — the feature-table build does not start until the EDA report and imputation strategy are produced. `project_plan.md` PHASE numbers were aligned to CRISP-DM order: EDA = PHASE 1, Data Prep = PHASE 2.

| CRISP-DM phase            | project_plan.md scope                                       | Status                       |
|---------------------------|--------------------------------------------------------------|------------------------------|
| 1. Business Understanding | "Project Description" + "Project Goals"                     | DONE                         |
| 2. Data Understanding     | Phase 0 (Data Infrastructure) + Phase 1 (EDA)               | Collection DONE, EDA **TODO — next up** |
| 3. Data Preparation       | Phase 2 (cleanup + build `ml.us_gold_features_daily`)       | **TODO — gated on EDA**      |
| 4. Modeling               | Phase 3 (ARIMA → XGBoost/LightGBM → LSTM → TFT)             | TODO                         |
| 5. Evaluation             | Phase 3 metrics + SHAP + Phase 4 model-comparison table     | TODO                         |
| 6. Deployment             | Phase 4 (PFE report + optional REST API / dashboard)        | TODO                         |

## Files in this folder

- [`01-business-understanding.md`](01-business-understanding.md)
- [`02-data-understanding.md`](02-data-understanding.md)
- [`03-data-preparation.md`](03-data-preparation.md)
- [`04-modeling.md`](04-modeling.md)
- [`05-evaluation.md`](05-evaluation.md)
- [`06-deployment.md`](06-deployment.md)

## Standard phase-doc template

Every `NN-<phase>.md` file in this folder follows:

```
# Phase N — <CRISP-DM phase name>

> Status: DONE | IN PROGRESS | TODO
> Maps to project_plan.md: <section reference>

## Goal
One line.

## Inputs (artifacts from the previous phase)

## Tasks
- [ ] Checklist item.

## Outputs (artifacts for the next phase)

## Acceptance criteria (gate to next phase)
- Concrete, checkable conditions.

## Open questions
```

## How to use

- Working on a specific phase? Open the matching `NN-<phase>.md` and treat its **Tasks** list as the source of truth for what to do next.
- **Acceptance criteria are the gate** — don't move to the next phase until every box is ticked.
- Edit the `Status:` header as work progresses (TODO → IN PROGRESS → DONE).
- These docs are checklists, not code. Implementation lives in `.py` files and notebooks; do not paste Python/SQL stubs in here.
