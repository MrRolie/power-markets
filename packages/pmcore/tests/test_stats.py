import numpy as np
import pytest

from pmcore import stats


def test_dm_detects_a_better_model_and_not_a_worse_one():
    rng = np.random.default_rng(0)
    base = rng.gamma(2.0, 2.0, 400)
    better = base - 0.5 + rng.normal(0, 0.5, 400)
    worse = base + 0.5 + rng.normal(0, 0.5, 400)
    assert stats.diebold_mariano(better, base)["p_one_sided"] < 0.001
    assert stats.diebold_mariano(worse, base)["p_one_sided"] > 0.99


def test_dm_equal_losses_not_rejected_often():
    rng = np.random.default_rng(1)
    rej = 0
    for _ in range(200):
        a, b = rng.normal(5, 1, 300), rng.normal(5, 1, 300)
        rej += stats.diebold_mariano(a, b)["p_one_sided"] < 0.05
    assert rej / 200 < 0.10


def test_identical_losses_do_not_reject():
    a = np.ones(100)
    r = stats.diebold_mariano(a, a)
    assert r["p_one_sided"] == 1.0


def test_newey_west_matches_iid_variance_at_zero_lags():
    d = np.arange(10.0)
    assert stats.newey_west_var_of_mean(d, 0) == pytest.approx(d.var() / d.size)


def test_dm_refuses_too_few_periods():
    with pytest.raises(ValueError):
        stats.diebold_mariano(np.ones(10), np.zeros(10), lags=7)


def test_holm_steps_down():
    r = stats.holm({"a": 0.01, "b": 0.02, "c": 0.04}, alpha=0.05)
    assert r["a"]["rejects"] and r["b"]["rejects"] and r["c"]["rejects"]
    r = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03}, alpha=0.05)
    assert r["a"]["rejects"] and not r["c"]["rejects"] and not r["b"]["rejects"]
    assert r["a"]["p_holm"] == pytest.approx(0.03)
