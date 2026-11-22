"""The replay's whole code path on synthetic data: forecasts, intervals, rule, monitor, deal."""

import tomllib

import pandas as pd

from hq_price import cli, features, models, replay
from test_guards import _lf, _zone


def test_replay_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setitem(models.HGB, "max_iter", 5)  # code path only; the frozen settings are tested elsewhere
    days = pd.date_range("2023-12-01", "2024-06-30", freq="D")
    da, rt, lf = _zone(days, -14.5), _zone(days, 24.0), _lf(days)
    des = features.build(da, rt, lf, pd.date_range("2023-12-10", "2024-06-30", freq="D"))
    cfg = tomllib.loads((cli.REPO / "pieces/hq-price/plan.toml").read_text())
    cfg["intervals"]["min_residual_days"] = 20  # reach the interval and band code on a short history
    cfg["deal"]["min_band_days"] = 10
    targets = ["T1_da_lbmp", "T2_da_mcc", "T3_rt_lbmp", "T4_rt_mcc"]
    prior = {t: replay.forecasts(des, t, "2024-04", "2024-05") for t in targets}
    res = replay.run(des, cfg, targets, "2024-06", "2024-06", prior, tmp_path)
    assert set(res["rule"]) == {"M1:T1_da_lbmp", "M2:T1_da_lbmp", "M1:T2_da_mcc", "M2:T2_da_mcc", "P2:T2_da_mcc",
                                "M1:T3_rt_lbmp", "M2:T3_rt_lbmp", "M1:T4_rt_mcc", "M2:T4_rt_mcc", "P2:T4_rt_mcc"}
    assert res["results"]["T2_da_mcc"]["baseline"] == "Z"
    assert res["deal"]["summary"]["days"] > 15
    assert len(res["monitor"]) == 8
    assert res["results"]["T1_da_lbmp"]["intervals"]["M1"]["n_hours"] > 0
    assert "band_coverage" in res["deal"]["summary"]["M1"]
    from hq_price import report
    fake_val = {"run_id": "v", "label": "validation (seen)", "targets": targets, "plan_tag": {"match": True},
                "results": {t: {**res["results"][t], "by_year": {2024: res["results"][t]["scores"]}} for t in targets}}
    rp = {"run_id": "r", "label": "held out", "targets": targets, "plan_tag": {"match": True}, "period": ["2024-06", "2024-06"],
          "git": {"commit": "abc1234", "dirty": False}, **res}
    fake_der = {"run_id": "d", "label": "validation (seen)", "targets": targets, "results": res["results"]}
    for lang in ("fr", "en"):
        text = report.render(fake_val, fake_der, rp, rp, [{"status": "finished"}], False, lang)
        assert "`r`" in text and "`v`" in text and "`d`" in text
    # an absent day of real-time outcomes is disclosed, from the hour counts alone
    import copy
    gap = copy.deepcopy(rp)
    for m in gap["results"]["T3_rt_lbmp"]["by_month"].values():
        m["B0"]["n_hours"] -= 24
    assert set(report.gaps(gap)) == {"T3_rt_lbmp"}
    assert report.miscounted(gap) == () if "_outcomes" in gap["results"]["T3_rt_lbmp"]["scores"] else ("T3_rt_lbmp",)
    old = copy.deepcopy(gap)
    old["results"]["T3_rt_lbmp"]["scores"].pop("_outcomes", None)
    assert report.miscounted(old) == ("T3_rt_lbmp",)
    assert "¹" in report.render(fake_val, fake_der, rp, old, [], False, "en")  # old scoring: flagged
    fixed = report.render(fake_val, fake_der, rp, gap, [], False, "en")  # fixed scoring: disclosed, not flagged
    assert "¹" not in fixed and "hours with no outcome" in fixed
    # a departure is shown beside the registered replay, and only with a finished departure entry in the ledger
    dep = {**copy.deepcopy(rp), "run_id": "r2"}
    import pytest
    with pytest.raises(report.Untraceable):
        report.render(fake_val, fake_der, rp, gap, [{"run_id": "r2", "status": "finished", "departure": None}], False, "en", dep)
    text = report.render(fake_val, fake_der, rp, gap, [{"run_id": "r2", "status": "finished", "departure": "why"}], False, "en", dep)
    assert "Departure from the plan" in text and "`r2`" in text and "`r`" in text
    # the README charts come from the record alone, name the run, and refuse a missing value
    from hq_price import figures
    for lang in ("fr", "en"):
        for fn in (figures.monthly_mae, figures.monitor_states, figures.deal_by_month):
            svg = fn(rp, lang)
            assert svg.startswith("<svg") and "run r" in svg or "exécution r" in svg
    broken = copy.deepcopy(rp)
    broken["deal"].pop("by_month")
    with pytest.raises(report.Untraceable):
        figures.deal_by_month(broken, "en")


def test_validate_command_end_to_end(tmp_path, monkeypatch):
    import argparse
    import json
    import subprocess

    monkeypatch.setitem(models.HGB, "max_iter", 5)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                    "--allow-empty", "-m", "x"], check=True)
    cfg = tomllib.loads((cli.REPO / "pieces/hq-price/plan.toml").read_text())
    cfg["periods"].update(validation_first_month="2024-04", validation_last_month="2024-05",
                          held_out_first_day="2024-06-01")
    cfg["intervals"]["min_residual_days"] = 20
    days = pd.date_range("2015-12-01", "2024-06-30", freq="D")[-220:]
    data = (_zone(days, -14.5), _zone(days, 24.0), _lf(days))
    monkeypatch.setattr(cli, "plan", lambda: cfg)
    monkeypatch.setattr(cli, "load", lambda d: data)
    monkeypatch.setattr(cli, "REPO", tmp_path)
    monkeypatch.setattr(cli.nyiso, "manifest", lambda raw, prods: {})
    a = argparse.Namespace(data=str(tmp_path / "data"), targets="T1_da_lbmp,T2_da_mcc,T3_rt_lbmp,T4_rt_mcc")
    out = cli.cmd_validate(a)
    rec = json.loads((tmp_path / out["record"]).read_text())
    assert rec["label"] == "validation (seen)" and rec["git"]["commit"]
    assert set(rec["results"]) == {"T1_da_lbmp", "T2_da_mcc", "T3_rt_lbmp", "T4_rt_mcc"}
    from hq_price import report
    for lang in ("fr", "en"):
        text = report.seen_comparisons(rec, lang) + report.by_year_table(rec, "T1_da_lbmp", lang)
        assert rec["run_id"] in text
