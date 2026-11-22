"""Admission by posting time: what a forecaster held at a decision time.

A file (one operating day of one product) is admitted for a decision only if its posting time is at least
MARGIN before the decision time (docs/plan.md §2). A lag day whose file is not admitted falls back to the latest earlier day
whose file is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TZ = "America/New_York"
MARGIN = pd.Timedelta(minutes=60)


class LookaheadError(RuntimeError):
    """An input posted at or after the decision time reached a fit, a forecast or a score."""


def posting_table(df: pd.DataFrame, day_col: str = "day") -> pd.Series:
    """One posting time per file day (the latest, if a day's rows disagree)."""
    return df.groupby(day_col)["posted_utc"].max().sort_index()


def admitted_day(posted: pd.Series, lag_day: pd.Timestamp, decision: pd.Timestamp) -> pd.Timestamp | None:
    """Latest file day <= lag_day whose posting time is before the decision time."""
    cand = posted.loc[:lag_day]
    ok = cand[cand <= decision - MARGIN]
    return None if ok.empty else ok.index[-1]


def admitted_days(posted: pd.Series, lag_days: pd.Series, decisions: pd.Series) -> pd.Series:
    """Vectorised `admitted_day` over aligned series of lag days and decision times."""
    days = posted.index.to_numpy()
    post = _utc_np(posted)
    margin = MARGIN.to_timedelta64()
    out = []
    for lag, dec in zip(lag_days.to_numpy(), _utc_np(decisions)):
        dec = dec - margin
        i = np.searchsorted(days, lag, side="right")
        j = i - 1
        while j >= 0 and not post[j] <= dec:
            j -= 1
        out.append(days[j] if j >= 0 else np.datetime64("NaT"))
    return pd.Series(pd.to_datetime(out), index=lag_days.index)


def _utc_np(s: pd.Series) -> np.ndarray:
    """A tz-aware series as naive-UTC numpy datetimes (naive series pass through)."""
    if isinstance(s.dtype, pd.DatetimeTZDtype):
        return s.dt.tz_convert(None).to_numpy()
    return s.to_numpy()


def require_before(used_posted: pd.Series, decisions: pd.Series, what: str) -> None:
    """Refuse if any used posting time is not at least MARGIN before its row's decision time."""
    bad = ~(used_posted <= decisions - MARGIN)
    bad &= used_posted.notna()
    if bad.any():
        first = used_posted.index[bad.values][0]
        raise LookaheadError(f"{what}: {int(bad.sum())} rows use inputs posted at or after the decision (first {first})")


def local_hour_matrix(df: pd.DataFrame, value: str, day_col: str | list[str] = "day") -> pd.DataFrame:
    """Day x local hour-beginning (0..23). The repeated autumn hour is averaged; the missing spring hour
    takes the hour before it."""
    hour = df["ts_utc"].dt.tz_convert(TZ).dt.hour
    keys = list(day_col) if isinstance(day_col, (list, tuple)) else [day_col]
    m = df.assign(h=hour.values).groupby(keys + ["h"])[value].mean().unstack("h")
    m = m.reindex(columns=range(24))
    return m.ffill(axis=1)
