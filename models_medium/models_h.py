"""Model runners for the medium-horizon (T+30 / T+60) study.

Each ``run_*`` returns a uniform result dict so the notebooks/comparison stay model-agnostic:
``{name, h, target, dates, y_t, actual, pred, metrics, dir_acc, skill_drift, dm_p, ...}``.

Design decisions (justified in interpretation/02_review.md and the notebooks):
- **Direct multi-step** (one model per horizon h), predicting the **price level** y_{t+h}.
- **Statistical model = univariate SARIMA on the level** (not SARIMAX): a true multi-step
  SARIMAX would need *future* exogenous values, which are unknown at the forecast origin.
  Exogenous information is instead routed through the ML and hybrid models, which regress
  y_{t+h} on features known **at** t.
- **Boosting runs two ways**: ``target='level'`` (exposes the tree-extrapolation cap on a
  rising test set — a cautionary diagnostic) and ``target='return'`` (predict the h-day
  log-return, reconstruct the level — leakage- and extrapolation-safe; the reported variant).
- **Hybrid = drift baseline + ML-on-residuals**. The drift baseline equals ARIMA(0,1,0)+drift
  (what auto_arima selects on this near-random-walk series), so this is the SARIMA+ML hybrid;
  residuals are ~stationary, so trees never hit the extrapolation cap.
"""

import os
import sys
import warnings

import numpy as np
import pandas as pd

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import models_medium.utils_h as U  # noqa: E402

SEED = U.SEED
np.random.seed(SEED)


# ============================================================ result assembly
def _result(name, h, target, te, pred, lo=None, hi=None, extra=None):
    """Build the uniform result dict + persist aligned predictions."""
    yt = te["y"].to_numpy()
    actual = te[f"y_h{h}"].to_numpy()
    pred = np.asarray(pred, dtype=float)
    m = U.evaluate(actual, pred)
    drift = U.estimate_drift(te["y"])  # in-sample drift only for skill reference fallback
    res = {
        "name": name, "h": h, "target": target,
        "dates": te["date"].to_numpy(), "y_t": yt, "actual": actual, "pred": pred,
        "metrics": m,
        "dir_acc": U.directional_accuracy_h(yt, actual, pred),
    }
    if extra:
        res.update(extra)
    U.save_predictions(name, h, te["date"], yt, actual, pred, lo=lo, hi=hi)
    return res


# ============================================================ benchmarks
def run_benchmarks(df, h):
    """Flat random walk and random-walk-with-drift (drift fit on train+val)."""
    d = U.prepare_xy(df, h)
    tr, va, te = U.chrono_split(d)
    drift = U.estimate_drift(pd.concat([tr, va])["y"])
    out = {}
    out["random_walk"] = _result("random_walk", h, "level", te, U.rw_flat_pred(te["y"].to_numpy()))
    out["rw_drift"] = _result("rw_drift", h, "level", te, U.rw_drift_pred(te["y"].to_numpy(), drift, h))
    return out, drift


# ============================================================ SARIMA (level, analytic PIs)
def run_sarima(df, h, alpha=0.1):
    """Univariate SARIMA on the price level; rolling h-step forecast over the test block.

    Order chosen by ``pmdarima.auto_arima`` on train+val (seasonal off — STL seasonality ~1.4%).
    The fitted state-space model is then extended one realized day at a time and queried for an
    h-step forecast at each test origin, giving analytic prediction intervals.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    import pmdarima as pm

    full = df.sort_values("date").reset_index(drop=True)
    y = full["y"].to_numpy()
    d = U.prepare_xy(df, h)
    tr, va, te = U.chrono_split(d)
    pos = {dt: i for i, dt in enumerate(full["date"])}
    test_pos = [pos[dt] for dt in te["date"]]
    j0 = test_pos[0]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        auto = pm.auto_arima(y[:j0 + 1], seasonal=False, stepwise=True, d=1,
                             max_p=3, max_q=3, with_intercept=True,
                             suppress_warnings=True, error_action="ignore")
        order = auto.order
        res = SARIMAX(y[:j0 + 1], order=order, trend="c",
                      enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)

        preds, los, his = [], [], []
        for idx, p in enumerate(test_pos):
            fc = res.get_forecast(steps=h)
            preds.append(float(fc.predicted_mean[h - 1]))
            ci = fc.conf_int(alpha=alpha)
            los.append(float(ci[h - 1, 0])); his.append(float(ci[h - 1, 1]))
            if idx < len(test_pos) - 1:
                res = res.append(y[p + 1:p + 2], refit=False)

    return _result(f"sarima{order}", h, "level", te, preds, lo=los, hi=his,
                   extra={"order": order, "pi_coverage": U.pi_coverage(te[f"y_h{h}"].to_numpy(), None, lo=los, hi=his)})


# ============================================================ gradient boosting
def _make_model(name):
    if name == "lgbm":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(random_state=SEED, verbose=-1, n_jobs=1)
    if name == "xgb":
        from xgboost import XGBRegressor
        return XGBRegressor(random_state=SEED, verbosity=0, n_jobs=1)
    if name == "cat":
        from catboost import CatBoostRegressor
        return CatBoostRegressor(random_state=SEED, verbose=0, thread_count=1)
    raise ValueError(name)


def _space(trial, name):
    if name == "lgbm":
        return dict(n_estimators=trial.suggest_int("n_estimators", 150, 600),
                    num_leaves=trial.suggest_int("num_leaves", 7, 63),
                    learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    min_child_samples=trial.suggest_int("min_child_samples", 10, 80),
                    subsample=trial.suggest_float("subsample", 0.6, 1.0),
                    colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0))
    if name == "xgb":
        return dict(n_estimators=trial.suggest_int("n_estimators", 150, 600),
                    max_depth=trial.suggest_int("max_depth", 2, 6),
                    learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    subsample=trial.suggest_float("subsample", 0.6, 1.0),
                    colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
                    min_child_weight=trial.suggest_int("min_child_weight", 1, 20))
    if name == "cat":
        return dict(iterations=trial.suggest_int("iterations", 150, 600),
                    depth=trial.suggest_int("depth", 2, 8),
                    learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                    l2_leaf_reg=trial.suggest_float("l2_leaf_reg", 1.0, 10.0))
    raise ValueError(name)


def _tune(name, X, y, h, n_trials=25):
    import optuna
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_squared_error

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    tscv = TimeSeriesSplit(n_splits=4, gap=h)

    def obj(trial):
        params = _space(trial, name)
        errs = []
        for tri, vai in tscv.split(X):
            mdl = _make_model(name); mdl.set_params(**params)
            mdl.fit(X[tri], y[tri])
            errs.append(np.sqrt(mean_squared_error(y[vai], mdl.predict(X[vai]))))
        return float(np.mean(errs))

    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
    return study.best_params


def run_boosting(df, h, name="lgbm", target="return", n_trials=25, shap_sample=200):
    """Direct-h gradient boosting. ``target='return'`` predicts log(y_{t+h}/y_t) and
    reconstructs the level (safe); ``target='level'`` predicts y_{t+h} directly (extrapolation
    diagnostic). Returns the result dict plus tuned params, SHAP importances, and (for level)
    the extrapolation report.
    """
    feats = U.FEATURE_COLUMNS
    d = U.prepare_xy(df, h)
    tr, va, te = U.chrono_split(d)
    trainval = pd.concat([tr, va])
    Xtv = trainval[feats].to_numpy(); Xte = te[feats].to_numpy()

    if target == "return":
        ytv = np.log(trainval[f"y_h{h}"].to_numpy() / trainval["y"].to_numpy())
    else:
        ytv = trainval[f"y_h{h}"].to_numpy()

    best = _tune(name, Xtv, ytv, h, n_trials=n_trials)
    mdl = _make_model(name); mdl.set_params(**best)
    mdl.fit(Xtv, ytv)
    raw = mdl.predict(Xte)
    pred = te["y"].to_numpy() * np.exp(raw) if target == "return" else raw

    extra = {"params": best}
    if target == "level":
        extra["extrapolation"] = U.tree_extrapolation_report(
            trainval[f"y_h{h}"].to_numpy(), pred, te[f"y_h{h}"].to_numpy())

    # SHAP on the tuned model (TreeExplainer; sample test rows for speed)
    try:
        import shap
        Xs = Xte[:shap_sample]
        sv = shap.TreeExplainer(mdl).shap_values(Xs)
        imp = np.abs(np.asarray(sv)).mean(axis=0)
        extra["shap"] = dict(sorted(zip(feats, imp.tolist()), key=lambda kv: -kv[1]))
    except Exception as e:  # SHAP is best-effort; never block the run
        extra["shap_error"] = repr(e)

    return _result(f"{name}_{target}", h, target, te, pred, extra=extra)


# ============================================================ hybrid (drift + ML residual)
def run_hybrid(df, h, name="lgbm", n_trials=25):
    """Hybrid SARIMA/drift baseline + ML on the residual (the SARIMAX+ML architecture).

    Baseline = RW-with-drift (= ARIMA(0,1,0)+drift). ML learns the residual
    ``y_{t+h} - baseline`` from features known at t; the residual is ~stationary, so the tree
    never extrapolates beyond its training range. Final forecast = baseline + ML residual.
    """
    feats = U.FEATURE_COLUMNS
    d = U.prepare_xy(df, h)
    tr, va, te = U.chrono_split(d)
    trainval = pd.concat([tr, va])
    drift = U.estimate_drift(trainval["y"])

    base_tv = U.rw_drift_pred(trainval["y"].to_numpy(), drift, h)
    resid_tv = trainval[f"y_h{h}"].to_numpy() - base_tv
    Xtv = trainval[feats].to_numpy(); Xte = te[feats].to_numpy()

    best = _tune(name, Xtv, resid_tv, h, n_trials=n_trials)
    mdl = _make_model(name); mdl.set_params(**best)
    mdl.fit(Xtv, resid_tv)

    base_te = U.rw_drift_pred(te["y"].to_numpy(), drift, h)
    pred = base_te + mdl.predict(Xte)
    return _result(f"hybrid_{name}", h, "level", te, pred, extra={"params": best, "drift": drift})


def attach_skill_and_dm(results, drift, h):
    """Add skill-vs-drift and Diebold-Mariano (vs RW-drift) to each result in-place."""
    bench = results["rw_drift"]["pred"]
    actual = results["rw_drift"]["actual"]
    for r in results.values():
        r["skill_drift"] = U.skill_vs(bench, r["pred"], actual)
        if r["name"] == "rw_drift":
            r["dm_stat"], r["dm_p"] = 0.0, 1.0
        else:
            r["dm_stat"], r["dm_p"] = U.diebold_mariano(actual, r["pred"], bench, h)
    return results
