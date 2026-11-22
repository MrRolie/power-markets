import json

import pytest

from hq_price import replay


def test_second_replay_refused_without_departure(tmp_path):
    (tmp_path / "docs").mkdir()
    replay.ledger_path(tmp_path).write_text(json.dumps([{"status": "finished", "run_id": "x"}]))
    with pytest.raises(replay.ReplayRefused):
        replay.check_ledger(tmp_path, None)
    assert len(replay.check_ledger(tmp_path, "owner allowed: reason")) == 1


def test_started_but_not_fetched_may_run_again(tmp_path):
    (tmp_path / "docs").mkdir()
    replay.ledger_path(tmp_path).write_text(json.dumps([{"status": "started"}]))
    assert replay.check_ledger(tmp_path, None)


def test_fetched_but_unfinished_refuses_without_departure(tmp_path):
    (tmp_path / "docs").mkdir()
    replay.ledger_path(tmp_path).write_text(json.dumps([{"status": "fetched"}]))
    with pytest.raises(replay.ReplayRefused):
        replay.check_ledger(tmp_path, None)


def test_gate_refuses_when_tag_absent(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    gate = replay.held_out_gate(tmp_path, "plan-v1", ["docs/plan.md"])
    with pytest.raises(replay.ReplayRefused):
        gate()


def _tagged_repo(tmp_path):
    import shutil
    import subprocess

    from hq_price import cli
    (tmp_path / "docs").mkdir()
    (tmp_path / "pieces/hq-price").mkdir(parents=True)
    shutil.copy(cli.REPO / "docs/plan.md", tmp_path / "docs/plan.md")
    shutil.copy(cli.REPO / "pieces/hq-price/plan.toml", tmp_path / "pieces/hq-price/plan.toml")
    g = ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(g + ["add", "-A"], check=True)
    subprocess.run(g + ["commit", "-q", "-m", "x"], check=True)
    subprocess.run(g + ["tag", "plan-v1"], check=True)
    return tmp_path


def test_cmd_replay_refuses_before_writing_or_fetching(tmp_path, monkeypatch):
    import argparse

    from hq_price import cli
    repo = _tagged_repo(tmp_path)
    monkeypatch.setattr(cli, "REPO", repo)
    calls = []
    monkeypatch.setattr(cli.nyiso, "fetch", lambda *a, **k: calls.append(a))
    all4 = "T1_da_lbmp,T2_da_mcc,T3_rt_lbmp,T4_rt_mcc"
    for targets, prior in (("T1_da_lbmp,T2_da_mcc", "x"), (all4, "no-such-run")):
        a = argparse.Namespace(data=str(repo / "data"), targets=targets, prior_run=prior, departure=None)
        with pytest.raises((replay.ReplayRefused, FileNotFoundError, cli.runs.RecordError)):
            cli.cmd_replay(a)
    assert calls == [] and not replay.ledger_path(repo).exists()


def test_cmd_replay_marks_fetched_and_refuses_a_second_touch(tmp_path, monkeypatch):
    import argparse

    from hq_price import cli
    repo = _tagged_repo(tmp_path)
    for prod in ("damlbmp", "rtlbmp", "isolf"):
        (repo / "data/raw" / prod).mkdir(parents=True)
        (repo / "data/raw" / prod / "x.zip").write_bytes(b"x")
    monkeypatch.setattr(cli, "REPO", repo)
    monkeypatch.setattr(cli, "_prior", lambda *a, **k: {})
    gates = []
    monkeypatch.setattr(cli.nyiso, "fetch", lambda prod, f, l, raw, fence, held_out: gates.append(fence.gate()))

    def crash(*a, **k):
        raise RuntimeError("crash after the fetch")
    monkeypatch.setattr(cli, "_replay_record", crash)
    a = argparse.Namespace(data=str(repo / "data"), targets="T1_da_lbmp,T2_da_mcc,T3_rt_lbmp,T4_rt_mcc",
                           prior_run="p", departure=None)
    with pytest.raises(RuntimeError):
        cli.cmd_replay(a)
    assert len(gates) == 3  # the gate ran (tag matched) before each product's fetch
    assert json.loads(replay.ledger_path(repo).read_text())[-1]["status"] == "fetched"
    # the ledger is now a tracked-file change in a real repo; here it is untracked, so the tree stays clean
    with pytest.raises(replay.ReplayRefused):
        cli.cmd_replay(a)


def test_cmd_replay_records_the_tree_state_checked_before_its_ledger_write(tmp_path, monkeypatch):
    import argparse
    import subprocess

    from hq_price import cli
    repo = _tagged_repo(tmp_path)
    for prod in ("damlbmp", "rtlbmp", "isolf"):
        (repo / "data/raw" / prod).mkdir(parents=True)
        (repo / "data/raw" / prod / "x.zip").write_bytes(b"x")
    (repo / ".gitignore").write_text("data/\n")
    replay.ledger_path(repo).parent.mkdir(parents=True, exist_ok=True)
    replay.ledger_path(repo).write_text("[]")  # a tracked ledger, as in the real repository
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "ledger"], check=True)
    monkeypatch.setattr(cli, "REPO", repo)
    monkeypatch.setattr(cli, "_prior", lambda *a, **k: {})
    monkeypatch.setattr(cli.nyiso, "fetch", lambda *a, **k: None)
    seen = {}
    monkeypatch.setattr(cli, "_replay_record", lambda *a, **k: seen.update(git=a[6]) or {"run_id": "r"})
    a = argparse.Namespace(data=str(repo / "data"), targets="T1_da_lbmp,T2_da_mcc,T3_rt_lbmp,T4_rt_mcc",
                           prior_run="p", departure=None)
    cli.cmd_replay(a)
    assert seen["git"]["dirty"] is False  # the ledger write that follows the check does not mark the record dirty
    assert cli.runs.git_state(repo)["dirty"] is True
