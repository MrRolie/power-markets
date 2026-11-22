"""Run records: every number a report prints traces to one of these (docs/plan.md §10)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

LABELS = ("in sample", "validation (seen)", "held out")


class RecordError(RuntimeError):
    pass


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def git_state(repo: Path) -> dict:
    commit = _git(repo, "rev-parse", "HEAD").strip()
    dirty = bool(_git(repo, "status", "--porcelain", "--untracked-files=no").strip())
    return {"commit": commit, "dirty": dirty}


def tag_check(repo: Path, tag: str, files: list[str]) -> dict:
    """Whether each file equals its content at the tag. A missing tag is reported, never assumed."""
    try:
        _git(repo, "rev-parse", "--verify", f"refs/tags/{tag}")
    except subprocess.CalledProcessError:
        return {"tag": tag, "present": False, "match": False, "files": {}}
    res = {}
    for f in files:
        try:
            at_tag = _git(repo, "show", f"{tag}:{f}")
        except subprocess.CalledProcessError:
            res[f] = False
            continue
        res[f] = (repo / f).read_text() == at_tag
    return {"tag": tag, "present": True, "match": all(res.values()) and bool(res), "files": res}


def versions(pkgs=("numpy", "pandas", "scikit-learn", "scipy", "pyarrow", "pmcore", "hq-price")) -> dict:
    out = {}
    for p in pkgs:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = None
    return out


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def new_run_id(kind: str) -> str:
    return f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{kind}-{uuid.uuid4().hex[:6]}"


def write(record_dir: Path, run_id: str, record: dict) -> Path:
    if record.get("label") not in LABELS:
        raise RecordError(f"label {record.get('label')!r} is not one of {LABELS}")
    record_dir.mkdir(parents=True, exist_ok=True)
    path = record_dir / f"{run_id}.json"
    if path.exists():
        raise RecordError(f"{path} exists; records are never overwritten")
    record = {"run_id": run_id, "written_utc": datetime.now(timezone.utc).isoformat(), **record}
    path.write_text(json.dumps(record, indent=1, sort_keys=True, default=str))
    return path


def read(record_dir: Path, run_id: str) -> dict:
    path = record_dir / f"{run_id}.json"
    if not path.exists():
        raise RecordError(f"no run record {run_id}")
    return json.loads(path.read_text())
