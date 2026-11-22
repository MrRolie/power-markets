"""Scores of docs/plan.md §6 and the intervals of §5, from a table of hourly forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pmcore import clock, stats

from .models import MCC_NONZERO

POINT = ("B0", "B1", "M1", "M2", "Z", "M1_noLF")
PROB = ("P0", "P2")


def point_scores(f: pd.DataFrame, models=POINT) -> dict:
    out = {"_outcomes": {"hours": int(len(f)), "missing_hours": int(f["y"].isna().sum()),
                         "missing_days": sorted(str(d.date()) for d in f.loc[f["y"].isna(), "day"].unique())}}
    top = f["y"] >= f["y"].quantile(0.9)
    for m in models:
        if m not in f:
            continue
        e = f[m] - f["y"]
        out[m] = {"n_hours": int(e.notna().sum()), "mae": float(e.abs().mean()), "rmse": float(np.sqrt((e**2).mean())),
                  "bias": float(e.mean()), "mae_top_decile": float(e[top].abs().mean())}
    return out


def event(y: pd.Series) -> pd.Series:
    """Non-zero posted congestion; NaN where the outcome is missing (never scored as "no congestion")."""
    return (y.abs() > MCC_NONZERO).astype(float).where(y.notna())


def prob_scores(f: pd.DataFrame) -> dict:
    ev = event(f["y"])
    return {m: {"n_hours": int((f[m].notna() & ev.notna()).sum()), "brier": float(((f[m] - ev) ** 2).mean()),
                "event_rate": float(ev.mean())} for m in PROB if m in f}


SEASON = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA",
          9: "SON", 10: "SON", 11: "SON"}


def robustness(f: pd.DataFrame, target: str) -> dict:
    """Plan §9: scores by year, season, hour group and (prices) realised price decile."""
    days = pd.DatetimeIndex(f["day"])
    hg = pd.cut(f["hour"], [-1, 6, 22, 23], labels=["00-06", "07-22", "23"])
    groups = {"year": days.year, "season": days.month.map(SEASON), "hour_group": hg.astype(str)}
    if target.endswith("lbmp"):
        groups["price_decile"] = pd.qcut(f["y"], 10, labels=False, duplicates="drop")
    return {k: {str(g): point_scores(x) for g, x in f.groupby(np.asarray(v))} for k, v in groups.items()}


def daily_loss(f: pd.DataFrame, m: str, kind: str = "abs") -> pd.Series:
    if kind == "abs":
        loss = (f[m] - f["y"]).abs()
    else:
        loss = (f[m] - event(f["y"])) ** 2
    return loss.groupby(f["day"]).mean()


def compare(f: pd.DataFrame, m: str, base: str, kind: str = "abs", lags: int = 7) -> dict:
    a, b = daily_loss(f, m, kind), daily_loss(f, base, kind)
    a, b = a.align(b, join="inner")
    return stats.diebold_mariano(a.to_numpy(), b.to_numpy(), lags=lags)


def add_intervals(f: pd.DataFrame, m: str, level: float = 0.90, residual_days: int = 365,
                  min_days: int = 330) -> pd.DataFrame:
    """Per local hour, the 5 % and 95 % quantiles of the model's earlier residuals whose targets were posted
    before the decision of the first day of the forecast's fold, over the latest `residual_days` days."""
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    f = f.copy()
    f[f"{m}_lo"] = np.nan
    f[f"{m}_hi"] = np.nan
    res = (f["y"] - f[m])
    for fold, g in f.groupby("fold", sort=True):
        dec0 = g["decision"].min()
        first = g["day"].min()
        past = f[(f["y_posted"] <= dec0 - clock.MARGIN) & (f["day"] >= first - pd.Timedelta(days=residual_days))
                 & (f["fold"] < fold)]
        days_avail = past["day"].nunique()
        if days_avail < min_days:
            continue
        q = res.loc[past.index].groupby(past["hour"]).quantile([lo_q, hi_q]).unstack()
        idx = g.index
        f.loc[idx, f"{m}_lo"] = g[m] + q.loc[g["hour"], lo_q].to_numpy()
        f.loc[idx, f"{m}_hi"] = g[m] + q.loc[g["hour"], hi_q].to_numpy()
    return f


def interval_scores(f: pd.DataFrame, m: str) -> dict:
    ok = f[f"{m}_lo"].notna() & f["y"].notna()  # a missing outcome is neither a hit nor a miss
    if not ok.any():
        return {"n_hours": 0}
    g = f[ok]
    cov = ((g["y"] >= g[f"{m}_lo"]) & (g["y"] <= g[f"{m}_hi"])).mean()
    return {"n_hours": int(ok.sum()), "coverage": float(cov), "mean_width": float((g[f"{m}_hi"] - g[f"{m}_lo"]).mean())}
