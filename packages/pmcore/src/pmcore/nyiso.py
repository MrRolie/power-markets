"""NYISO public files: fetch behind a fence, read into UTC rows that carry their posting time.

Facts used here are measured in docs/problem.md §5:
- time stamps are hour-beginning, Eastern prevailing time; the spring day has 23 rows, the autumn day 25 with
  01:00 written twice, told apart only by order;
- each daily file inside a monthly zip carries an entry time (local wall clock), used as its posting time.
"""

from __future__ import annotations

import hashlib
import io
import time
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TZ = "America/New_York"
BASE = "https://mis.nyiso.com/public/csv"
UA = "power-markets-research-fetch/0.1 (polite, cached, one pass)"
PRODUCTS = {
    "damlbmp": "damlbmp/{ym}01damlbmp_zone_csv.zip",
    "rtlbmp": "rtlbmp/{ym}01rtlbmp_zone_csv.zip",
    "isolf": "isolf/{ym}01isolf_csv.zip",
}


class FenceError(ValueError):
    """A request reached into data the plan has not released."""


class ClockError(ValueError):
    """A day's rows do not match the clock-change convention."""


# ---------------------------------------------------------------- fetch


@dataclass(frozen=True)
class Fence:
    first_unfetched: pd.Timestamp  # first operating day never fetched without the gate
    gate: Callable[[], None] | None = None  # raises unless the held-out release is allowed

    def check_month(self, year: int, month: int, *, held_out: bool) -> None:
        last_day = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
        if last_day < self.first_unfetched:
            return
        if not held_out:
            raise FenceError(f"{year}-{month:02d} reaches past {self.first_unfetched.date()}: refused")
        if self.gate is None:
            raise FenceError("held-out fetch requested with no gate: refused")
        self.gate()


def months(start: str, end: str) -> list[tuple[int, int]]:
    p = pd.period_range(start, end, freq="M")
    return [(x.year, x.month) for x in p]


def fetch(product: str, start: str, end: str, raw: Path, fence: Fence, *, held_out: bool = False,
          pause: float = 1.0, opener=urllib.request.urlopen) -> list[dict]:
    todo = months(start, end)
    for y, m in todo:  # the whole request is refused before any network call
        fence.check_month(y, m, held_out=held_out)
    dest = raw / product
    dest.mkdir(parents=True, exist_ok=True)
    log = []
    for y, m in todo:
        rel = PRODUCTS[product].format(ym=f"{y}{m:02d}")
        path = dest / Path(rel).name
        if path.exists() and path.stat().st_size > 0:
            log.append({"file": rel, "status": "cached"})
            continue
        req = urllib.request.Request(f"{BASE}/{rel}", headers={"User-Agent": UA})
        with opener(req, timeout=60) as r:
            body = r.read()
        zipfile.ZipFile(io.BytesIO(body)).testzip()
        path.write_bytes(body)
        log.append({"file": rel, "status": "fetched", "bytes": len(body)})
        time.sleep(pause)
    return log


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- read


def local_hours_to_utc(day: pd.Timestamp, stamps: list[str]) -> pd.DatetimeIndex:
    """Map one operating day's hour-beginning local stamps to UTC, by order on clock-change days."""
    start = pd.Timestamp(day).tz_localize(TZ)
    end = (pd.Timestamp(day) + pd.Timedelta(days=1)).tz_localize(TZ)
    n_hours = int((end - start) / pd.Timedelta(hours=1))
    expected = pd.date_range(start.tz_convert("UTC"), periods=n_hours, freq="h")
    if len(stamps) != n_hours:
        raise ClockError(f"{day.date()}: {len(stamps)} rows, {n_hours} hours in the local day")
    wall = [t.tz_convert(TZ).strftime("%H:%M") for t in expected]
    if [s[-5:] for s in stamps] != wall:
        raise ClockError(f"{day.date()}: stamps do not match the local hours in order")
    return expected


def entry_time_utc(date_time: tuple) -> pd.Timestamp:
    """A zip entry's local wall time, as UTC. An ambiguous autumn time takes the later reading."""
    t = pd.Timestamp(*date_time)
    return t.tz_localize(TZ, ambiguous=False, nonexistent="shift_forward").tz_convert("UTC")


def read_zone_zip(path: Path) -> pd.DataFrame:
    """Rows: day, ts_utc, name, ptid, lbmp, mcl, mcc, posted_utc."""
    out = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            day = pd.Timestamp(info.filename[:8])
            df = pd.read_csv(io.BytesIO(zf.read(info))).iloc[:, :6]
            df.columns = ["stamp", "name", "ptid", "lbmp", "mcl", "mcc"]
            names = df["name"].unique()
            first = df.loc[df["name"] == names[0], "stamp"].tolist()
            utc = local_hours_to_utc(day, first)
            mapping = dict(enumerate(utc))
            df["k"] = df.groupby("name", sort=False).cumcount()
            sizes = df.groupby("name", sort=False).size()
            if (sizes != len(first)).any():
                raise ClockError(f"{info.filename}: names carry different row counts")
            # every name must carry the same stamp sequence, in the same order
            if not (df.groupby("name", sort=False)["stamp"].apply(list).map(lambda x: x == first)).all():
                raise ClockError(f"{info.filename}: names carry different stamps")
            df["ts_utc"] = df["k"].map(mapping)
            df["day"] = day
            df["posted_utc"] = entry_time_utc(info.date_time)
            out.append(df.drop(columns=["stamp", "k"]))
    df = pd.concat(out, ignore_index=True)
    return df[["day", "ts_utc", "name", "ptid", "lbmp", "mcl", "mcc", "posted_utc"]]


def read_isolf_zip(path: Path) -> pd.DataFrame:
    """Rows: issue_file_day, ts_utc, area, mw, posted_utc. An issue covers several days."""
    out = []
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            fday = pd.Timestamp(info.filename[:8])
            df = pd.read_csv(io.BytesIO(zf.read(info)))
            stamp = df.columns[0]
            df["d"] = pd.to_datetime(df[stamp].str[:10], format="%m/%d/%Y")
            parts = []
            for d, g in df.groupby("d", sort=True):
                g = g.copy()
                try:
                    g["ts_utc"] = local_hours_to_utc(d, g[stamp].tolist())
                except ClockError:
                    continue  # a partial last day in an issue is dropped, not guessed
                parts.append(g)
            w = pd.concat(parts).drop(columns=[stamp, "d"])
            long = w.melt(id_vars="ts_utc", var_name="area", value_name="mw")
            long["issue_file_day"] = fday
            long["posted_utc"] = entry_time_utc(info.date_time)
            out.append(long)
    return pd.concat(out, ignore_index=True)


def load_product(raw: Path, product: str, cache: Path) -> pd.DataFrame:
    """All zips of one product, cached as parquet keyed by the zips' hashes."""
    zips = sorted((raw / product).glob("*.zip"))
    if not zips:
        raise FileNotFoundError(f"no {product} archives under {raw}")
    key = hashlib.sha256("".join(sha256(z) for z in zips).encode()).hexdigest()[:16]
    cache.mkdir(parents=True, exist_ok=True)
    cpath = cache / f"{product}-{key}.parquet"
    if cpath.exists():
        return pd.read_parquet(cpath)
    reader = read_isolf_zip if product == "isolf" else read_zone_zip
    df = pd.concat([reader(z) for z in zips], ignore_index=True)
    df.to_parquet(cpath)
    return df


def manifest(raw: Path, products) -> dict[str, str]:
    return {f"{p}/{z.name}": sha256(z) for p in products for z in sorted((raw / p).glob("*.zip"))}


def decision_time_utc(day: pd.Timestamp | str, hour_local: int = 5) -> pd.Timestamp:
    """Decision time for operating day `day`: `hour_local`:00 Eastern on the day before."""
    d = pd.Timestamp(day) - pd.Timedelta(days=1)
    return (d + pd.Timedelta(hours=hour_local)).tz_localize(TZ).tz_convert("UTC")

