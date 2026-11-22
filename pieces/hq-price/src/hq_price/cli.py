"""Command-line surface: every command prints one JSON document on stdout.

  hq-price fetch      --product P --start YYYY-MM --end YYYY-MM
  hq-price validate   --targets T1_da_lbmp,T2_da_mcc
  hq-price tag-check
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tomllib
from pathlib import Path

import pandas as pd

from pmcore import nyiso, runs

from . import features, monitor, replay, report, score, walkforward as wf
from . import models as M

REPO = Path(__file__).resolve().parents[4]
PLAN_FILES = ["docs/plan.md", "pieces/hq-price/plan.toml"]
TAG = "plan-v1"


def plan() -> dict:
    return tomllib.loads((REPO / "pieces/hq-price/plan.toml").read_text())


def data_dir(a) -> Path:
    return Path(a.data) if a.data else REPO / "data"


def fence(cfg) -> nyiso.Fence:
    return nyiso.Fence(pd.Timestamp(cfg["periods"]["fence_first_unfetched_day"]), gate=None)


def load(d: Path):
    return [nyiso.load_product(d / "raw", p, d / "cache") for p in ("damlbmp", "rtlbmp", "isolf")]


def cmd_fetch(a) -> dict:
    cfg = plan()
    log = nyiso.fetch(a.product, a.start, a.end, data_dir(a) / "raw", fence(cfg))
    return {"ok": True, "files": len(log), "fetched": sum(x["status"] == "fetched" for x in log)}


def cmd_tag_check(a) -> dict:
    return {"ok": True, **runs.tag_check(REPO, TAG, PLAN_FILES)}


def _by_year(f: pd.DataFrame) -> dict:
    return {int(y): score.point_scores(g) for y, g in f.groupby(f["day"].dt.year)}


def cmd_validate(a) -> dict:
    cfg = plan()
    d = data_dir(a)
    t0 = time.time()
    git0, tag0 = runs.git_state(REPO), runs.tag_check(REPO, TAG, PLAN_FILES)  # provenance as of the start
    da, rt, lf = load(d)
    p = cfg["periods"]
    days = pd.date_range("2016-01-15", p["held_out_first_day"], freq="D", inclusive="left")
    des = features.build(da, rt, lf, days)
    run_id = runs.new_run_id("validate")
    out_dir = d / "runs" / run_id
    out_dir.mkdir(parents=True)
    results = {}
    for target in a.targets.split(","):
        parts = []
        for fold in wf.folds(p["validation_first_month"], p["validation_last_month"]):
            reg = wf.registry(target)
            reg["M1_noLF"] = M.LEAR(with_lf=False)
            parts.append(wf.run_fold(des, target, fold, reg))
        f = pd.concat(parts, ignore_index=True)
        for m in ("M1", "M2"):
            f = score.add_intervals(f, m, cfg["intervals"]["level"], cfg["intervals"]["residual_days"])
        fpath = out_dir / f"{target}.parquet"
        f.to_parquet(fpath)
        r = {"scores": score.point_scores(f), "by_year": _by_year(f),
             "baseline": monitor.BASELINE[target],
             "versus_baseline": {m: score.compare(f, m, monitor.BASELINE[target]) for m in ("M1", "M2")},
             "versus_B0": {m: score.compare(f, m, "B0") for m in ("M1", "M2")},
             "m1_fallback_hours_by_fold": f.groupby("fold")["M1_fallback_hours"].first().to_dict(),
             "days_with_slot_older_than_3": int((des.fallback_age.loc[f["day"].unique()].max(axis=1) > 3).sum()),
             "M1_versus_M1_noLF": score.compare(f, "M1", "M1_noLF"),
             "intervals": {m: score.interval_scores(f, m) for m in ("M1", "M2")},
             "forecasts_sha256": runs.sha256_file(fpath)}
        if target.endswith("mcc"):
            r["prob_scores"] = score.prob_scores(f)
            r["P2_versus_P0"] = score.compare(f, "P2", "P0", kind="brier")
        results[target] = r
    rec = {"label": "validation (seen)", "kind": "validate", "targets": a.targets.split(","),
           "git": git0, "git_at_end": runs.git_state(REPO), "plan_tag": tag0,
           "versions": runs.versions(), "plan": cfg,
           "raw_manifest": (man := nyiso.manifest(d / "raw", ("damlbmp", "rtlbmp", "isolf"))),
           "raw_manifest_sha256": runs.hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest(),
           "results": results, "seconds": round(time.time() - t0, 1)}
    path = runs.write(REPO / "runs", run_id, rec)
    return {"ok": True, "run_id": run_id, "record": str(path.relative_to(REPO)),
            "mae": {t: {m: round(v["mae"], 3) for m, v in r["scores"].items() if not m.startswith("_")} for t, r in results.items()}}


def _prior(d: Path, run_id: str, targets: list[str], last_month: str | None = None) -> dict:
    rec = runs.read(REPO / "runs", run_id)
    if rec["label"] != "validation (seen)" or rec["kind"] != "validate":
        raise runs.RecordError(f"{run_id} is not a validation run")
    out = {}
    for t in targets:
        if t not in rec["results"]:
            raise runs.RecordError(f"{run_id} has no {t}")
        path = d / "runs" / run_id / f"{t}.parquet"
        if runs.sha256_file(path) != rec["results"][t]["forecasts_sha256"]:
            raise runs.RecordError(f"{path} does not match its record")
        f = pd.read_parquet(path)
        if last_month:
            f = f[f["fold"] <= last_month]
        out[t] = f.drop(columns=[c for c in f.columns if c.endswith(("_lo", "_hi"))])
    return out


def _replay_record(a, label: str, kind: str, first: str, last: str, prior_run: str, git_before: dict | None = None) -> dict:
    cfg = plan()
    d = data_dir(a)
    targets = a.targets.split(",")
    t0 = time.time()
    # provenance as of the start; a replay passes the state it checked clean before writing its own ledger entry
    git0, tag0 = git_before or runs.git_state(REPO), runs.tag_check(REPO, TAG, PLAN_FILES)
    prior = _prior(d, prior_run, targets, None if kind == "replay" else "2024-10")
    da, rt, lf = load(d)
    days = pd.date_range("2016-01-15", pd.Period(last).end_time.normalize(), freq="D")
    des = features.build(da, rt, lf, days)
    run_id = runs.new_run_id(kind)
    out_dir = d / "runs" / run_id
    out_dir.mkdir(parents=True)
    res = replay.run(des, cfg, targets, first, last, prior, out_dir)
    rec = {"label": label, "kind": kind, "period": [first, last], "prior_run": prior_run, "targets": targets,
           "git": git0, "git_at_end": runs.git_state(REPO), "plan_tag": tag0,
           "versions": runs.versions(), "plan": cfg,
           "raw_manifest": (man := nyiso.manifest(d / "raw", ("damlbmp", "rtlbmp", "isolf"))),
           "raw_manifest_sha256": runs.hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest(),
           **res, "seconds": round(time.time() - t0, 1)}
    path = runs.write(REPO / "runs", run_id, rec)
    beats = {k: v["beats_baseline"] for k, v in res["rule"].items()}
    return {"ok": True, "run_id": run_id, "record": str(path.relative_to(REPO)), "label": label, "beats_baseline": beats}


def cmd_rehearse(a) -> dict:
    """The replay's code path on the last validation year (2024-11..2025-10), earlier folds as prior."""
    return _replay_record(a, "validation (seen)", "rehearse", "2024-11", "2025-10", a.prior_run)


def cmd_replay(a) -> dict:
    cfg = plan()
    p = cfg["periods"]
    tc = runs.tag_check(REPO, TAG, PLAN_FILES)
    if not tc["match"]:
        raise replay.ReplayRefused(f"plan files differ from tag {TAG}")
    git_before = runs.git_state(REPO)
    if git_before["dirty"]:
        raise replay.ReplayRefused("working tree has uncommitted changes")
    entries = replay.check_ledger(REPO, a.departure)
    # every check that can fail runs before the ledger is written or anything is fetched (code review 1, B3)
    targets = a.targets.split(",")
    if sorted(targets) != sorted(cfg["targets"]["registered"]):
        raise replay.ReplayRefused(f"targets {targets} are not the registered set {cfg['targets']['registered']}")
    d = data_dir(a)
    for prod in ("damlbmp", "rtlbmp", "isolf"):
        if not any((d / "raw" / prod).glob("*.zip")):
            raise replay.ReplayRefused(f"no {prod} archives under {d / 'raw'}")
    _prior(d, a.prior_run, targets, None)  # the prior run exists and its forecasts match their record
    first, last = p["held_out_first_day"][:7], p["held_out_last_day"][:7]
    gate = replay.held_out_gate(REPO, TAG, PLAN_FILES)
    fence_h = nyiso.Fence(pd.Timestamp(p["fence_first_unfetched_day"]), gate=gate)
    commit = runs.git_state(REPO)["commit"]
    if a.departure:
        replay.write_departure(REPO, a.departure, commit)
    entry = {"status": "started", "utc": pd.Timestamp.now(tz="UTC").isoformat(), "commit": commit,
             "departure": a.departure, "targets": targets, "prior_run": a.prior_run}
    entries.append(entry)
    replay.ledger_path(REPO).write_text(json.dumps(entries, indent=1))
    for prod in ("damlbmp", "rtlbmp", "isolf"):
        nyiso.fetch(prod, first, last, d / "raw", fence_h, held_out=True)
    entry.update({"status": "fetched", "fetched_utc": pd.Timestamp.now(tz="UTC").isoformat()})
    replay.ledger_path(REPO).write_text(json.dumps(entries, indent=1))
    res = _replay_record(a, "held out", "replay", first, last, a.prior_run, git_before)
    entry.update({"status": "finished", "run_id": res["run_id"]})
    replay.ledger_path(REPO).write_text(json.dumps(entries, indent=1))
    return res


def cmd_derive(a) -> dict:
    """Scores derived from a validation run's saved forecasts (hash-checked): robustness (plan §9), outcome counts,
    the comparisons against B0. Refuses held-out runs: re-scoring the held-out year is the owner's ruling."""
    d = data_dir(a)
    src = runs.read(REPO / "runs", a.from_run)
    if src["label"] != "validation (seen)":
        raise replay.ReplayRefused(f"{a.from_run} is labelled {src['label']!r}; derive runs on validation only")
    git0 = runs.git_state(REPO)
    results = {}
    for t in src["targets"]:
        path = d / "runs" / a.from_run / f"{t}.parquet"
        if runs.sha256_file(path) != src["results"][t]["forecasts_sha256"]:
            raise runs.RecordError(f"{path} does not match its record")
        f = pd.read_parquet(path)
        r = {"scores": score.point_scores(f), "robustness": score.robustness(f, t),
             "intervals": {m: score.interval_scores(f, m) for m in ("M1", "M2")},
             "versus_B0": {m: score.compare(f, m, "B0") for m in ("M1", "M2")},
             "forecasts_sha256": src["results"][t]["forecasts_sha256"]}
        if t.endswith("mcc"):
            r["prob_scores"] = score.prob_scores(f)
            r["P2_versus_P0"] = score.compare(f, "P2", "P0", kind="brier")
        results[t] = r
    run_id = runs.new_run_id("derive")
    rec = {"label": "validation (seen)", "kind": "derive", "source_run": a.from_run, "targets": src["targets"],
           "git": git0, "versions": runs.versions(), "results": results}
    path = runs.write(REPO / "runs", run_id, rec)
    return {"ok": True, "run_id": run_id, "record": str(path.relative_to(REPO))}


def cmd_report(a) -> dict:
    files = report.write(REPO, a.validate_run, a.derived_run, a.rehearse_run, a.replay_run, a.departure_run)
    return {"ok": True, "files": files}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hq-price")
    ap.add_argument("--data", default=None, help="data directory (default: <repo>/data)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--product", required=True, choices=sorted(nyiso.PRODUCTS))
    f.add_argument("--start", required=True)
    f.add_argument("--end", required=True)
    sub.add_parser("tag-check")
    v = sub.add_parser("validate")
    v.add_argument("--targets", default="T1_da_lbmp,T2_da_mcc")
    for name in ("rehearse", "replay"):
        r = sub.add_parser(name)
        r.add_argument("--prior-run", required=True, help="run id of the validation run")
        r.add_argument("--targets", default="T1_da_lbmp,T2_da_mcc,T3_rt_lbmp,T4_rt_mcc")
        if name == "replay":
            r.add_argument("--departure", default=None, help="reason; required for any replay after the first")
    dv = sub.add_parser("derive")
    dv.add_argument("--from-run", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("--validate-run", required=True)
    rp.add_argument("--derived-run", required=True)
    rp.add_argument("--rehearse-run", required=True)
    rp.add_argument("--replay-run", required=True)
    rp.add_argument("--departure-run", default=None, help="a second replay recorded as a departure, shown beside the first")
    a = ap.parse_args(argv)
    try:
        res = {"fetch": cmd_fetch, "tag-check": cmd_tag_check, "validate": cmd_validate,
               "rehearse": cmd_rehearse, "replay": cmd_replay, "report": cmd_report, "derive": cmd_derive}[a.cmd](a)
    except (nyiso.FenceError, nyiso.ClockError, FileNotFoundError, runs.RecordError, replay.ReplayRefused,
            report.Untraceable) as e:
        print(json.dumps({"ok": False, "refused": str(e)}))
        return 2
    print(json.dumps(res, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
