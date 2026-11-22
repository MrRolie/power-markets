"""NERC holidays (docs/plan.md §2): six days; Sunday observed on Monday, Saturday not moved."""

from __future__ import annotations

from datetime import date, timedelta


def _nth_weekday(y: int, m: int, weekday: int, n: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(y: int, m: int, weekday: int) -> date:
    d = date(y, m + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def nerc_holidays(year: int) -> set[date]:
    fixed = [date(year, 1, 1), date(year, 7, 4), date(year, 12, 25)]
    out = {d + timedelta(days=1) if d.weekday() == 6 else d for d in fixed}
    out.add(_last_weekday(year, 5, 0))  # Memorial Day
    out.add(_nth_weekday(year, 9, 0, 1))  # Labor Day
    out.add(_nth_weekday(year, 11, 3, 4))  # Thanksgiving
    return out


def is_nerc_holiday(d) -> bool:
    d = d.date() if hasattr(d, "date") else d
    return d in nerc_holidays(d.year)
