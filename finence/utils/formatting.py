from __future__ import annotations


def format_currency(value: float, use_compact: bool = False) -> str:
    try:
        if use_compact:
            return f"₪{value:,.0f}" if abs(value) >= 1000 else f"₪{value:,.2f}"
        else:
            return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"
