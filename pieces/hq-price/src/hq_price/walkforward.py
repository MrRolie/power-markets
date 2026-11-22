"""Monthly walk-forward (docs/plan.md §4): refit at each fold start on samples admitted at that decision time."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from pmcore import clock

from . import models as M
from .features import Design

POSTED = {"T1_da_lbmp": "da_posted", "T2_da_mcc": "da_posted", "T3_rt_lbmp": "rt_posted", "T4_rt_mcc": "rt_posted"}


@dataclass(frozen=True)
class Fold:
    month: pd.Period

    @property
    def first(self) -> pd.Timestamp:
        return self.month.start_time

    @property
    def last(self) -> pd.Timestamp:
        return self.month.end_time.normalize()


def folds(first_month: str, last_month: str) -> list[Fold]:
    return [Fold(p) for p in pd.period_range(first_month, last_month, freq="M")]


def registry(target: str) -> dict:
    reg = {"B0": M.Naive(0), "B1": M.Naive(7), "M1": M.LEAR(), "M2": M.GBM()}
    if target.endswith("mcc"):
        reg["Z"] = M.Zero()
    return reg


def train_split(des: Design, target: str, fold: Fold) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Training samples: every hour of a day whose target was posted before the fold's first decision."""
    dec0 = des.decision.loc[fold.first]
    posted = des.y.groupby("day")[POSTED[target]].max()
    ok_days = posted.index[posted <= dec0 - clock.MARGIN]
    y = des.y[des.y["day"].isin(ok_days) & des.y[target].notna()]
    X = des.X.loc[des.X.index.isin(ok_days)]
    # the purge, as a refusal: no training label posted at or after the decision; no training day after the fold
    clock.require_before(y.groupby("day")[POSTED[target]].max(), pd.Series(dec0, index=ok_days), "training label")
    if len(X) and X.index.max() >= fold.first:
        raise clock.LookaheadError(f"training day {X.index.max().date()} not before fold {fold.month}")
    return X, y


def run_fold(des: Design, target: str, fold: Fold, models: dict | None = None) -> pd.DataFrame:
    X, y = train_split(des, target, fold)
    test_days = des.X.index[(des.X.index >= fold.first) & (des.X.index <= fold.last)]
    rows = des.y[des.y["day"].isin(test_days)].copy()
    out = rows[["day", "ts_utc", "hour", target, POSTED[target]]].rename(columns={target: "y", POSTED[target]: "y_posted"})
    for name, model in (models or registry(target)).items():
        model.fit(X, y, target)
        out[name] = model.predict(des.X, rows).values
        if hasattr(model, "n_fallback_hours"):
            out[f"{name}_fallback_hours"] = model.n_fallback_hours
    if target.endswith("mcc"):
        days = pd.DatetimeIndex(test_days)
        out["P0"] = M.prob_climatology(des.y, target, POSTED[target], days, des.decision, rows).values
        out["P2"] = M.ProbGBM().fit(X, y, target).predict(des.X, rows).values
    out["fold"] = str(fold.month)
    out["target"] = target
    out["decision"] = des.decision.reindex(out["day"]).set_axis(out.index)  # keeps UTC
    return out
