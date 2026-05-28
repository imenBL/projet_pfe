"""Shared helpers for the medium-horizon (T+30 / T+60) gold-forecasting study.

Forecast framing (locked for this study):
- Predict the **price level** ``y_{t+h}`` directly, **direct multi-step** (one model per
  horizon ``h`` in :data:`HORIZONS`). This is the deliverable the user asked to report on.
- Benchmark = **random walk WITH drift** (a no-change RW is far too weak on a trending
  series). Because a level target inflates R^2, the **headline metric is skill vs the drift
  benchmark + a Diebold-Mariano significance test**, never R^2 alone.
- Guardrails for the level target: a tree-extrapolation diagnostic (trees cannot predict
  above their training max) and change/momentum features so tree splits stay in-range.

This module mirrors ``models/utils.py`` (the t+1 baseline) but is intentionally separate:
the target, benchmark and metrics have different semantics (level @ h vs next-day return).
It reuses the leak-fixed feature table via ``data_access`` and the canonical feature-name
constants from ``USA_cleaning``.
"""

import os
import sys

import numpy as np
import pandas as pd

# Make repo-root modules (data_access, USA_cleaning) importable regardless of CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import data_access  # noqa: E402
from USA_cleaning import (  # noqa: E402
    ENGINEERED_FEATURES, MACRO_FEATURES, MARKET_FEATURES,
    GEO_FEATURES, RESERVE_FEATURE, CALENDAR_FEATURES,
)

SEED = 42
HORIZONS = [30, 60]               # trading days ahead (T+30, T+60)
TRAIN_RATIO, VAL_RATIO = 0.70, 0.15
PREDICTIONS_DIR = os.path.join(_REPO_ROOT, "models_medium", "predictions")
REPORTS_DIR = os.path.join(_REPO_ROOT, "reports", "phase4-medium-horizon")

# --------------------------------------------------------------------------------------
# Feature engineering — medium-horizon change / momentum / surprise features
# All are backward-looking (shift/rolling ending at t), computed on the trading-day grid,
# so a row at t uses only information available at the close of t. The base 24 features
# are the project_plan contract; the extended ones de-trend the slow level features
# (kills the co-trend spurious-correlation trap flagged in EDA) and add horizon-scale
# momentum that a daily t+1 target could not exploit.
# --------------------------------------------------------------------------------------

MOMENTUM_WINDOWS = [30, 60, 90]
_MACRO_DIFF = ["real_rate", "fed_rate", "cpi", "dxy", "unemployment"]  # 21d difference (rate/level safe)
_MACRO_YOY = ["cpi", "gdp"]                                           # 252d ratio (inflation, growth)

BASE_FEATURES = (
    ENGINEERED_FEATURES + MACRO_FEATURES + MARKET_FEATURES
    + GEO_FEATURES + RESERVE_FEATURE + CALENDAR_FEATURES
)
EXTENDED_FEATURES = (
    [f"roc_{w}" for w in MOMENTUM_WINDOWS]
    + ["y_ma_60", "y_vol_60", "dist_ma_30", "dist_ma_60"]
    + [f"d21_{m}" for m in _MACRO_DIFF]
    + [f"yoy_{m}" for m in _MACRO_YOY]
)
FEATURE_COLUMNS = BASE_FEATURES + EXTENDED_FEATURES


def build_feature_frame(refresh=False):
    """Load the leak-fixed feature table and append medium-horizon engineered features.

    Returns a frame sorted by date with ``y`` (price level) plus :data:`FEATURE_COLUMNS`.
    Leading rows carry NaNs in the longest-window features (up to ~252 rows for YoY); the
    target builders drop them.
    """
    df = data_access.load_features(refresh=refresh).copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    y = df["y"]

    # price momentum (rate-of-change over the horizon scale)
    for w in MOMENTUM_WINDOWS:
        df[f"roc_{w}"] = y / y.shift(w) - 1.0
    # horizon-scale level & volatility
    df["y_ma_60"] = y.rolling(60).mean()
    df["y_vol_60"] = np.log(y / y.shift(1)).rolling(60).std()
    # distance of price from its moving average (mean-reversion / trend-stretch signal)
    df["dist_ma_30"] = y / df["y_ma_30"] - 1.0
    df["dist_ma_60"] = y / df["y_ma_60"] - 1.0
    # macro changes (1 trading-month difference) — stationary 'surprise' proxies
    for m in _MACRO_DIFF:
        df[f"d21_{m}"] = df[m] - df[m].shift(21)
    # macro YoY (252 trading days) for strictly-positive trending levels
    for m in _MACRO_YOY:
        df[f"yoy_{m}"] = df[m] / df[m].shift(252) - 1.0
    return df


# --------------------------------------------------------------------------------------
# Direct multi-step target + chronological split
# --------------------------------------------------------------------------------------

def make_target(df, h):
    """Append the direct-h price-level target ``y_h{h} = y(t+h)``."""
    out = df.copy()
    out[f"y_h{h}"] = out["y"].shift(-h)
    return out


def prepare_xy(df, h, features=FEATURE_COLUMNS):
    """Frame ready for modeling at horizon h: drops feature warm-up and the final h rows."""
    d = make_target(df, h)
    return d.dropna(subset=list(features) + [f"y_h{h}"]).reset_index(drop=True)


def chrono_split(df):
    """Chronological 70/15/15 split by position (never shuffled). Same policy as the baseline."""
    n = len(df)
    i = int(n * TRAIN_RATIO)
    j = int(n * (TRAIN_RATIO + VAL_RATIO))
    return df.iloc[:i].copy(), df.iloc[i:j].copy(), df.iloc[j:].copy()


# --------------------------------------------------------------------------------------
# Benchmarks (the bar every model must clear)
# --------------------------------------------------------------------------------------

def estimate_drift(y_hist):
    """Mean daily log-return over a history window (the drift of a geometric random walk)."""
    return float(np.mean(np.diff(np.log(np.asarray(y_hist, dtype=float)))))


def rw_drift_pred(y_t, drift, h):
    """Geometric random-walk-WITH-drift forecast: ``y_t * exp(h * drift)``."""
    return np.asarray(y_t, dtype=float) * np.exp(h * float(drift))


def rw_flat_pred(y_t):
    """Naive no-change random walk: ``y_{t+h} = y_t`` (weak reference on a trend)."""
    return np.asarray(y_t, dtype=float)


# --------------------------------------------------------------------------------------
# Metrics (on the $/g price scale) + significance
# --------------------------------------------------------------------------------------

def evaluate(y_true, y_pred):
    """{MAE, RMSE, MAPE %, sMAPE %, R2} on the price scale. R2 is reported but caveated."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    ss_tot = float(np.sum((y_true - y_true.mean()) ** 2))
    denom_smape = np.abs(y_true) + np.abs(y_pred)
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(np.abs(err / y_true)) * 100.0),
        "sMAPE": float(np.mean(2.0 * np.abs(err) / np.where(denom_smape == 0, np.nan, denom_smape)) * 100.0),
        "R2": (1.0 - float(np.sum(err ** 2)) / ss_tot) if ss_tot > 0 else float("nan"),
    }


def directional_accuracy_h(y_t, y_true_h, y_pred_h):
    """Share of origins where the predicted h-day move sign matches the actual move sign."""
    y_t = np.asarray(y_t, dtype=float)
    return float(np.mean(np.sign(np.asarray(y_pred_h) - y_t) == np.sign(np.asarray(y_true_h) - y_t)))


def skill_vs(bench_pred, model_pred, y_true):
    """MSE skill score vs a benchmark: ``1 - MSE_model / MSE_bench`` (>0 = beats benchmark)."""
    y_true = np.asarray(y_true, dtype=float)
    mse_m = np.mean((np.asarray(model_pred) - y_true) ** 2)
    mse_b = np.mean((np.asarray(bench_pred) - y_true) ** 2)
    return float(1.0 - mse_m / mse_b) if mse_b > 0 else float("nan")


def diebold_mariano(y_true, pred_model, pred_bench, h, loss="squared"):
    """Diebold-Mariano test of equal predictive accuracy (model vs benchmark).

    Uses a Newey-West (Bartlett) HAC variance truncated at ``h-1`` lags — the correct
    correction for h-step-ahead, serially-correlated forecast errors — plus the
    Harvey-Leybourne-Newbold small-sample adjustment. Returns ``(dm_stat, p_value)``.
    A **negative** DM stat with small p means the model's loss is significantly *lower*
    (better) than the benchmark's.
    """
    from scipy import stats

    y_true = np.asarray(y_true, dtype=float)
    e_m = np.asarray(pred_model, dtype=float) - y_true
    e_b = np.asarray(pred_bench, dtype=float) - y_true
    if loss == "absolute":
        d = np.abs(e_m) - np.abs(e_b)
    else:
        d = e_m ** 2 - e_b ** 2
    n = len(d)
    d_bar = float(np.mean(d))
    # long-run variance with Bartlett weights up to h-1
    gamma0 = float(np.mean((d - d_bar) ** 2))
    lrv = gamma0
    for k in range(1, h):
        if k >= n:
            break
        cov = float(np.mean((d[k:] - d_bar) * (d[:-k] - d_bar)))
        lrv += 2.0 * (1.0 - k / h) * cov
    if lrv <= 0:
        return float("nan"), float("nan")
    dm = d_bar / np.sqrt(lrv / n)
    hln = np.sqrt(max((n + 1 - 2 * h + h * (h - 1) / n) / n, 1e-12))  # HLN correction
    dm_hln = dm * hln
    p = 2.0 * (1.0 - stats.t.cdf(abs(dm_hln), df=n - 1))
    return float(dm_hln), float(p)


# --------------------------------------------------------------------------------------
# Purged / embargoed walk-forward backtest (overlapping h-step targets need an embargo)
# --------------------------------------------------------------------------------------

def purged_walk_forward(n, h, n_splits=5, min_train_frac=0.4):
    """Expanding-window folds with an ``h``-day embargo between train and test.

    Yields ``(train_idx, test_idx)`` arrays. The tail of the sample after ``min_train_frac``
    is cut into ``n_splits`` contiguous test blocks; for each block the training set excludes
    the final ``h`` rows before the block (purge), so a training row's (t, t+h) target never
    overlaps the test block. This is the time-series analogue of purged CV.
    """
    start = int(n * min_train_frac)
    if start >= n:
        return
    block = (n - start) // n_splits
    if block <= 0:
        return
    for i in range(n_splits):
        test_lo = start + i * block
        test_hi = n if i == n_splits - 1 else start + (i + 1) * block
        train_hi = max(test_lo - h, 1)          # embargo of h rows
        yield np.arange(0, train_hi), np.arange(test_lo, test_hi)


# --------------------------------------------------------------------------------------
# Split-conformal prediction intervals (calibrated on a held-out block)
# --------------------------------------------------------------------------------------

def conformal_halfwidth(cal_residuals, alpha=0.1):
    """Symmetric split-conformal half-width: the (1-alpha) quantile of |calibration residuals|.

    Calibration residuals must come from a block disjoint from (and before) the test set,
    with the natural h-gap of the chronological split acting as the embargo. PI = pred ± hw.
    """
    r = np.abs(np.asarray(cal_residuals, dtype=float))
    r = r[np.isfinite(r)]
    if r.size == 0:
        return float("nan")
    # finite-sample conformal quantile level
    q = min(1.0, np.ceil((r.size + 1) * (1 - alpha)) / r.size)
    return float(np.quantile(r, q))


def conformal_relative_halfwidths(cal_resid, cal_y_t, test_y_t, alpha=0.1):
    """Scale-aware split-conformal half-widths (per test point).

    Gold is strongly trending/heteroskedastic, so an absolute residual quantile calibrated
    on an earlier (lower-price) block under-covers. We instead take the (1-alpha) quantile of
    **relative** residuals ``|resid| / y_t`` on the calibration block and rescale by each test
    origin's ``y_t`` — giving wider intervals when the price (and absolute risk) is higher.
    Returns an array of half-widths aligned to ``test_y_t``.
    """
    r = np.abs(np.asarray(cal_resid, dtype=float)) / np.asarray(cal_y_t, dtype=float)
    r = r[np.isfinite(r)]
    if r.size == 0:
        return np.full(len(np.atleast_1d(test_y_t)), np.nan)
    q = min(1.0, np.ceil((r.size + 1) * (1 - alpha)) / r.size)
    rel = float(np.quantile(r, q))
    return rel * np.asarray(test_y_t, dtype=float)


def conformal_relative_bounds(cal_resid_signed, cal_y_t, test_pred, test_y_t, alpha=0.1):
    """Asymmetric, scale-aware split-conformal interval (handles point-forecast bias).

    Symmetric intervals under-cover when the point forecast is biased (e.g. RW-with-drift
    lags an accelerating bull run). We take the lower/upper ``alpha/2`` quantiles of the
    **signed relative** residual ``e_rel = (actual - pred) / y_t`` on the calibration block
    and rescale by each test origin's ``y_t``. Returns ``(lo, hi)`` arrays for the test set:
    ``lo = pred + q_lo * y_t`` , ``hi = pred + q_hi * y_t``.
    """
    e = np.asarray(cal_resid_signed, dtype=float) / np.asarray(cal_y_t, dtype=float)
    e = e[np.isfinite(e)]
    test_pred = np.asarray(test_pred, dtype=float)
    test_y_t = np.asarray(test_y_t, dtype=float)
    if e.size == 0:
        nan = np.full(test_pred.shape, np.nan)
        return nan, nan
    q_lo = float(np.quantile(e, alpha / 2.0))
    q_hi = float(np.quantile(e, 1.0 - alpha / 2.0))
    return test_pred + q_lo * test_y_t, test_pred + q_hi * test_y_t


def adaptive_conformal_intervals(y_t, pred, actual, h, alpha=0.1, gamma=0.03, window=250):
    """Adaptive Conformal Inference (Gibbs & Candès 2021) over ordered forecast origins.

    Split-conformal under-covers here because the test regime is more volatile than the
    calibration block (exchangeability fails). ACI instead tracks an effective miscoverage
    rate ``a_t`` that it nudges from *realized* coverage: every miss widens the next interval.
    This yields near-nominal **long-run** coverage even under distribution shift.

    Implementation (causal): the half-width at origin ``i`` is ``q(1 - a_i)`` of the trailing
    ``window`` of **relative** absolute residuals from origins whose actual was already known
    (index ``<= i - h``), rescaled by ``y_t[i]``. After an origin's actual becomes known
    (``h`` steps later) its coverage updates ``a`` via ``a += gamma * (alpha - miss)``.
    Returns ``(lo, hi)`` arrays aligned to the inputs.
    """
    y_t = np.asarray(y_t, dtype=float)
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    n = len(pred)
    lo = np.empty(n); hi = np.empty(n); covered = np.zeros(n, dtype=bool)
    rel_res = np.abs(actual - pred) / y_t            # known only h steps after each origin
    a = alpha
    for i in range(n):
        usable = rel_res[: max(0, i - h + 1)]        # residuals known by origin i
        cal = usable[-window:] if usable.size else np.array([0.0])
        lvl = min(max(1.0 - a, 0.0), 1.0)
        q = float(np.quantile(cal, lvl)) if cal.size else 0.0
        hw = q * y_t[i]
        lo[i], hi[i] = pred[i] - hw, pred[i] + hw
        covered[i] = lo[i] <= actual[i] <= hi[i]
        j = i - h                                     # outcome of origin j is known now
        if j >= 0:
            miss = 0.0 if covered[j] else 1.0
            a = a + gamma * (alpha - miss)
    return lo, hi


def pi_coverage(y_true, pred, halfwidth=None, lo=None, hi=None):
    """Empirical coverage of a PI — either symmetric (``pred ± halfwidth``) or explicit ``[lo, hi]``."""
    y_true = np.asarray(y_true, dtype=float)
    if lo is not None and hi is not None:
        lo = np.asarray(lo, dtype=float); hi = np.asarray(hi, dtype=float)
    else:
        pred = np.asarray(pred, dtype=float); halfwidth = np.asarray(halfwidth, dtype=float)
        lo, hi = pred - halfwidth, pred + halfwidth
    return float(np.mean((y_true >= lo) & (y_true <= hi)))


# --------------------------------------------------------------------------------------
# Tree-extrapolation diagnostic (the level-target failure mode)
# --------------------------------------------------------------------------------------

def tree_extrapolation_report(y_train_target, y_pred, y_actual=None):
    """Diagnose the tree extrapolation cap on a level target.

    Trees cannot predict above the max target seen in training, so on a bull-market test set
    whose actuals exceed that ceiling they are systematically biased low. Returns the training
    ceiling, how many predictions reach/exceed it, and — the damning number — what share of the
    **actual** test targets lie above the ceiling (the region the tree structurally cannot reach).
    """
    ceil = float(np.max(y_train_target))
    yp = np.asarray(y_pred, dtype=float)
    out = {
        "train_ceiling": ceil,
        "share_pred_at_or_above_ceiling": float(np.mean(yp >= ceil * (1 - 0.005))),
        "n_pred_above_ceiling": int(np.sum(yp > ceil)),
    }
    if y_actual is not None:
        ya = np.asarray(y_actual, dtype=float)
        out["share_actual_above_ceiling"] = float(np.mean(ya > ceil))
    return out


# --------------------------------------------------------------------------------------
# Persistence of aligned test predictions for the comparison notebook
# --------------------------------------------------------------------------------------

def save_predictions(name, h, dates, y_t, actual, pred, lo=None, hi=None):
    """Persist aligned test predictions to models_medium/predictions/<name>_h{h}.csv."""
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    out = pd.DataFrame({
        "date": pd.to_datetime(dates).to_numpy(),
        "y_t": np.asarray(y_t, dtype=float),         # price at the forecast origin
        "actual": np.asarray(actual, dtype=float),    # true y_{t+h}
        "pred": np.asarray(pred, dtype=float),
    })
    if lo is not None:
        out["pi_lo"] = np.asarray(lo, dtype=float)
    if hi is not None:
        out["pi_hi"] = np.asarray(hi, dtype=float)
    path = os.path.join(PREDICTIONS_DIR, f"{name}_h{h}.csv")
    out.to_csv(path, index=False)
    return path
