"""The worked deal of docs/plan.md §7: a stated block valued from the day-ahead forecast. Not a trading result."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pmcore import clock

from .nerc import is_nerc_holiday


def deal_hours(f: pd.DataFrame, cfg: dict) -> pd.Series:
    days = pd.DatetimeIndex(f["day"])
    weekday = days.day_of_week < 5
    not_hol = np.array([not is_nerc_holiday(d) for d in days])
    in_hours = f["hour"].isin(cfg["hours_beginning"]).to_numpy()
    return pd.Series(weekday & not_hol & in_hours, index=f.index)


def daily_values(lbmp: pd.DataFrame, mcc: pd.DataFrame, cfg: dict, models=("B0", "M1", "M2")) -> pd.DataFrame:
    """Per deal day: forecast value of each model, settled value, and the congestion part (posted sign:
    LBMP = energy + losses − posted congestion, so the block's congestion part is −MW × posted congestion)."""
    mw = cfg["mw"]
    sel = deal_hours(lbmp, cfg)
    f = lbmp[sel]
    out = pd.DataFrame({"settled": f.groupby("day")["y"].sum() * mw,
                        "hours": f.groupby("day").size(),
                        "decision": f.groupby("day")["decision"].first(),
                        "posted": f.groupby("day")["y_posted"].max(),
                        "fold": f.groupby("day")["fold"].first()})
    for m in models:
        out[f"value_{m}"] = f.groupby("day")[m].sum() * mw
    g = mcc[deal_hours(mcc, cfg)]
    out["congestion_settled"] = -g.groupby("day")["y"].sum() * mw
    for m in models:
        if m in g:
            out[f"congestion_{m}"] = -g.groupby("day")[m].sum() * mw
    return out


def add_bands(v: pd.DataFrame, m: str, level: float = 0.90, residual_days: int = 365,
              min_days: int = 200) -> pd.DataFrame:
    """A band per day from the quantiles of the same deal's earlier daily value errors, admitted at the
    first decision of the day's fold (settled days posted before it, within `residual_days`)."""
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    v = v.copy()
    err = v["settled"] - v[f"value_{m}"]
    v[f"lo_{m}"], v[f"hi_{m}"] = np.nan, np.nan
    for fold, g in v.groupby("fold", sort=True):
        dec0, first = g["decision"].min(), g.index.min()
        past = v[(v["posted"] <= dec0 - clock.MARGIN) & (v.index >= first - pd.Timedelta(days=residual_days)) & (v["fold"] < fold)]
        if past.index.nunique() < min_days:
            continue
        lo, hi = err.loc[past.index].quantile([lo_q, hi_q])
        v.loc[g.index, f"lo_{m}"] = g[f"value_{m}"] + lo
        v.loc[g.index, f"hi_{m}"] = g[f"value_{m}"] + hi
    return v


def congestion_summary(v: pd.DataFrame, models=("B0", "M1", "M2")) -> dict:
    """The block's congestion part, settled and as forecast by the T2 models (plan §7)."""
    out = {"settled_total": float(v["congestion_settled"].sum())}
    for m in models:
        if f"congestion_{m}" in v:
            e = v[f"congestion_{m}"] - v["congestion_settled"]
            out[m] = {"forecast_total": float(v[f"congestion_{m}"].sum()), "mae_daily": float(e.abs().mean())}
    return out


def summary(v: pd.DataFrame, models=("B0", "M1", "M2")) -> dict:
    out = {"days": int(len(v)), "settled_total": float(v["settled"].sum()),
           "congestion_settled_total": float(v["congestion_settled"].sum())}
    for m in models:
        e = v[f"value_{m}"] - v["settled"]
        out[m] = {"forecast_total": float(v[f"value_{m}"].sum()), "mae_daily": float(e.abs().mean()),
                  "bias_daily": float(e.mean())}
        if f"lo_{m}" in v and v[f"lo_{m}"].notna().any():
            ok = v[f"lo_{m}"].notna()
            out[m]["band_coverage"] = float(((v.loc[ok, "settled"] >= v.loc[ok, f"lo_{m}"]) &
                                             (v.loc[ok, "settled"] <= v.loc[ok, f"hi_{m}"])).mean())
            out[m]["band_days"] = int(ok.sum())
    return out
