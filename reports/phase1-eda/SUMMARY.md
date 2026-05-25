# Phase 1 — EDA Summary (USA / gold 24K / USD / 2017 → today)

> **Status:** Template — verdicts to be filled in by the user after running `notebooks/01_eda_phase1.ipynb`.
> For visuals, run `notebooks/01_eda_phase1.ipynb`.
> Maps to: `refactor/02-data-understanding.md`, `project_plan.md` PHASE 1.

## Scope

- Target: `gold_24k` for USA, in USD per gram.
- Period analyzed: **2017-01-01 → today**.
- Other karats (`gold_22k`, `gold_21k`, `gold_18k`, `gold_14k`, `gold_10k`) and `silver_price` excluded per `project_plan.md`.

## Trend (Task 1)

_Fill after running notebook §1._ Describe the overall direction (e.g., upward with three regime shifts: 2020 COVID, 2022 inflation, 2024 election), the start/end price levels, the largest drawdown, and any outliers worth flagging.

## Seasonality — STL decomposition (Task 4)

_Fill after running notebook §4._ State the relative magnitudes of trend / seasonal / residual standard deviations. Indicate whether SARIMA's seasonal term is justified or if plain ARIMA (or ARIMA on log-returns) is sufficient.

## Stationarity verdict (Task 3)

_Fill after running notebook §3 with the ADF / KPSS results._

| Transform     | ADF says | KPSS says | Both agree stationary? |
|---------------|----------|-----------|------------------------|
| level         | ?        | ?         | ?                      |
| first_diff    | ?        | ?         | ?                      |
| log_returns   | ?        | ?         | ?                      |

**Chosen modeling target for ARIMA family:** _(typically `log_returns`)_.

## Correlations (Task 2)

_Fill after running notebook §2 with the ranked Pearson/Spearman table._

| Rank | Feature       | Pearson r | Spearman ρ | Notes                |
|------|---------------|-----------|------------|----------------------|
| 1    | _e.g._ `dxy`  | ?         | ?          | Strongly negative    |
| 2    | ?             | ?         | ?          |                      |
| 3    | ?             | ?         | ?          |                      |
| ...  | ...           | ...       | ...        |                      |

**Predictors with |ρ| < 0.1:** _(list — kept anyway because `project_plan.md` mandates `ALL_EXOG_FEATURES`)._

## Geopolitical signal (Task 5)

_Fill after running notebook §5._

- Spike-day count (top 1% of `crisis_index` or `war_intensity`): **?**
- Mean 7-day forward return after a spike: **?%**
- Baseline mean 7-day return: **?%**
- Mann-Whitney U one-sided p-value: **?** (rejects baseline ≥ post-spike if p < 0.05)
- **Verdict:** _(do USA geopolitical spikes co-move with gold-price moves?)_

## Missing-value strategy (Task 6) — locked

| Source                 | Native grain | Imputation rule (Phase 2)                                  |
|------------------------|--------------|-------------------------------------------------------------|
| `cleaned_prices`       | Daily (gaps) | **Forward-fill** weekend / holiday gaps                     |
| `macroeconomic_data`   | Monthly      | **Forward-fill** month → daily                              |
| `vix_oil_data`         | Daily (gaps) | **Forward-fill** weekend / holiday gaps                     |
| `geopolitical_data`    | Daily        | Dense for USA; ffill any sporadic gaps if found             |
| `reserves_gold`        | Annual       | **Forward-fill** year → daily                               |

These rules carry forward as the contract for Phase 2 feature-build.

## Confirmed predictors to carry into Phase 2

Per `project_plan.md`, all 14 `ALL_EXOG_FEATURES` carry forward regardless of EDA correlation strength:

- **Macro (FRED):** `fed_rate`, `real_rate`, `cpi`, `gdp`, `dxy`, `unemployment`
- **Market (Yahoo):** `vix`, `oil_price`
- **Geopolitical (GDELT, USA):** `total_events`, `political_events`, `war_intensity`, `crisis_index`, `political_pressure`
- **Reserves (World Bank, USA):** `gold_reserves`

Plus calendar features from `dim_date`: `month`, `quarter`, `day_of_week`, `is_month_end` (last two derived in Phase 2 since they aren't in the table).

## Phase 2 hand-off — column-name and data-quality findings

Surfaced by EDA, fixes belong to Phase 2 per `refactor/03-data-preparation.md`:

1. `cleaned_prices` is actually **`cleaned_data`** in the live DB (insert-function name mismatch noted in CLAUDE.md "Known pitfalls").
2. `cleaned_data.country` is actually **`"Pays"`** (French slug, mixed case requires quoting). Standardize to ISO3 `country_code` (`etats-unis` → `USA`, `tunisie` → `TUN`, etc.).
3. `cleaned_data."Année"` (accented) — normalize.
4. `cleaned_data.date` is **TEXT** → convert to `DATE`.
5. `cleaned_data.devise` is **NULL for `etats-unis`** — non-blocker for Stage 1 (USA-only) but worth flagging.
6. `cleaned_data.gold_24k` contains some **0-valued rows** that were filtered out in EDA; Phase 2 should add a non-zero / sanity-bound constraint at feature-build time.
7. `geopolitical_data` is actually **`gdelt_data`** in the live DB.
8. `"Macroeconomic_data"` (quoted, mixed-case columns `"CPI"`, `"GDP"`, `"DXY"`, `"Unemployment"`) — rename table and columns to match the DDL convention in `database.py`.
9. `vix_oil_data."Date"` (quoted, capital D) → `date`. Column `oil` → `oil_price`.
10. `dim_date` lacks `day_of_week` and `is_month_end` — derive in feature-build, not at the table level.
11. **Open question — trading-day calendar:** NYSE business days, or every calendar day forward-filled? Affects row count and the meaning of `y_lag_1`. Lock this **before** computing lag/MA/vol features in Phase 2.

---

_When all the "Fill after running notebook" sections above are completed, tick the 3 acceptance-criteria boxes in `refactor/02-data-understanding.md` and flip its Status header to **DONE**. Phase 2 (`refactor/03-data-preparation.md`) is then unblocked._
