"""The design table: one row per operating day D, built only from files posted before D's decision time.

Inputs and lags are those of docs/plan.md §2 and §5. Every row records the posting time of each file it used,
and `require_before` refuses the table if any is not strictly earlier than the row's decision time.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from pmcore import clock, nyiso

from .nerc import is_nerc_holiday

LOC = "H Q"
DA_LAGS = (1, 2, 3, 7)
RT_LAGS = (2, 3, 4, 7)
OTHER_ZONES = ("NORTH", "N.Y.C.")
LF_AREAS = ("NYISO", "North", "Capitl")
TARGETS = {
    "T1_da_lbmp": ("da", "lbmp"),
    "T2_da_mcc": ("da", "mcc"),
    "T3_rt_lbmp": ("rt", "lbmp"),
    "T4_rt_mcc": ("rt", "mcc"),
}


@dataclass
class Design:
    X: pd.DataFrame  # index: operating day; feature columns
    used_posted: pd.DataFrame  # index: operating day; one posting-time column per file used
    decision: pd.Series  # index: operating day; UTC decision time
    y: pd.DataFrame  # long: day, ts_utc, hour (local), target columns, y_posted
    fallback_age: pd.DataFrame  # index: operating day; per slot, days between the slot's day and the day used


def _lag_block(posted: pd.Series, mat: pd.DataFrame, days: pd.Index, dec: pd.Series, lag: int,
               prefix: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    lag_days = pd.Series(days - pd.Timedelta(days=lag), index=days)
    a = clock.admitted_days(posted, lag_days, dec)
    block = mat.reindex(a.values)
    block.index = days
    block.columns = [f"{prefix}_l{lag}_h{h:02d}" for h in block.columns]
    used = posted.reindex(a.values).set_axis(days).rename(f"{prefix}_l{lag}")
    age = pd.Series((lag_days.values - a.values) / pd.Timedelta(days=1), index=days, name=f"{prefix}_l{lag}")
    return block, used, age


def _load_forecast(lf: pd.DataFrame, days: pd.Index, dec: pd.Series) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    issues = lf.groupby("issue_file_day")["posted_utc"].max().sort_index()
    lf = lf[lf["area"].isin(LF_AREAS)].copy()
    lf["day"] = lf["ts_utc"].dt.tz_convert(nyiso.TZ).dt.tz_localize(None).dt.normalize()
    lf = lf[(lf["day"] - lf["issue_file_day"]).dt.days.between(0, 3)]
    blocks, used = [], []
    chosen = clock.admitted_days(issues, pd.Series(days, index=days), dec)
    keep_ok = (days - chosen.values).days <= 3
    chosen = chosen.where(keep_ok)
    for area in LF_AREAS:
        sub = lf[lf["area"] == area]
        mat = clock.local_hour_matrix(sub.rename(columns={"mw": "v"}), "v", day_col=["issue_file_day", "day"])
        idx = pd.MultiIndex.from_arrays([chosen.values, days])
        b = mat.reindex(idx)
        b.index = days
        b.columns = [f"lf_{area}_h{h:02d}" for h in b.columns]
        blocks.append(b)
    used = issues.reindex(chosen.values).set_axis(days).rename("lf")
    age = pd.Series((days - pd.Timedelta(days=1) - chosen.values) / pd.Timedelta(days=1), index=days, name="lf")
    return pd.concat(blocks, axis=1), used, age


def _calendar(days: pd.Index) -> pd.DataFrame:
    c = pd.DataFrame(index=days)
    for d in range(7):
        c[f"dow_{d}"] = (days.day_of_week == d).astype(float)
    c["holiday"] = np.array([is_nerc_holiday(d) for d in days], dtype=float)
    return c


def build(da: pd.DataFrame, rt: pd.DataFrame, lf: pd.DataFrame, days: pd.DatetimeIndex) -> Design:
    days = pd.DatetimeIndex(days, name="day")
    dec = pd.Series([nyiso.decision_time_utc(d) for d in days], index=days, name="decision")
    blocks, used, ages = [], [], []
    da_post = clock.posting_table(da)
    rt_post = clock.posting_table(rt)
    for (frame, post, lags, mkt) in ((da, da_post, DA_LAGS, "da"), (rt, rt_post, RT_LAGS, "rt")):
        loc = frame[frame["name"] == LOC]
        for value in ("lbmp", "mcc"):
            mat = clock.local_hour_matrix(loc, value)
            for lag in lags:
                b, u, g = _lag_block(post, mat, days, dec, lag, f"{mkt}_{value}")
                blocks.append(b)
                used.append(u)
                ages.append(g)
    for zone in OTHER_ZONES:
        mat = clock.local_hour_matrix(da[da["name"] == zone], "lbmp")
        b, u, g = _lag_block(da_post, mat, days, dec, 1, f"da_{zone}")
        blocks.append(b)
        used.append(u)
        ages.append(g)
    lfb, lfu, lfg = _load_forecast(lf, days, dec)
    blocks.append(lfb)
    used.append(lfu)
    ages.append(lfg)
    blocks.append(_calendar(days))
    X = pd.concat(blocks, axis=1)
    ages = pd.concat(ages, axis=1)
    U = pd.concat(used, axis=1)
    for col in U.columns:
        clock.require_before(U[col], dec, f"feature {col}")
    y = _targets(da, rt, days)
    return Design(X=X, used_posted=U, decision=dec, y=y, fallback_age=ages)


def _targets(da: pd.DataFrame, rt: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    parts = []
    for mkt, frame in (("da", da), ("rt", rt)):
        loc = frame[(frame["name"] == LOC) & frame["day"].isin(days)]
        t = loc[["day", "ts_utc", "lbmp", "mcc", "posted_utc"]].rename(
            columns={"lbmp": f"{mkt}_lbmp", "mcc": f"{mkt}_mcc", "posted_utc": f"{mkt}_posted"})
        parts.append(t.set_index(["day", "ts_utc"]))
    y = pd.concat(parts, axis=1).reset_index()
    y["hour"] = y["ts_utc"].dt.tz_convert(nyiso.TZ).dt.hour
    y = y.rename(columns={"da_lbmp": "T1_da_lbmp", "da_mcc": "T2_da_mcc",
                          "rt_lbmp": "T3_rt_lbmp", "rt_mcc": "T4_rt_mcc"})
    return y.sort_values("ts_utc").reset_index(drop=True)
