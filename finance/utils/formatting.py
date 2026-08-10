from __future__ import annotations

from typing import Optional


def fmt_money(value: float, decimals: int = 0) -> str:
    """A bare number with thousands separators and no currency symbol
    (e.g. ``1,234``). Falls back to ``str(value)`` on bad input."""
    try:
        return f"{float(value):,.{int(decimals)}f}"
    except (ValueError, TypeError):
        return str(value)


def parse_float(text: object) -> Optional[float]:
    """Parse a user-entered number, tolerating commas/whitespace. Returns
    ``None`` for blank or unparseable input."""
    s = str(text or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def format_currency(value: float, use_compact: bool = False) -> str:
    try:
        if use_compact:
            return f"₪{value:,.0f}" if abs(value) >= 1000 else f"₪{value:,.2f}"
        else:
            return f"₪{value:,.2f}"
    except (ValueError, TypeError):
        return f"₪{value}"
