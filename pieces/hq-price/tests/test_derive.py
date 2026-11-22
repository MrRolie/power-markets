"""`derive` re-scores only validation forecasts, and only files that match their record."""

import argparse
import json

import pandas as pd
import pytest

from hq_price import cli, replay
from pmcore import runs


def _setup(tmp_path, monkeypatch, label):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                    "--allow-empty", "-m", "x"], check=True)
    monkeypatch.setattr(cli, "REPO", tmp_path)
    d = tmp_path / "data" / "runs" / "src"
    d.mkdir(parents=True)
    p = d / "T1_da_lbmp.parquet"
    pd.DataFrame({"y": [1.0]}).to_parquet(p)
    runs.write(tmp_path / "runs", "src", {"label": label, "targets": ["T1_da_lbmp"],
                                          "results": {"T1_da_lbmp": {"forecasts_sha256": "0" * 64}}})
    return argparse.Namespace(data=str(tmp_path / "data"), from_run="src")


def test_derive_refuses_held_out(tmp_path, monkeypatch):
    with pytest.raises(replay.ReplayRefused):
        cli.cmd_derive(_setup(tmp_path, monkeypatch, "held out"))


def test_derive_refuses_a_file_that_does_not_match_its_record(tmp_path, monkeypatch):
    with pytest.raises(runs.RecordError):
        cli.cmd_derive(_setup(tmp_path, monkeypatch, "validation (seen)"))
    assert not [p for p in (tmp_path / "runs").iterdir() if "derive" in p.name]


def test_derive_refusal_prints_json(tmp_path, monkeypatch, capsys):
    a = _setup(tmp_path, monkeypatch, "held out")
    assert cli.main(["--data", a.data, "derive", "--from-run", "src"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False
