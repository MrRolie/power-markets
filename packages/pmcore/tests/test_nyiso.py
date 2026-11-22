import zipfile

import pandas as pd
import pytest

from pmcore import nyiso


def _zip(tmp_path, files):
    p = tmp_path / "x_csv.zip"
    with zipfile.ZipFile(p, "w") as zf:
        for name, text, dt in files:
            zi = zipfile.ZipInfo(name, date_time=dt)
            zf.writestr(zi, text)
    return p


HDR = "Time Stamp,Name,PTID,LBMP ($/MWHr),Marginal Cost Losses ($/MWHr),Marginal Cost Congestion ($/MWHr)\n"


def _day_csv(day: str, hours: list[str], names=("H Q", "WEST")):
    rows = [f"{day} {h},{n},1,10.0,0.5,0.1" for h in hours for n in names]
    return HDR + "\n".join(rows) + "\n"


def test_autumn_day_maps_duplicate_hour_by_order(tmp_path):
    hours = ["00:00", "01:00", "01:00"] + [f"{h:02d}:00" for h in range(2, 24)]
    p = _zip(tmp_path, [("20251102damlbmp_zone.csv", _day_csv("11/02/2025", hours), (2025, 11, 1, 9, 33, 0))])
    df = nyiso.read_zone_zip(p)
    hq = df[df["name"] == "H Q"].sort_values("ts_utc")
    assert len(hq) == 25
    assert hq["ts_utc"].is_unique
    assert hq["ts_utc"].diff().dropna().eq(pd.Timedelta(hours=1)).all()
    assert hq["ts_utc"].iloc[1] == pd.Timestamp("2025-11-02 05:00", tz="UTC")  # 01:00 EDT
    assert hq["ts_utc"].iloc[2] == pd.Timestamp("2025-11-02 06:00", tz="UTC")  # 01:00 EST


def test_spring_day_has_23_hours(tmp_path):
    hours = ["00:00", "01:00"] + [f"{h:02d}:00" for h in range(3, 24)]
    p = _zip(tmp_path, [("20250309damlbmp_zone.csv", _day_csv("03/09/2025", hours), (2025, 3, 8, 9, 33, 0))])
    df = nyiso.read_zone_zip(p)
    assert (df["name"] == "H Q").sum() == 23


def test_wrong_row_count_refused(tmp_path):
    hours = [f"{h:02d}:00" for h in range(24)]  # 24 rows on a 25-hour day
    p = _zip(tmp_path, [("20251102damlbmp_zone.csv", _day_csv("11/02/2025", hours), (2025, 11, 1, 9, 33, 0))])
    with pytest.raises(nyiso.ClockError):
        nyiso.read_zone_zip(p)


def test_posted_time_is_entry_time_in_utc(tmp_path):
    hours = [f"{h:02d}:00" for h in range(24)]
    p = _zip(tmp_path, [("20250701damlbmp_zone.csv", _day_csv("07/01/2025", hours), (2025, 6, 30, 9, 33, 0))])
    df = nyiso.read_zone_zip(p)
    assert (df["posted_utc"] == pd.Timestamp("2025-06-30 13:33", tz="UTC")).all()


def test_ambiguous_entry_time_takes_later_reading():
    t = nyiso.entry_time_utc((2025, 11, 2, 1, 30, 0))
    assert t == pd.Timestamp("2025-11-02 06:30", tz="UTC")


def test_decision_time():
    assert nyiso.decision_time_utc("2025-07-02") == pd.Timestamp("2025-07-01 09:00", tz="UTC")
    assert nyiso.decision_time_utc("2025-01-02") == pd.Timestamp("2025-01-01 10:00", tz="UTC")


def test_fence_refuses_before_any_request(tmp_path):
    fence = nyiso.Fence(pd.Timestamp("2025-11-01"))

    def boom(*a, **k):
        raise AssertionError("network touched")

    with pytest.raises(nyiso.FenceError):
        nyiso.fetch("damlbmp", "2025-09", "2025-11", tmp_path, fence, opener=boom)
    with pytest.raises(nyiso.FenceError):  # held_out without a gate
        nyiso.fetch("damlbmp", "2025-11", "2025-11", tmp_path, fence, held_out=True, opener=boom)
    fence.check_month(2025, 10, held_out=False)


def test_fence_gate_is_called_for_held_out(tmp_path):
    calls = []
    fence = nyiso.Fence(pd.Timestamp("2025-11-01"), gate=lambda: calls.append(1))
    fence.check_month(2025, 12, held_out=True)
    assert calls == [1]


def test_isolf_issue_rows(tmp_path):
    hdr = '"Time Stamp","Capitl","North","NYISO"\n'
    rows = [f'"07/01/2025 {h:02d}:00",1,2,3' for h in range(24)] + [f'"07/02/2025 {h:02d}:00",1,2,3' for h in range(24)]
    p = _zip(tmp_path, [("20250701isolf.csv", hdr + "\n".join(rows) + "\n", (2025, 6, 30, 7, 5, 0))])
    df = nyiso.read_isolf_zip(p)
    assert set(df["area"]) == {"Capitl", "North", "NYISO"}
    assert len(df) == 48 * 3
    assert (df["issue_file_day"] == pd.Timestamp("2025-07-01")).all()


