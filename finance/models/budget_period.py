from __future__ import annotations

from typing import Optional

from .accounts import parse_iso_date


def next_month(year: int, month: int) -> tuple[int, int]:
    if month >= 12:
        return year + 1, 1
    return year, month + 1


def future_months(
    n: int, *, after: Optional[tuple[int, int]] = None
) -> list[tuple[int, int]]:
    """The next ``n`` ``(year, month)`` tuples strictly after ``after`` — which
    defaults to the current calendar month."""
    if after is None:
        from datetime import date as _date

        try:
            today = _date.today()
            after = (today.year, today.month)
        except Exception:
            after = (1970, 1)
    y, m = int(after[0]), int(after[1])
    out: list[tuple[int, int]] = []
    for _ in range(max(0, int(n))):
        y, m = next_month(y, m)
        out.append((y, m))
    return out


def budget_period_end_key(date_str: str, reset_day: int) -> Optional[tuple[int, int]]:
    from datetime import datetime as _datetime

    try:
        dt = parse_iso_date(str(date_str or "").strip())
    except Exception:
        return None
    if dt == _datetime.min:
        return None
    if int(dt.day) <= int(reset_day):
        return int(dt.year), int(dt.month)
    return next_month(int(dt.year), int(dt.month))


def current_budget_period_end_key(reset_day: int) -> tuple[int, int]:
    try:
        from datetime import date as _date

        today = _date.today()
    except Exception:
        return 1970, 1
    if int(today.day) <= int(reset_day):
        return int(today.year), int(today.month)
    return next_month(int(today.year), int(today.month))
