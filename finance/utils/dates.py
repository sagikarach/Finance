"""Date parsing/normalization — the single source of truth for date handling.

Kept as a leaf module (depends only on the stdlib + ``utils.safe``) so any
layer, including the domain models, can normalize dates without an import cycle.
``finance.models.accounts`` re-exports these for backward compatibility.
"""

from __future__ import annotations

from datetime import date, datetime
import re

from .safe import PARSE_ERRORS

ISO_DATE = "%Y-%m-%d"


def shift_month(base: date, delta_months: int) -> tuple[int, int]:
    """Return ``(year, month)`` shifted by ``delta_months`` from ``base``."""
    y = int(base.year)
    m0 = int(base.month) - 1
    n = y * 12 + m0 + int(delta_months)
    return int(n // 12), int(n % 12 + 1)

# A value already in canonical ISO YYYY-MM-DD form — used to skip work.
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_iso_date(value: str) -> datetime:
    """Parse a date string to ``datetime``, tolerating every format the app's
    various sources emit. Returns ``datetime.min`` when nothing matches."""
    s = str(value or "").strip()
    if not s:
        return datetime.min

    # Fast path: ISO-like formats.
    try:
        return datetime.fromisoformat(s)
    except PARSE_ERRORS:
        pass
    try:
        return datetime.strptime(s, ISO_DATE)
    except PARSE_ERRORS:
        pass

    # Common bank-export formats.
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except PARSE_ERRORS:
        pass
    try:
        return datetime.strptime(s, "%d.%m.%Y")
    except PARSE_ERRORS:
        pass
    # Dash-separated day-first (e.g. 16-07-2026). Guarded by the fast ISO paths
    # above, so a real yyyy-mm-dd is never mistaken for this.
    try:
        return datetime.strptime(s, "%d-%m-%Y")
    except PARSE_ERRORS:
        pass

    # 2-digit year (e.g. 01/01/24, 01.01.24 or 01-01-24)
    m = re.match(r"^\s*(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2})\s*$", s)
    if m:
        try:
            d = int(m.group(1))
            mo = int(m.group(2))
            yy = int(m.group(3))
            year = 2000 + yy  # assume 20xx for exports
            return datetime(year, mo, d)
        except PARSE_ERRORS:
            return datetime.min

    # Missing year (e.g. 01/01, 01.01 or 01-01) -> assume current year.
    m2 = re.match(r"^\s*(\d{1,2})[/.\-](\d{1,2})\s*$", s)
    if m2:
        try:
            d = int(m2.group(1))
            mo = int(m2.group(2))
            now = datetime.now()
            return datetime(int(now.year), mo, d)
        except PARSE_ERRORS:
            return datetime.min

    return datetime.min


def to_iso_date(value: str) -> str:
    """Normalize a date string to ISO ``YYYY-MM-DD``.

    Reuses :func:`parse_iso_date` so every format the app already tolerates
    (DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY, 2-digit years, ...) is accepted.
    Returns the stripped original unchanged if it cannot be parsed, so an
    unexpected input is never silently discarded.
    """
    s = str(value or "").strip()
    if not s:
        return ""
    if _ISO_RE.match(s):
        return s  # already canonical — skip the parse round-trip
    dt = parse_iso_date(s)
    if dt == datetime.min:
        return s
    return dt.date().isoformat()
