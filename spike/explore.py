"""Spike exploration over the fenced archive (2016-01..2025-10). Reference only.

Prints one JSON document of measurements; nothing here reaches the product.
Usage: python explore.py <raw_dir> <out_json>
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

FENCE = pd.Timestamp("2025-11-01")


def load_zone_zips(d: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames, meta = [], []
    for z in sorted(d.glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                day = pd.Timestamp(info.filename[:8])
                meta.append({"day": day, "zip_mtime": pd.Timestamp(*info.date_time)})
                df = pd.read_csv(io.BytesIO(zf.read(info))).iloc[:, :6]
                df.columns = ["ts", "name", "ptid", "lbmp", "mcl", "mcc"]
                df["file_day"] = day
                frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], format="%m/%d/%Y %H:%M")
    assert df["ts"].max() < FENCE, "fence breached"
    return df, pd.DataFrame(meta)


def sign_test(df: pd.DataFrame) -> dict:
    out = {}
    for label, s in (("lbmp_minus_mcl_plus_mcc", 1), ("lbmp_minus_mcl_minus_mcc", -1)):
        e = df["lbmp"] - df["mcl"] + s * df["mcc"]
        spread = e.groupby([df["file_day"], df["ts"]]).agg(lambda x: x.max() - x.min())
        out[label] = {
            "hours": int(spread.size),
            "share_spread_le_0.02": float((spread <= 0.02).mean()),
            "p99_spread": float(spread.quantile(0.99)),
        }
    return out


def dst_rows(df: pd.DataFrame) -> dict:
    hq = df[df["name"] == "H Q"]
    n = hq.groupby("file_day").size()
    odd = n[n != 24]
    ex = {}
    for day in odd.index[:4]:
        ex[str(day.date())] = hq[hq["file_day"] == day]["ts"].dt.strftime("%H:%M").tolist()
    return {"rows_per_day_counts": {int(k): int(v) for k, v in n.value_counts().items()},
            "examples": ex}


def hq_describe(df: pd.DataFrame, label: str) -> dict:
    hq = df[df["name"] == "H Q"].copy()
    hq["year"] = hq["ts"].dt.year
    g = hq.groupby("year")
    return {
        f"{label}_by_year": {
            int(y): {
                "n": int(len(x)),
                "lbmp_mean": round(float(x["lbmp"].mean()), 2),
                "lbmp_p01": round(float(x["lbmp"].quantile(0.01)), 2),
                "lbmp_p99": round(float(x["lbmp"].quantile(0.99)), 2),
                "share_lbmp_le_0": round(float((x["lbmp"] <= 0).mean()), 4),
                "mcc_mean": round(float(x["mcc"].mean()), 2),
                "share_mcc_nonzero": round(float((x["mcc"].abs() > 0.005).mean()), 4),
                "mcc_p01": round(float(x["mcc"].quantile(0.01)), 2),
                "mcc_p99": round(float(x["mcc"].quantile(0.99)), 2),
            }
            for y, x in g
        }
    }


def hq_vs_zone(df: pd.DataFrame, other: str) -> dict:
    p = df[df["name"].isin(["H Q", other])].pivot_table(index="ts", columns="name", values="lbmp")
    d = p["H Q"] - p[other]
    return {f"hq_minus_{other}": {"mean": round(float(d.mean()), 2), "corr": round(float(p.corr().iloc[0, 1]), 3)}}


def posting_times(meta: pd.DataFrame) -> dict:
    lag = (meta["zip_mtime"] - meta["day"]).dt.total_seconds() / 3600
    return {"zip_mtime_minus_file_day_hours": {
        "min": round(float(lag.min()), 2), "p50": round(float(lag.median()), 2),
        "p95": round(float(lag.quantile(0.95)), 2), "max": round(float(lag.max()), 2),
        "share_after_file_day_start": round(float((lag > 0).mean()), 4)}}


def autocorr(df: pd.DataFrame) -> dict:
    hq = df[df["name"] == "H Q"].set_index("ts")["lbmp"].sort_index()
    hq = hq[~hq.index.duplicated()]
    return {f"acf_lag_{h}h": round(float(hq.autocorr(h)), 3) for h in (24, 48, 168)}


def main(raw: Path, out: Path) -> None:
    res = {}
    da, da_meta = load_zone_zips(raw / "damlbmp")
    res["da_rows"] = int(len(da))
    res["da_span"] = [str(da["ts"].min()), str(da["ts"].max())]
    res["da_names"] = sorted(da["name"].unique().tolist())
    res["da_sign_test"] = sign_test(da)
    res["da_dst"] = dst_rows(da)
    res["da_posting"] = posting_times(da_meta)
    res.update(hq_describe(da, "da"))
    res.update(hq_vs_zone(da, "NORTH"))
    res["da_acf"] = autocorr(da)
    rt_dir = raw / "rtlbmp"
    if any(rt_dir.glob("*.zip")):
        rt, rt_meta = load_zone_zips(rt_dir)
        res["rt_rows"] = int(len(rt))
        res["rt_span"] = [str(rt["ts"].min()), str(rt["ts"].max())]
        res["rt_ts_minutes"] = sorted(rt["ts"].dt.minute.unique().tolist())[:12]
        res["rt_sign_test"] = sign_test(rt)
        res["rt_dst"] = dst_rows(rt)
        res["rt_posting"] = posting_times(rt_meta)
        res.update(hq_describe(rt, "rt"))
        m = da[da["name"] == "H Q"].set_index("ts")["lbmp"]
        r = rt[rt["name"] == "H Q"].set_index("ts")["lbmp"]
        m, r = m[~m.index.duplicated()], r[~r.index.duplicated()]
        spread = (m - r).dropna()
        res["hq_da_minus_rt"] = {"n": int(spread.size), "mean": round(float(spread.mean()), 2),
                                  "sd": round(float(spread.std()), 2)}
    out.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"ok": True, "out": str(out)}))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
