"""The held-out replay (docs/plan.md §3, §6–§8, §10) and its rehearsal.

`run` scores every model of every target over a period of monthly folds, against the forecasts of an earlier
validation run for everything that needs earlier days (intervals, deal bands, monitor thresholds). The
rehearsal uses the last validation year as the period and the years before it as the earlier run; it touches no
held-out data. The held-out replay is gated: tag match, a ledger refusing a second replay, then the fetch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pmcore import runs, stats

from . import deal, monitor, score, walkforward as wf
from . import models as M

FAMILY_MODELS = {"T1_da_lbmp": ("M1", "M2"), "T2_da_mcc": ("M1", "M2", "P2"),
                 "T3_rt_lbmp": ("M1", "M2"), "T4_rt_mcc": ("M1", "M2", "P2")}


class ReplayRefused(RuntimeError):
    pass


def ledger_path(repo: Path) -> Path:
    return repo / "docs" / "replay-ledger.json"


def check_ledger(repo: Path, departure: str | None) -> list:
    p = ledger_path(repo)
    entries = json.loads(p.read_text()) if p.exists() else []
    touched = [e for e in entries if e.get("status") in ("fetched", "finished")]
    if touched and not departure:
        raise ReplayRefused(f"{len(touched)} replay(s) already fetched or finished the held-out year; another needs --departure")
    return entries


def write_departure(repo: Path, reason: str, commit: str) -> None:
    """Plan preamble and §10: a departure is recorded in docs/departures.md."""
    p = repo / "docs" / "departures.md"
    head = "# Departures from plan-v1\n\nEach entry: UTC time, commit, reason. Allowed only by the owner.\n\n"
    text = p.read_text() if p.exists() else head
    stamp = pd.Timestamp.now(tz="UTC").isoformat()
    p.write_text(text + f"- {stamp}, commit `{commit[:12]}`: {reason}\n")


def forecasts(des, target: str, first_month: str, last_month: str) -> pd.DataFrame:
    parts = []
    for fold in wf.folds(first_month, last_month):
        reg = wf.registry(target)
        reg["M1_noLF"] = M.LEAR(with_lf=False)
        parts.append(wf.run_fold(des, target, fold, reg))
    return pd.concat(parts, ignore_index=True)


def _with_intervals(prior: pd.DataFrame, cur: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    both = pd.concat([prior.assign(_period="prior"), cur.assign(_period="current")], ignore_index=True)
    for m in ("M1", "M2"):
        both = score.add_intervals(both, m, cfg["intervals"]["level"], cfg["intervals"]["residual_days"],
                                   cfg["intervals"]["min_residual_days"])
    return both[both["_period"] == "current"].drop(columns="_period")


def rule(results: dict, cfg: dict) -> dict:
    """The rule of plan §6 over the family of pairs that ran."""
    pairs, pvals = {}, {}
    for target, r in results.items():
        for m in FAMILY_MODELS[target]:
            if m == "P2":
                if "P2_versus_P0" not in r:
                    continue
                c, loss_m, loss_b = r["P2_versus_P0"], r["prob_scores"]["P2"]["brier"], r["prob_scores"]["P0"]["brier"]
            else:
                c = r["versus_baseline"][m]
                loss_m, loss_b = r["scores"][m]["mae"], r["scores"][r["baseline"]]["mae"]
            key = f"{m}:{target}"
            pairs[key] = {"loss_model": loss_m, "loss_baseline": loss_b, "lower": loss_m < loss_b, "dm": c}
            pvals[key] = c["p_one_sided"]
    h = stats.holm(pvals, cfg["rule"]["alpha"])
    for k in pairs:
        pairs[k]["holm"] = h[k]
        pairs[k]["beats_baseline"] = bool(pairs[k]["lower"] and h[k]["rejects"])
    return pairs


def run(des, cfg: dict, targets: list[str], first_month: str, last_month: str, prior: dict[str, pd.DataFrame],
        out_dir: Path) -> dict:
    results, frames = {}, {}
    for target in targets:
        cur = forecasts(des, target, first_month, last_month)
        cur = _with_intervals(prior[target], cur, cfg)
        cur.to_parquet(out_dir / f"{target}.parquet")
        frames[target] = cur
        base = monitor.BASELINE[target]
        r = {"baseline": base, "scores": score.point_scores(cur),
             "by_month": {k: score.point_scores(g) for k, g in cur.groupby("fold")},
             "versus_baseline": {m: score.compare(cur, m, base) for m in ("M1", "M2")},
             "versus_B0": {m: score.compare(cur, m, "B0") for m in ("M1", "M2")},
             "M1_versus_M1_noLF": score.compare(cur, "M1", "M1_noLF"),
             "robustness": score.robustness(cur, target),
             "intervals": {m: score.interval_scores(cur, m) for m in ("M1", "M2")},
             "m1_fallback_hours_by_fold": cur.groupby("fold")["M1_fallback_hours"].first().to_dict(),
             "forecasts_sha256": runs.sha256_file(out_dir / f"{target}.parquet")}
        if target.endswith("mcc"):
            r["prob_scores"] = score.prob_scores(cur)
            r["P2_versus_P0"] = score.compare(cur, "P2", "P0", kind="brier")
        results[target] = r
    # monitor: thresholds from the earlier run's days, states over the period
    mon = {}
    regime_src = {"T1_da_lbmp": "T2_da_mcc", "T2_da_mcc": "T2_da_mcc", "T3_rt_lbmp": "T3_rt_lbmp", "T4_rt_mcc": "T3_rt_lbmp"}
    for target in targets:
        age = data_flag(des, target, cfg["monitor"]["max_fallback_age_days"])
        src = regime_src[target]
        if src not in frames:
            continue
        both_src = pd.concat([prior[src], frames[src]], ignore_index=True)
        both = pd.concat([prior[target], frames[target]], ignore_index=True)
        for m in ("M1", "M2"):
            st = monitor.statistics(both, m, monitor.BASELINE[target], cfg["monitor"]["window_days"], both_src)
            prior_days = prior[target]["day"].unique()
            th = monitor.thresholds(st.loc[st.index.isin(prior_days)], cfg["monitor"])
            col = monitor.REGIME[target]
            s_all = monitor.states(st, th, col, age, cfg["monitor"]["stop_after_consecutive_days"])  # one run across the boundary
            s_prior = s_all.loc[s_all.index.isin(prior_days)]
            s_cur = s_all.loc[~s_all.index.isin(prior_days)]
            mon[f"{m}:{target}"] = {
                "thresholds": th,
                "states_period": s_cur["state"].value_counts().to_dict(),
                "states_prior_in_sample": s_prior["state"].value_counts().to_dict(),
                "first_stop_day": str(s_cur.index[s_cur["state"] == "stop trusting"].min()) if (s_cur["state"] == "stop trusting").any() else None,
                "zero_baseline_days": int((st.loc[~st.index.isin(prior_days), "rel_mae"].isna()
                                           & st.loc[~st.index.isin(prior_days), "bias"].notna()).sum()),
                "data_signal_days": int(s_cur["sig_data"].sum()),
                "daily": s_cur.reset_index().astype({"day": str}).to_dict(orient="list"),
            }
    # the deal, on T1 with the congestion part from T2
    dl = None
    if "T1_da_lbmp" in frames and "T2_da_mcc" in frames:
        v_prior = deal.daily_values(prior["T1_da_lbmp"], prior["T2_da_mcc"], cfg["deal"])
        v_cur = deal.daily_values(frames["T1_da_lbmp"], frames["T2_da_mcc"], cfg["deal"])
        v = pd.concat([v_prior.assign(_p="prior"), v_cur.assign(_p="current")])
        for m in ("B0", "M1", "M2"):
            v = deal.add_bands(v, m, 0.90, cfg["intervals"]["residual_days"], cfg["deal"]["min_band_days"])
        v = v[v["_p"] == "current"].drop(columns="_p")
        dl = {"summary": deal.summary(v), "congestion": deal.congestion_summary(v),
              "by_month": {str(k): deal.summary(g) for k, g in v.groupby(v.index.to_period("M"))}}
    return {"results": results, "rule": rule(results, cfg), "monitor": mon, "deal": dl}


FEATURE_PREFIXES = {"T1_da_lbmp": ("da_lbmp", "da_NORTH", "da_N.Y.C.", "lf"),
                   "T2_da_mcc": ("da_mcc", "da_NORTH", "da_N.Y.C.", "lf"),
                   "T3_rt_lbmp": ("rt_lbmp", "da_lbmp", "da_NORTH", "da_N.Y.C.", "lf"),
                   "T4_rt_mcc": ("rt_mcc", "da_mcc", "da_NORTH", "da_N.Y.C.", "lf")}


def data_flag(des, target: str, max_age_days: int) -> pd.Series:
    """Plan §8 data signal, from this target's own inputs: a slot filled from a day more than `max_age_days`
    older than its own, or an input missing."""
    pre = FEATURE_PREFIXES[target]
    age = des.fallback_age[[c for c in des.fallback_age.columns if c.startswith(pre)]]
    xcols = [c for c in des.X.columns if c.startswith(pre)]
    return (age > max_age_days).any(axis=1) | age.isna().any(axis=1) | des.X[xcols].isna().any(axis=1)


def held_out_gate(repo: Path, tag: str, files: list[str]):
    def gate():
        tc = runs.tag_check(repo, tag, files)
        if not tc["match"]:
            raise ReplayRefused(f"plan files differ from tag {tag}: {tc}")
    return gate

