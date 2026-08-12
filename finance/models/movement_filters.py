from __future__ import annotations

from typing import Any, List

from .accounts import parse_iso_date
from .bank_movement import counts_as_transfer
from ..utils.safe import PARSE_ERRORS


def _in_month(date_str: str, year: int, month: int) -> bool:
    try:
        dt = parse_iso_date(date_str)
        return dt.year == year and dt.month == month
    except PARSE_ERRORS:
        return False


def movements_for_month(
    movements: List[Any], movement_type: Any, year: int, month: int
) -> List[Any]:
    """Movements of ``movement_type`` falling in ``(year, month)`` — excluding
    transfers and the 'העברה' category — sorted newest first."""
    filtered = [
        m
        for m in movements
        if m.type == movement_type
        and _in_month(m.date, year, month)
        and not counts_as_transfer(m)
    ]
    return sorted(filtered, key=lambda x: parse_iso_date(x.date), reverse=True)
