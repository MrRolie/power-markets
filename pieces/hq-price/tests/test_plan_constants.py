"""The code's constants equal the frozen values of pieces/hq-price/plan.toml (tag plan-v1)."""

import tomllib
from datetime import date
from pathlib import Path

import pandas as pd

from pmcore import clock, nyiso
from hq_price import cli, features, models, monitor, nerc, walkforward

PLAN = tomllib.loads((Path(cli.REPO) / "pieces/hq-price/plan.toml").read_text())


def test_timing():
    t = PLAN["timing"]
    assert nyiso.TZ == clock.TZ == t["timezone"]
    assert clock.MARGIN == pd.Timedelta(minutes=t["admission_margin_minutes"])
    assert nyiso.decision_time_utc("2025-07-02").tz_convert(t["timezone"]).hour == t["decision_hour_local_day_before"]


def test_features():
    f = PLAN["features"]
    assert list(features.DA_LAGS) == f["da_lags_days"]
    assert list(features.RT_LAGS) == f["rt_lags_days"]
    assert list(features.OTHER_ZONES) == f["other_zones"]
    assert list(features.LF_AREAS) == f["load_forecast_areas"]
    assert models.MCC_NONZERO == PLAN["targets"]["mcc_nonzero_abs"]


def test_feature_counts():
    cols = ([f"da_lbmp_l{k}_h{h:02d}" for k in (1, 2, 3, 7) for h in range(24)]
            + [f"da_mcc_l{k}_h{h:02d}" for k in (1, 2, 3, 7) for h in range(24)]
            + [f"rt_lbmp_l{k}_h{h:02d}" for k in (2, 3, 4, 7) for h in range(24)]
            + [f"rt_mcc_l{k}_h{h:02d}" for k in (2, 3, 4, 7) for h in range(24)]
            + [f"da_{z}_l1_h{h:02d}" for z in ("NORTH", "N.Y.C.") for h in range(24)]
            + [f"lf_{a}_h{h:02d}" for a in ("NYISO", "North", "Capitl") for h in range(24)]
            + [f"dow_{d}" for d in range(7)] + ["holiday"])
    X = pd.DataFrame(columns=cols)
    f = PLAN["features"]
    for t, n in (("T1_da_lbmp", f["n_features_T1_T2"]), ("T2_da_mcc", f["n_features_T1_T2"]),
                 ("T3_rt_lbmp", f["n_features_T3_T4"]), ("T4_rt_mcc", f["n_features_T3_T4"])):
        p, o = models.feature_columns(X, t)
        assert len(p) + len(o) == n, t


def test_models_and_baselines():
    m = PLAN["models"]
    assert models.HGB == {k: m["M2"][k] for k in ("max_iter", "learning_rate", "max_leaf_nodes", "min_samples_leaf",
                                                    "l2_regularization", "random_state")} | {"early_stopping": False}
    assert models.LEAR().window_days == m["M1"]["window_days"]
    assert str(models.GBM().train_from.date()) == m["M2"]["train_from"]
    for t in ("T1_da_lbmp", "T2_da_mcc", "T3_rt_lbmp", "T4_rt_mcc"):
        assert monitor.BASELINE[t] == m[f"baseline_{t[:2]}"]
        assert m[f"baseline_{t[:2]}"] in walkforward.registry(t)


def test_nerc_holidays():
    assert nerc.nerc_holidays(2022) == {date(2022, 1, 1), date(2022, 5, 30), date(2022, 7, 4), date(2022, 9, 5),
                                        date(2022, 11, 24), date(2022, 12, 26)}  # Christmas on Sunday -> Monday
    assert date(2021, 12, 24) not in nerc.nerc_holidays(2021)  # Saturday Christmas is not moved
    assert date(2021, 12, 25) in nerc.nerc_holidays(2021)


def test_periods():
    p = PLAN["periods"]
    assert p["validation_first_month"] == "2022-11" and p["held_out_first_day"] == p["fence_first_unfetched_day"]


def test_defaults_bound_to_plan():
    import inspect

    from hq_price import deal, score
    assert inspect.signature(score.compare).parameters["lags"].default == PLAN["rule"]["lags"]
    assert inspect.signature(models.prob_climatology).parameters["window_days"].default == PLAN["models"]["P0"]["window_days"]
    sig = inspect.signature(score.add_intervals).parameters
    assert sig["level"].default == PLAN["intervals"]["level"]
    assert sig["residual_days"].default == PLAN["intervals"]["residual_days"]
    assert sig["min_days"].default == PLAN["intervals"]["min_residual_days"]
    assert inspect.signature(deal.add_bands).parameters["min_days"].default == PLAN["deal"]["min_band_days"]
    assert 'criterion="aic"' in inspect.getsource(models.LEAR.fit)
