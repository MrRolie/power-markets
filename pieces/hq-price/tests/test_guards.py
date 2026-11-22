"""Each lookahead guard, broken on purpose, fires."""

import numpy as np
import pandas as pd
import pytest

from pmcore import clock, nyiso
from hq_price import features, walkforward as wf

NAMES = ["H Q", "NORTH", "N.Y.C."]


def _zone(days, post_offset_h):
    rows = []
    rng = np.random.default_rng(0)
    for d in days:
        utc = pd.date_range(pd.Timestamp(d).tz_localize(nyiso.TZ), periods=24, freq="h").tz_convert("UTC")
        posted = pd.Timestamp(d).tz_localize(nyiso.TZ).tz_convert("UTC") + pd.Timedelta(hours=post_offset_h)
        for n in NAMES:
            rows.append(pd.DataFrame({"day": d, "ts_utc": utc, "name": n, "ptid": 1,
                                      "lbmp": rng.normal(30, 5, 24), "mcl": 0.0,
                                      "mcc": rng.choice([0.0, 2.0], 24), "posted_utc": posted}))
    return pd.concat(rows, ignore_index=True)


def _lf(days):
    rows = []
    for f in days:
        posted = pd.Timestamp(f).tz_localize(nyiso.TZ).tz_convert("UTC") - pd.Timedelta(hours=17)
        utc = pd.date_range(pd.Timestamp(f).tz_localize(nyiso.TZ), periods=48, freq="h").tz_convert("UTC")
        for a in features.LF_AREAS:
            rows.append(pd.DataFrame({"ts_utc": utc, "area": a, "mw": 1000.0, "issue_file_day": f, "posted_utc": posted}))
    return pd.concat(rows, ignore_index=True)


@pytest.fixture
def data():
    days = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    return _zone(days, -14.5), _zone(days, 24.0), _lf(days)


def test_design_builds_and_passes_guard(data):
    da, rt, lf = data
    des = features.build(da, rt, lf, pd.date_range("2024-01-15", "2024-03-31", freq="D"))
    assert des.X.notna().all().all()


def test_break_feature_posted_after_decision(data):
    da, rt, lf = data
    days = pd.date_range("2024-01-15", "2024-03-31", freq="D")
    dec = pd.Series([nyiso.decision_time_utc(d) for d in days], index=days)
    used = dec.copy()  # posted exactly at the decision time: not admitted
    with pytest.raises(clock.LookaheadError):
        clock.require_before(used, dec, "break")


def test_admission_falls_back_when_late(data):
    da, rt, lf = data
    late_day = pd.Timestamp("2024-02-10")
    da.loc[da["day"] == late_day, "posted_utc"] += pd.Timedelta(days=5)  # a corrected, re-posted file
    des = features.build(da, rt, lf, pd.date_range("2024-02-11", "2024-02-11", freq="D"))
    hq = da[(da["name"] == "H Q") & (da["day"] == late_day - pd.Timedelta(days=1))]
    assert des.X.loc["2024-02-11", "da_lbmp_l1_h00"] == pytest.approx(hq["lbmp"].iloc[0])


def test_break_training_label_after_fold_decision(data):
    da, rt, lf = data
    des = features.build(da, rt, lf, pd.date_range("2024-01-15", "2024-03-31", freq="D"))
    fold = wf.folds("2024-03", "2024-03")[0]
    X, y = wf.train_split(des, "T1_da_lbmp", fold)
    assert y["day"].max() <= fold.first - pd.Timedelta(days=1)
    X, y = wf.train_split(des, "T3_rt_lbmp", fold)
    assert y["day"].max() <= fold.first - pd.Timedelta(days=2)
    # break: claim a label of the fold's first day was posted long before; the day-after-fold check fires
    des.y.loc[des.y["day"] == fold.first, "da_posted"] = pd.Timestamp("2000-01-01", tz="UTC")
    with pytest.raises(clock.LookaheadError):
        wf.train_split(des, "T1_da_lbmp", fold)
