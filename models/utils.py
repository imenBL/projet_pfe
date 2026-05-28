"""Shared helpers for the Phase-3 modeling notebooks.

Keeps every notebook on the *same* data, split, target and metrics so the final
comparison is fair. Import from any notebook in `models/` with `import utils`.

Forecast framing (locked): supervised models predict the next-day log-return
`ret_next = ln(y_{t+1}) - ln(y_t)` and reconstruct the price `ŷ_{t+1} = y_t · e^{r̂}`;
ARIMA/Prophet model the level natively. All models are scored on the $/g price scale.
"""

import os
import sys

import numpy as np
import pandas as pd

# Make the repo-root modules (data_access, db_settings) importable no matter the notebook CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import data_access  # noqa: E402
from USA_cleaning import (  # noqa: E402
    ENGINEERED_FEATURES, MACRO_FEATURES, MARKET_FEATURES,
    GEO_FEATURES, RESERVE_FEATURE, CALENDAR_FEATURES,
)

# project_plan.md feature contract: 6 engineered + 14 exogenous + 4 calendar = 24.
FEATURE_COLUMNS = (
    ENGINEERED_FEATURES + MACRO_FEATURES + MARKET_FEATURES
    + GEO_FEATURES + RESERVE_FEATURE + CALENDAR_FEATURES
)
TARGET = "ret_next"

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
SEED = 42

# Where each model notebook drops its aligned test predictions for 06_comparison.
PREDICTIONS_DIR = os.path.join(_REPO_ROOT, "models", "predictions")


def load_modeling_frame():
    """Cleaned, sorted frame with price `y` and the next-day log-return `ret_next`.

    Drops the warm-up rows (engineered-feature NaNs) and the final row (no t+1 target),
    leaving a contiguous run of trading days (~2 417 rows).
    """
    df = data_access.load_features().copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    log_y = np.log(df["y"])
    df[TARGET] = log_y.shift(-1) - log_y

    df = df.dropna(subset=FEATURE_COLUMNS + [TARGET]).reset_index(drop=True)
    return df


def chrono_split(df):
    """Chronological 70/15/15 split by position on the sorted frame (never shuffled)."""
    n = len(df)
    i_train = int(n * TRAIN_RATIO)
    i_val = int(n * (TRAIN_RATIO + VAL_RATIO))
    return df.iloc[:i_train], df.iloc[i_train:i_val], df.iloc[i_val:]


def reconstruct_price(y_t, ret):
    """Reconstruct next-day price from the current level and a (predicted) log-return."""
    return np.asarray(y_t, dtype=float) * np.exp(np.asarray(ret, dtype=float))


def actual_test_price(test):
    """True next-day price for each test row (= y_t · e^{ret_next})."""
    return reconstruct_price(test["y"], test[TARGET])


def random_walk_pred(test):
    """Naive reference: predict tomorrow = today (ŷ_{t+1} = y_t)."""
    return np.asarray(test["y"], dtype=float)


# ----------------------------------------------------------------------------- metrics

def evaluate(y_true, y_pred):
    """{MAE, RMSE, MAPE (%), R2} on the $/g price scale."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(np.abs(err / y_true)) * 100.0),
        "R2": 1.0 - float(np.sum(err ** 2)) / ss_tot if ss_tot > 0 else float("nan"),
    }


def directional_accuracy(test, price_pred):
    """Share of test days where the predicted price move matches the actual move sign."""
    y_t = np.asarray(test["y"], dtype=float)
    actual = actual_test_price(test)
    return float(np.mean(np.sign(np.asarray(price_pred) - y_t) == np.sign(actual - y_t)))


def skill_vs_rw(test, price_pred):
    """MSE skill score vs the random walk: 1 - MSE_model / MSE_rw (0 = tie, >0 = better)."""
    actual = actual_test_price(test)
    mse_model = np.mean((np.asarray(price_pred) - actual) ** 2)
    mse_rw = np.mean((random_walk_pred(test) - actual) ** 2)
    return float(1.0 - mse_model / mse_rw) if mse_rw > 0 else float("nan")


def save_predictions(name, test, price_pred):
    """Persist aligned test predictions to models/predictions/<name>.csv for the comparison."""
    os.makedirs(PREDICTIONS_DIR, exist_ok=True)
    out = pd.DataFrame({
        "date": pd.to_datetime(test["date"]).to_numpy(),
        "y_t": np.asarray(test["y"], dtype=float),       # today's price (random-walk pred)
        "actual": actual_test_price(test),                # true next-day price
        "pred": np.asarray(price_pred, dtype=float),
    })
    out.to_csv(os.path.join(PREDICTIONS_DIR, f"{name}.csv"), index=False)
    return out
