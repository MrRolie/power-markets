import numpy as np
import pandas as pd

from hq_price import deal, monitor


def _forecasts(n_days=120, jump_day=80):
    days = pd.date_range("2024-01-01", periods=n_days, freq="D")
    rows = []
    rng = np.random.default_rng(0)
    for i, d in enumerate(days):
        dec = pd.Timestamp(d - pd.Timedelta(days=1)).tz_localize("UTC") + pd.Timedelta(hours=10)
        posted = pd.Timestamp(d).tz_localize("UTC") + pd.Timedelta(hours=23)
        y = rng.normal(30, 5, 24)
        err = 1.0 if i < jump_day else 20.0  # the model breaks at jump_day
        rows.append(pd.DataFrame({"day": d, "hour": range(24), "y": y, "B0": y + rng.normal(0, 3, 24),
                                  "M1": y + rng.normal(0, err, 24), "y_posted": posted, "decision": dec,
                                  "fold": str(d.to_period("M"))}))
    return pd.concat(rows, ignore_index=True)


CFG = {"bias_band": [0.025, 0.975], "regime_band": [0.01, 0.99], "rel_mae_quantile": 0.95}


def test_monitor_uses_only_errors_posted_before_decision():
    f = _forecasts()
    s = monitor.statistics(f, "M1", window=28)
    # the break at day 80 cannot show on day 80 or 81: those errors are not posted at their decisions
    assert s.loc["2024-03-21", "rel_mae"] == s.loc["2024-03-21", "rel_mae"]  # defined
    before = s.loc[: pd.Timestamp("2024-03-21") + pd.Timedelta(days=1), "rel_mae"].max()
    assert before < 1.0
    assert s["rel_mae"].iloc[-1] > 3.0


def test_monitor_says_stop_after_break():
    f = _forecasts()
    s = monitor.statistics(f, "M1", window=28)
    th = monitor.thresholds(s.loc[:"2024-03-15"], CFG)
    st = monitor.states(s, th, "share_le0")
    assert (st.loc[:"2024-01-28", "state"] == "no verdict (window not full)").all()
    assert st["state"].iloc[-1] == "stop trusting"


def test_deal_hours_are_weekday_non_holiday_block():
    f = _forecasts(n_days=10)
    sel = deal.deal_hours(f, {"hours_beginning": list(range(7, 23))})
    picked = f[sel]
    assert set(picked["hour"]) == set(range(7, 23))
    assert (pd.DatetimeIndex(picked["day"]).day_of_week < 5).all()
    assert pd.Timestamp("2024-01-01") not in set(picked["day"])  # New Year's Day


def test_deal_congestion_sign():
    f = _forecasts(n_days=10)
    m = f.copy()
    m["y"] = 1.0  # posted congestion of +1 everywhere
    m["B0"] = m["M1"] = m["M2"] = 1.0
    f["M2"] = f["M1"]
    v = deal.daily_values(f, m, {"mw": 50, "hours_beginning": list(range(7, 23))})
    assert (v["congestion_settled"] == -50 * 16).all()


def test_p0_skips_a_day_posted_late():
    from hq_price import models
    days = pd.date_range("2024-01-01", periods=40, freq="D")
    rows = []
    for d in days:
        posted = pd.Timestamp(d).tz_localize("UTC") + pd.Timedelta(hours=10)
        rows.append(pd.DataFrame({"day": d, "hour": range(24), "T2_da_mcc": 0.0, "da_posted": posted}))
    y = pd.concat(rows, ignore_index=True)
    late = pd.Timestamp("2024-02-05")
    y.loc[y["day"] == late, "T2_da_mcc"] = 5.0
    y.loc[y["day"] == late, "da_posted"] += pd.Timedelta(days=30)  # posted long after
    target_days = pd.DatetimeIndex([pd.Timestamp("2024-02-09")])
    dec = pd.Series([pd.Timestamp("2024-02-08 10:00", tz="UTC")], index=target_days)
    r = pd.DataFrame({"day": target_days.repeat(24), "hour": list(range(24))})
    p = models.prob_climatology(y, "T2_da_mcc", "da_posted", target_days, dec, r)
    assert (p == 0).all()


def test_lear_missing_input_gets_training_median():
    from hq_price import models
    days = pd.date_range("2024-01-01", periods=60, freq="D")
    rng = np.random.default_rng(0)
    cols = [f"da_lbmp_l{k}_h{h:02d}" for k in (1, 2, 3, 7) for h in range(24)] + [f"dow_{d}" for d in range(7)] + ["holiday"]
    X = pd.DataFrame(rng.normal(30, 5, (60, len(cols))), index=days, columns=cols)
    y = pd.DataFrame({"day": days.repeat(24), "hour": list(range(24)) * 60, "T1_da_lbmp": rng.normal(30, 5, 60 * 24)})
    m = models.LEAR(with_lf=False).fit(X, y, "T1_da_lbmp")
    X2 = X.copy()
    X2.iloc[-1, 0] = np.nan
    rows = y[y["day"] == days[-1]]
    out = m.predict(X2, rows)
    assert out.notna().all() and out.iloc[0] == m.fallback[0]


def test_missing_outcome_is_neither_hit_nor_event():
    from hq_price import score
    f = pd.DataFrame({"day": pd.Timestamp("2024-01-01"), "hour": [0, 1, 2, 3], "y": [0.0, 1.0, np.nan, np.nan],
                      "P0": 0.5, "P2": 0.5, "M1": 0.0, "M1_lo": -0.1, "M1_hi": 0.1})
    p = score.prob_scores(f)
    assert p["P2"]["n_hours"] == 2 and abs(p["P2"]["brier"] - 0.25) < 1e-12 and p["P2"]["event_rate"] == 0.5
    iv = score.interval_scores(f, "M1")
    assert iv["n_hours"] == 2 and iv["coverage"] == 0.5
    assert score.point_scores(f, ("M1",))["_outcomes"]["missing_hours"] == 2


def test_monitor_survives_a_block_of_missing_outcomes():
    f = _forecasts()
    block = f["day"].between("2024-02-19", "2024-02-24")
    f.loc[block, "y"] = np.nan
    f.loc[block, "y_posted"] = pd.NaT
    s = monitor.statistics(f, "M1", window=28)
    after = s.loc["2024-02-20":"2024-03-20"]
    assert after[["rel_mae", "bias", "share_le0", "share_nonzero_mcc"]].notna().all().all()
    th = monitor.thresholds(s.loc[:"2024-02-15"], CFG)
    flag = pd.Series(s.index.isin(pd.date_range("2024-02-21", "2024-02-26")), index=s.index)
    st = monitor.states(s, th, "share_le0", data_flag=flag)
    assert (st.loc["2024-02-21":"2024-02-26", "state"] == "stop trusting").all()
    assert (st.loc["2024-02-27":"2024-03-15", "state"] != "no verdict (window not full)").all()


def test_regime_shares_skip_missing_outcomes():
    f = _forecasts(n_days=3)
    f.loc[f["day"] == "2024-01-02", "y"] = np.nan
    f.loc[(f["day"] == "2024-01-03") & (f["hour"] < 12), "y"] = np.nan
    f.loc[(f["day"] == "2024-01-03") & (f["hour"] >= 12) & (f["hour"] < 18), "y"] = -1.0
    d = monitor._daily(f, "M1", "B0")
    assert d.loc["2024-01-02", ["nz", "le0"]].isna().all()
    assert d.loc["2024-01-03", "le0"] == 0.5  # 6 of the 12 hours with an outcome, not 6 of 24
