"""Forecast comparison: Diebold–Mariano with a Newey–West variance, and Holm's correction."""

from __future__ import annotations

import numpy as np
from scipy import stats


def newey_west_var_of_mean(d: np.ndarray, lags: int) -> float:
    """Long-run variance of the mean of d (Bartlett kernel)."""
    d = np.asarray(d, float)
    n = d.size
    e = d - d.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1)
        s += 2 * w * (e[k:] @ e[:-k]) / n
    return s / n


def diebold_mariano(loss_model: np.ndarray, loss_base: np.ndarray, lags: int = 7, h: int = 1) -> dict:
    """One-sided test of H0: E[loss_model - loss_base] >= 0 against "the model's loss is lower".

    Inputs are per-period losses (here: daily means). Long-run variance: Bartlett kernel with `lags` lags.
    The statistic gets the Harvey–Leybourne–Newbold factor for horizon h; the p-value is from Student's t with
    n − 1 degrees of freedom. A non-positive variance (a model identical to its baseline) does not reject."""
    d = np.asarray(loss_model, float) - np.asarray(loss_base, float)
    ok = ~np.isnan(d)
    d = d[ok]
    if d.size < 2 * (lags + 1):
        raise ValueError(f"{d.size} periods: too few for a test with {lags} lags")
    n = d.size
    v = newey_west_var_of_mean(d, lags)
    if not v > 0:
        return {"n": int(n), "mean_diff": float(d.mean()), "stat": None, "p_one_sided": 1.0,
                "note": "non-positive variance: does not reject"}
    hln = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat = hln * d.mean() / np.sqrt(v)
    return {"n": int(n), "mean_diff": float(d.mean()), "stat": float(stat),
            "p_one_sided": float(stats.t.cdf(stat, df=n - 1))}


def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm's step-down procedure. Returns, per key, the adjusted p-value and whether it rejects."""
    keys = sorted(pvalues, key=pvalues.get)
    m = len(keys)
    out, running, stop = {}, 0.0, False
    for i, k in enumerate(keys):
        adj = min(1.0, (m - i) * pvalues[k])
        running = max(running, adj)
        rejects = (not stop) and pvalues[k] <= alpha / (m - i)
        if not rejects:
            stop = True
        out[k] = {"p": pvalues[k], "p_holm": running, "rejects": rejects}
    return out
