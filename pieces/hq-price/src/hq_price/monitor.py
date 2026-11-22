"""The monitor of docs/plan.md §8: when the forecast should stop being trusted.

Each day's statistic uses only errors whose targets were posted before that day's decision time. Thresholds
are fixed from the validation days and frozen in the run record before the held-out replay.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from pmcore import clock

from .models import MCC_NONZERO


BASELINE = {"T1_da_lbmp": "B0", "T2_da_mcc": "Z", "T3_rt_lbmp": "B0", "T4_rt_mcc": "Z"}
REGIME = {"T1_da_lbmp": "share_nonzero_mcc", "T2_da_mcc": "share_nonzero_mcc",
          "T3_rt_lbmp": "share_le0", "T4_rt_mcc": "share_le0"}


def _daily(f: pd.DataFrame, m: str, base: str) -> pd.DataFrame:
    g = f.assign(ae_m=(f[m] - f["y"]).abs(), ae_b=(f[base] - f["y"]).abs(), e_m=f[m] - f["y"],
                 nz=(f["y"].abs() > MCC_NONZERO).astype(float).where(f["y"].notna()),
                 le0=(f["y"] <= 0).astype(float).where(f["y"].notna()))
    d = g.groupby("day").agg(ae_m=("ae_m", "mean"), ae_b=("ae_b", "mean"), e_m=("e_m", "mean"),
                             nz=("nz", "mean"), le0=("le0", "mean"), posted=("y_posted", "max"),
                             decision=("decision", "first"))
    return d.sort_index()


def statistics(f: pd.DataFrame, m: str, base: str = "B0", window: int = 28,
               regime_source: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per decision day: the window statistics over the latest `window` days whose targets were posted
    at least the admission margin before that day's decision. The regime shares come from `regime_source`
    (the day-ahead congestion or the real-time price rows, plan §8) when given, else from `f` itself."""
    d = _daily(f, m, base)
    if regime_source is not None:
        r = _daily(regime_source.assign(_z=0.0), "_z", "_z")[["nz", "le0"]]
        d[["nz", "le0"]] = r.reindex(d.index).to_numpy()
    posted = d["posted"].to_numpy()
    rows = []
    for day, dec in zip(d.index, d["decision"]):
        known = np.flatnonzero(posted <= dec - clock.MARGIN)
        if known.size < window:
            rows.append((day, np.nan, np.nan, np.nan, np.nan))
            continue
        w = d.iloc[known[-window:]]
        den = w["ae_b"].mean()
        rel = w["ae_m"].mean() / den if den > 0 else np.nan  # zero baseline window: not computed (plan §8)
        rows.append((day, rel, w["e_m"].mean(), w["nz"].mean(), w["le0"].mean()))
    return pd.DataFrame(rows, columns=["day", "rel_mae", "bias", "share_nonzero_mcc", "share_le0"]).set_index("day")


def thresholds(stats_validation: pd.DataFrame, cfg: dict) -> dict:
    s = stats_validation.dropna()
    lo_b, hi_b = cfg["bias_band"]
    lo_r, hi_r = cfg["regime_band"]
    return {"rel_mae_hi": float(s["rel_mae"].quantile(cfg["rel_mae_quantile"])),
            "bias": [float(s["bias"].quantile(lo_b)), float(s["bias"].quantile(hi_b))],
            "share_nonzero_mcc": [float(s["share_nonzero_mcc"].quantile(lo_r)), float(s["share_nonzero_mcc"].quantile(hi_r))],
            "share_le0": [float(s["share_le0"].quantile(lo_r)), float(s["share_le0"].quantile(hi_r))],
            "n_days": int(len(s))}


def states(stats: pd.DataFrame, th: dict, regime_col: str, data_flag: pd.Series | None = None,
           stop_after: int = 7) -> pd.DataFrame:
    s = stats.copy()
    s["sig_rel"] = s["rel_mae"] > th["rel_mae_hi"]
    s["sig_bias"] = (s["bias"] < th["bias"][0]) | (s["bias"] > th["bias"][1])
    lo, hi = th[regime_col]
    s["sig_regime"] = (s[regime_col] < lo) | (s[regime_col] > hi)
    s["sig_data"] = False if data_flag is None else data_flag.reindex(s.index).fillna(False).astype(bool)
    run = s["sig_rel"].astype(int).groupby((~s["sig_rel"]).cumsum()).cumsum()
    n_stat = s[["sig_rel", "sig_bias", "sig_regime"]].sum(axis=1)
    stop = (run >= stop_after) | (n_stat >= 2) | s["sig_data"]
    s["state"] = np.where(stop, "stop trusting", np.where(n_stat >= 1, "watch", "trust"))
    s.loc[s["bias"].isna(), "state"] = "no verdict (window not full)"
    return s
