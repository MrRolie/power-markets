"""The registered models of docs/plan.md §5. Each takes a training design and returns forecasts per hour.

Interface: fit(train_X_daily, train_y_long, target) then predict(X_daily, y_long_rows) -> Series aligned to the
rows (one per actual hour of each forecast day).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LassoLarsIC

from .features import DA_LAGS, LF_AREAS, OTHER_ZONES, RT_LAGS

MCC_NONZERO = 0.005


def _series_of(target: str) -> tuple[str, str, tuple[int, ...]]:
    mkt = "da" if target.startswith(("T1", "T2")) else "rt"
    value = "lbmp" if target.endswith("lbmp") else "mcc"
    lags = DA_LAGS if mkt == "da" else RT_LAGS
    return mkt, value, lags


def feature_columns(X: pd.DataFrame, target: str, with_lf: bool = True) -> tuple[list[str], list[str]]:
    """(price-like columns, other columns) used by M1/M2 for this target."""
    mkt, value, lags = _series_of(target)
    price = [c for c in X.columns if any(c.startswith(f"{mkt}_{value}_l{k}_") for k in lags)]
    if mkt == "rt":  # real-time targets also use the day-ahead block of the same value (plan §5)
        price += [c for c in X.columns if any(c.startswith(f"da_{value}_l{k}_") for k in DA_LAGS)]
    price += [c for c in X.columns if any(c.startswith(f"da_{z}_l1_") for z in OTHER_ZONES)]
    other = [c for c in X.columns if c.startswith(("dow_", "holiday"))]
    if with_lf:
        other = [c for c in X.columns if any(c.startswith(f"lf_{a}_") for a in LF_AREAS)] + other
    return price, other


def _same_hour(X: pd.DataFrame, rows: pd.DataFrame, lag_prefix: str) -> np.ndarray:
    """Value of a lagged 24-hour block at each row's own local hour."""
    cols = [f"{lag_prefix}_h{h:02d}" for h in range(24)]
    m = X.loc[rows["day"].values, cols].to_numpy()
    return m[np.arange(len(rows)), rows["hour"].to_numpy()]


# ------------------------------------------------------------------ naive


class Naive:
    """B0 (lag = latest admitted day) or B1 (lag 7): the same hour of a lagged day of the same market."""

    def __init__(self, lag: int):
        self.lag = lag

    def fit(self, X, y, target):
        self.target = target
        return self

    def predict(self, X, rows):
        mkt, value, lags = _series_of(self.target)
        lag = lags[0] if self.lag == 0 else self.lag
        return pd.Series(_same_hour(X, rows, f"{mkt}_{value}_l{lag}"), index=rows.index)


class Zero:
    def fit(self, X, y, target):
        return self

    def predict(self, X, rows):
        return pd.Series(0.0, index=rows.index)


# ------------------------------------------------------------------ M1: LEAR-style


def _robust(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    med = np.nanmedian(x, axis=0)
    mad = np.nanmedian(np.abs(x - med), axis=0)
    sd = np.nanstd(x, axis=0)
    scale = np.where(mad > 0, mad, np.where(sd > 0, sd, 1.0))
    return med, scale


class LEAR:
    def __init__(self, window_days: int = 728, with_lf: bool = True, asinh: bool = True):
        self.window_days, self.with_lf, self.asinh = window_days, with_lf, asinh

    def _tx(self, x, med, sc):
        z = (x - med) / sc
        return np.arcsinh(z) if self.asinh else z

    def fit(self, X, y, target):
        self.target = target
        days = X.index.sort_values()[-self.window_days:]
        X = X.loc[days]
        y = y[y["day"].isin(days)]
        self.price, self.other = feature_columns(X, target, self.with_lf)
        P, O = X[self.price].to_numpy(float), X[self.other].to_numpy(float)
        self.pm, self.ps = _robust(P)
        self.om, self.os = _robust(O)
        self.os[np.isin(np.arange(O.shape[1]), [i for i, c in enumerate(self.other) if c.startswith(("dow_", "holiday"))])] = 1.0
        self.om[[i for i, c in enumerate(self.other) if c.startswith(("dow_", "holiday"))]] = 0.0
        F = np.hstack([self._tx(P, self.pm, self.ps), (O - self.om) / self.os])
        Fi = pd.DataFrame(F, index=X.index)
        self.models, self.fallback = {}, {}
        ok_days = Fi.index[~Fi.isna().any(axis=1)]  # a training day with a missing input is left out
        y = y[y["day"].isin(ok_days)]
        yv = y[target].to_numpy(float)
        self.ym, self.ys = _robust(yv[:, None])
        for h in range(24):
            sel = (y["hour"] == h).to_numpy()
            self.fallback[h] = float(np.median(yv[sel]))
            yy = self._tx(yv[sel], self.ym[0], self.ys[0])
            ff = Fi.loc[y.loc[sel, "day"].values].to_numpy()
            if np.ptp(yy) == 0:
                continue  # constant target: the training median is the forecast (plan §5)
            try:
                self.models[h] = LassoLarsIC(criterion="aic").fit(ff, yy)
            except (ValueError, np.linalg.LinAlgError):
                continue  # failed fit: the training median is the forecast
        self.n_fallback_hours = 24 - len(self.models)
        return self

    def predict(self, X, rows):
        P, O = X[self.price].to_numpy(float), X[self.other].to_numpy(float)
        F = pd.DataFrame(np.hstack([self._tx(P, self.pm, self.ps), (O - self.om) / self.os]), index=X.index)
        out = np.empty(len(rows))
        for h, idx in rows.groupby("hour").indices.items():
            if h not in self.models:
                out[idx] = self.fallback[h]
                continue
            Fh = F.loc[rows["day"].values[idx]].to_numpy()
            bad = np.isnan(Fh).any(axis=1)
            z = self.models[h].predict(np.where(bad[:, None], 0.0, Fh))
            v = (np.sinh(z) if self.asinh else z) * self.ys[0] + self.ym[0]
            out[idx] = np.where(bad, self.fallback[h], v)  # missing input: the hour's training median
            self.n_missing_rows = getattr(self, "n_missing_rows", 0) + int(bad.sum())
        return pd.Series(out, index=rows.index)


# ------------------------------------------------------------------ M2 / P2: boosted trees


HGB = dict(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=40, l2_regularization=1.0,
           random_state=0, early_stopping=False)


def _long_features(X, rows, cols):
    F = X.loc[rows["day"].values, cols].to_numpy(float)
    return np.hstack([F, rows["hour"].to_numpy(float)[:, None]])


class GBM:
    def __init__(self, train_from: str = "2018-01-01", with_lf: bool = True):
        self.train_from, self.with_lf = pd.Timestamp(train_from), with_lf

    def fit(self, X, y, target):
        self.target = target
        X = X[X.index >= self.train_from]
        y = y[y["day"].isin(X.index)]
        price, other = feature_columns(X, target, self.with_lf)
        self.cols = price + other
        self.m = HistGradientBoostingRegressor(loss="absolute_error", **HGB)
        self.m.fit(_long_features(X, y, self.cols), y[target].to_numpy(float))
        return self

    def predict(self, X, rows):
        return pd.Series(self.m.predict(_long_features(X, rows, self.cols)), index=rows.index)


def prob_climatology(y: pd.DataFrame, target: str, posted_col: str, days: pd.DatetimeIndex,
                     decision: pd.Series, rows: pd.DataFrame, window_days: int = 28) -> pd.Series:
    """P0: share of non-zero congestion at the same local hour over the latest `window_days` admitted days."""
    from pmcore import clock

    nz = (y[target].abs() > MCC_NONZERO).astype(float)
    mat = y.assign(nz=nz).pivot_table(index="day", columns="hour", values="nz", aggfunc="mean")
    mat = mat.reindex(columns=range(24)).ffill(axis=1).sort_index()
    posted = y.groupby("day")[posted_col].max().reindex(mat.index)
    post = clock._utc_np(posted)
    margin = clock.MARGIN.to_timedelta64()
    vals = mat.to_numpy()
    m = np.full((len(days), 24), np.nan)
    for i, dec in enumerate(clock._utc_np(decision.reindex(days))):
        known = np.flatnonzero(post <= dec - margin)  # each day counted only if posted in time (plan §5)
        if known.size >= window_days:
            m[i] = vals[known[-window_days:]].mean(axis=0)
    di = pd.Index(days).get_indexer(rows["day"].values)
    return pd.Series(m[di, rows["hour"].to_numpy()], index=rows.index)


class ProbGBM:
    def __init__(self, train_from: str = "2018-01-01"):
        self.train_from = pd.Timestamp(train_from)

    def fit(self, X, y, target):
        self.target = target
        X = X[X.index >= self.train_from]
        y = y[y["day"].isin(X.index)]
        price, other = feature_columns(X, target, True)
        self.cols = price + other
        self.m = HistGradientBoostingClassifier(**HGB)
        self.m.fit(_long_features(X, y, self.cols), (y[target].abs() > MCC_NONZERO).to_numpy(int))
        return self

    def predict(self, X, rows):
        return pd.Series(self.m.predict_proba(_long_features(X, rows, self.cols))[:, 1], index=rows.index)
