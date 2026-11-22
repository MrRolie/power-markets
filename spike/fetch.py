"""Spike fetcher: NYISO public monthly zips, fenced away from the most recent twelve months.

Reference code for the spike only; the product's fetcher is rebuilt from the plan.
The fence: no file for a month on or after FENCE_MONTH is ever requested. The 2025-11 monthly zip
straddles the twelve-month line (today 2026-11-20), so 2025-10 is the last admissible month.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://mis.nyiso.com/public/csv"
FENCE_MONTH = (2025, 11)  # first month that is never fetched in the spike
PRODUCTS = {
    "damlbmp": "damlbmp/{ym}01damlbmp_zone_csv.zip",  # day-ahead zonal LBMP, hourly
    "rtlbmp": "rtlbmp/{ym}01rtlbmp_zone_csv.zip",  # real-time zonal, list P-4A
    "isolf": "isolf/{ym}01isolf_csv.zip",  # ISO load forecast, list P-7
}
UA = "power-markets-research-fetch/0.1 (polite, cached, one pass)"


class FenceError(ValueError):
    pass


def check_fence(year: int, month: int) -> None:
    if (year, month) >= FENCE_MONTH:
        raise FenceError(f"{year}-{month:02d} is inside the fenced twelve months; refused")


def months(start: str, end: str):
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    while (y, m) <= (ey, em):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fetch(product: str, start: str, end: str, out: Path, pause: float = 1.0) -> list[dict]:
    todo = list(months(start, end))
    for y, m in todo:  # refuse the whole request before any network call
        check_fence(y, m)
    log = []
    dest = out / product
    dest.mkdir(parents=True, exist_ok=True)
    for y, m in todo:
        rel = PRODUCTS[product].format(ym=f"{y}{m:02d}")
        path = dest / Path(rel).name
        if path.exists() and path.stat().st_size > 0:
            log.append({"file": rel, "status": "cached", "bytes": path.stat().st_size})
            continue
        req = urllib.request.Request(f"{BASE}/{rel}", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            path.write_bytes(body)
            log.append({"file": rel, "status": "fetched", "bytes": len(body)})
        except Exception as e:  # noqa: BLE001 - spike: record and continue
            log.append({"file": rel, "status": "error", "error": str(e)})
        time.sleep(pause)
    return log


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("product", choices=sorted(PRODUCTS))
    p.add_argument("start")
    p.add_argument("end")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        log = fetch(a.product, a.start, a.end, a.out)
    except FenceError as e:
        print(json.dumps({"ok": False, "refused": str(e)}))
        return 2
    errs = [x for x in log if x["status"] == "error"]
    print(json.dumps({"ok": not errs, "n": len(log), "errors": errs}))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
