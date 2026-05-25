# Phase 1 — EDA Summary (USA / gold 24K / USD / 2017 → today)

> **Status:** ✅ DONE — verdicts filled and verified against `notebooks/01_eda_phase1_copieeee.ipynb` live outputs.
> For visuals, run `notebooks/01_eda_phase1_copieeee.ipynb`.
> Maps to: `refactor/02-data-understanding.md`, `project_plan.md` PHASE 1.

## Scope

- Target: `gold_24k` for USA, filtered by `devise = 'USD'` from `raw_prices`.
- Period analyzed: **2017-01-02 → 2026-05-22** (2 448 trading days after dedup).
- Other karats (`gold_22k`, `gold_18k`, `gold_14k`, `gold_10k`) and `silver_price` excluded per `project_plan.md` (`gold_21k` was dropped at source).

## Trend (Task 1)

The `gold_24k` USA series follows a strong upward trajectory over the study period, multiplied by approximately **3.9×** (from **36.98 $/g** in Jan 2017 to **144.99 $/g** as of the last recorded price, 2026-05-22). Three successive regimes are clearly identifiable:

1. **2017–2019 — low consolidation phase** (~37–45 $/g): narrow range, gradual Fed rate hikes.
2. **2020–2022 — COVID shock + inflationary surge**: first upward breakout to 55–65 $/g, noticeably higher volatility.
3. **2022–2026 — bull super-cycle**: gold successively breaks 70, 90, then 130+ $/g, consistent with the international spot dynamics (all-time high late 2024).

**Key statistics (from notebook cell output):**

| Stat   | Value       |
|--------|-------------|
| Count  | 2 448 rows  |
| Mean   | 64.91 $/g   |
| Std    | 28.25 $/g   |
| Min    | 36.98 $/g   |
| 25%    | 43.13 $/g   |
| Median | 58.15 $/g   |
| 75%    | 65.46 $/g   |
| Max    | 173.62 $/g  |

**Outlier flagged:** the series maximum of **173.62 $/g** is implausible vs. the expected international spot (~90–95 $/g peak). Likely a one-off scraping error (decimal shift or unit mix). **Action for Phase 2:** add an upper-bound control or winsorization at the 99.5th percentile before building `ml.us_gold_features_daily`.

## Seasonality — STL decomposition (Task 4)

STL decomposition (period = 365 calendar days) reveals a **dominant trend** and a **modest seasonal component**:

| Component  | Std dev | Range                    | Approx. share of total variance |
|------------|---------|--------------------------|----------------------------------|
| `trend`    | 27.55   | 40.87 → 151.17 $/g       | ~95 %                            |
| `seasonal` | 3.45    | −13.39 → +22.20 $/g      | ~1.5 %                           |
| `residual` | 5.23    | (centred 0)              | ~3.4 %                           |

Seasonality exists but does not justify prioritising SARIMA over plain ARIMA on its own. **Recommendation:** use ARIMA(p,d,q) on log-returns as the baseline; test SARIMA(s=252 or s=365) only if ARIMA underperforms. The calendar features built in Phase 2 (`month`, `quarter`, `is_month_end`) will absorb whatever seasonality remains for tree-based and LSTM models.

> **Note:** STL was run with period = 365 (calendar days). A re-run with period = 252 (NYSE business days) may be informative after the trading-calendar convention is locked in Phase 2.

## Stationarity verdict (Task 3)

| Transform     | ADF stat | ADF p-value | ADF says         | KPSS stat | KPSS p-value | KPSS says        | Both agree stationary? |
|---------------|----------|-------------|------------------|-----------|--------------|------------------|------------------------|
| `level`       | +2.70    | 0.999       | non-stationary   | 6.12      | 0.010        | non-stationary   | ✅ No (consensus)      |
| `first_diff`  | −13.01   | 2.6e-24     | stationary       | 0.55      | 0.031        | non-stationary   | ❌ Disagree            |
| `log_returns` | −12.41   | 4.3e-23     | stationary       | 0.33      | 0.100        | stationary       | ✅ Yes (consensus)     |

**Interpretation:**
- **Level:** both tests agree the raw series is non-stationary (strong upward trend).
- **First difference:** ADF rejects the unit root but KPSS still rejects stationarity (p = 0.031) — classic sign of residual heteroscedasticity (absolute daily differences grow 3–4× over the period as price rises from ~37 to ~145 $/g).
- **Log-returns:** both tests agree on stationarity (ADF p ≈ 0; KPSS p = 0.100 > 0.05). The log transformation neutralises the exponential growth of absolute variance — canonical for multiplicative financial assets.

**Chosen modelling target for ARIMA family: `log_returns`.**

## Correlations (Task 2)

Computed on the warm-up-trimmed clean window (3 339 daily rows, 2017-04-01 → 2026-05-22), ranked by |Pearson r|:

| Rank | Feature              | Pearson r | Spearman ρ | Notes                                              |
|------|----------------------|-----------|------------|----------------------------------------------------|
| 1    | `gdp`                | +0.83     | +0.92      | Co-trend — likely spurious on returns              |
| 2    | `cpi`                | +0.81     | +0.94      | Co-trend — likely spurious on returns              |
| 3    | `gold_reserves`      | +0.78     | +0.93      | Co-trend — likely spurious on returns              |
| 4    | `dxy`                | +0.46     | +0.62      | Moderate; counter-intuitive sign (co-trend effect) |
| 5    | `fed_rate`           | +0.45     | +0.49      | Moderate; counter-intuitive sign (co-trend effect) |
| 6    | `real_rate`          | +0.44     | +0.49      | Moderate                                           |
| 7    | `total_events`       | −0.31     | −0.37      | Weak negative                                      |
| 8    | `political_events`   | −0.28     | −0.34      | Weak negative                                      |
| 9    | `oil_price`          | +0.22     | +0.38      | Non-linear (Spearman >> Pearson)                   |
| 10   | `political_pressure` | +0.19     | +0.18      | Very weak positive                                 |
| 11   | `crisis_index`       | −0.12     | −0.12      | Near zero                                          |
| 12   | `vix`                | +0.07     | +0.24      | Negligible linear / non-linear hidden              |
| 13   | `war_intensity`      | +0.03     | +0.03      | **Non-significant** (Pearson p = 0.14)             |
| 14   | `unemployment`       | −0.02     | +0.19      | **Non-significant** linearly (Pearson p = 0.32)    |

**Key observations:**
- The top-3 correlations (`gdp`, `cpi`, `gold_reserves`) reflect **co-trending**, not direct causality. Their predictive value on returns remains to be confirmed in Phase 3.
- `dxy`, `fed_rate`, `real_rate` are **positively** correlated with gold — counter-intuitive versus classical theory, but explained by the 2022–2026 period where Fed tightening and gold prices rose simultaneously.
- The Pearson vs. Spearman gap for `oil_price` (+0.22 vs +0.38), `vix` (+0.07 vs +0.24) and `unemployment` (−0.02 vs +0.19) signals **non-linear relationships** that tree-based models (XGBoost, LightGBM) will capture better than linear models.

**Statistically non-significant (Pearson p > 0.05):** `war_intensity` (p = 0.14) and `unemployment` (p = 0.32). Together with `vix`, these are the three predictors with |Pearson r| < 0.1. All are kept anyway because `project_plan.md` mandates `ALL_EXOG_FEATURES`; SHAP in Phase 3 is the final arbiter.

## Geopolitical signal (Task 5)

- Spike-day threshold: top 1% of `crisis_index` (≥ 0.975) or `war_intensity` (≥ 0.102)
- Spike-day count: **68 days** out of 3 339 clean-window days
- Mean 7-day forward return after a spike: **+0.55%** (median +0.63%)
- Baseline mean 7-day return (all days): **+0.29%** (median +0.31%, n = 3 332)
- Absolute difference: +0.26 pp (~90% relative uplift)
- Mann-Whitney U one-sided p-value: **p = 0.1525** (U = 121 508)

**Verdict:** The directional signal is consistent with gold’s safe-haven role, but **statistically non-significant** at the 5% threshold (p = 0.15, n = 68 spike days). The low power stems from the small spike count and high return variance — not necessarily from the absence of an effect. Geopolitical features are **retained** in the feature table; their predictive contribution will be arbitrated by SHAP in Phase 3. Tree-based models may capture conditional effects (e.g., spike in calm vs. stressed market regime) that the linear Mann-Whitney test cannot detect.

## Missing-value strategy (Task 6) — locked

| Source          | Native grain                       | Row count (notebook)       | Imputation rule (Phase 2)                                  |
|-----------------|------------------------------------|----------------------------|------------------------------------------------------------||
| `raw_prices`    | Daily (trading days only)          | 2 448 (2017-01-02→2026-05-22) | **Forward-fill** weekend / holiday gaps (max gap = 3 days) |
| `macro_data`    | Monthly (quarterly for `gdp`)      | 2 741 (2016-01-01→2026-05-15) | **Forward-fill** month/quarter → daily                    |
| `vix_oil_data`  | Daily (trading days only)          | 2 615 (2016-01-04→2026-05-25) | **Forward-fill** weekend / holiday gaps                    |
| `geopo_data`    | Daily (complete, 0% missing)       | 3 797 (2016-01-01→2026-05-24) | **No imputation needed** — GDELT coverage is fully dense  |
| `reserves_gold` | Annual                             | 15 rows (2010→2024)         | **Forward-fill** year → daily                              |

**Supporting numbers from EDA:**
- `gold_24k` max consecutive gap: **3 days** (weekend + US holiday) — safe for forward-fill.
- GDELT features: **0% missing** across all 5 columns over 9 years.
- Macro features (FRED): 97–99% missing on a daily calendar — expected given monthly/quarterly publication cadence.
- Market features (Yahoo): ~31% missing — expected (~252 trading days / 365 calendar days ≈ 69% coverage).
- `gold_reserves` (World Bank): 14% missing — one value per year forward-filled over 365 days.

These rules carry forward as the contract for Phase 2 feature-build.

## Confirmed predictors to carry into Phase 2

Per `project_plan.md`, all 14 `ALL_EXOG_FEATURES` carry forward regardless of EDA correlation strength:

- **Macro (FRED):** `fed_rate`, `real_rate`, `cpi`, `gdp`, `dxy`, `unemployment`
- **Market (Yahoo):** `vix`, `oil_price`
- **Geopolitical (GDELT, USA):** `total_events`, `political_events`, `war_intensity`, `crisis_index`, `political_pressure`
- **Reserves (World Bank, USA):** `gold_reserves`

Calendar features (`month`, `quarter`, `day_of_week`, `is_month_end`) are **derived in pandas from the `date` column** at feature-build time (Phase 2) — `dim_date` has been removed from the pipeline.

## Phase 2 hand-off — column-name and data-quality findings

Surfaced by EDA; fixes belong to Phase 2 per `refactor/03-data-preparation.md`:

1. **Table renames (resolved by refactor):** `cleaned_data` → `raw_prices`, `gdelt_data` → `geopo_data`, `Macroeconomic_data` → `macro_data` — now aligned in all docs.
2. `raw_prices.country` is currently a **French slug** (e.g. `etats-unis`). Standardise to ISO3 `country_code` (`etats-unis` → `USA`, `tunisie` → `TUN`, etc.).
3. `raw_prices.date` is **TIMESTAMP** in the live DB → target type is **DATE**; conversion in progress (Phase 2 task).
4. `raw_prices.gold_24k` had **no zero-valued rows** in the EDA window (dropped 0 rows). Maintain the non-zero sanity check at feature-build time as a defensive guard.
5. **`macro_data`:** mixed-case columns `"CPI"`, `"GDP"`, `"DXY"`, `"Unemployment"` — rename to lowercase at feature-build time. Also contained **duplicate rows** at EDA time (each FRED row appeared twice); deduplicate before feature-build. The notebook deduped in-memory by `drop_duplicates(subset='date')`.
6. `vix_oil_data` live columns: `"Date"` (quoted, capital D) → `date`; `oil` → `oil_price`. Live DB still uses TIMESTAMP → target DATE (conversion pending).
7. **`macro_data.gdp`** is **98.95% missing** on the daily calendar (3 392 / 3 428 days) — confirms FRED `GDP` series is **quarterly**, not monthly. Verify in `data_collection/fredAPI.py`.
8. **Calendar features:** `dim_date` has been removed. `day_of_week` and `is_month_end` are derived in pandas from the `date` column during Phase 2 feature-build.
9. **Open question — trading-day calendar:** NYSE business days (~252/year) vs. every calendar day forward-filled (365/year)? Affects row count and the semantics of `y_lag_1`. **Must be locked before computing lag/MA/vol features in Phase 2.**

> **Implementation status:** item 3 (TIMESTAMP → DATE conversion) is in progress for `raw_prices`, `macro_data`, and `vix_oil_data`. `reserves_gold` does not yet have a `date` column (Phase 2 addition). Item 2 (ISO3 standardisation) is a Phase 2 task. These are documented as pending — not yet fully applied to the DB or code.

---

_Phase 1 EDA is complete. To close Phase 1 formally:_
_1. Tick the 3 acceptance-criteria boxes in `refactor/02-data-understanding.md` and flip its Status to **DONE**._
_2. Phase 2 (`refactor/03-data-preparation.md`) is then unblocked — starting with the data-quality items listed above._
