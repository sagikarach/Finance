from __future__ import annotations

from datetime import date


def shift_month(base: date, delta_months: int) -> tuple[int, int]:
    """Return ``(year, month)`` shifted by ``delta_months`` from ``base``."""
    y = int(base.year)
    m0 = int(base.month) - 1
    n = y * 12 + m0 + int(delta_months)
    return int(n // 12), int(n % 12 + 1)
