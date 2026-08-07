from __future__ import annotations

from typing import List, Tuple

from ..qt import QApplication, QColor


def label_color() -> QColor:
    """Axis/label color that follows the app theme (dark → white, else ink)."""
    color = QColor("#0f172a")
    app = QApplication.instance()
    if app is not None:
        try:
            if str(app.property("theme") or "light") == "dark":
                color = QColor("#ffffff")
        except Exception:
            pass
    return color


def month_keys_from(start_date: str, count: int) -> List[Tuple[int, int]]:
    """List of ``(year, month)`` starting from ``start_date``, length ``count``."""
    from ..models.accounts import parse_iso_date

    dt = parse_iso_date(str(start_date or "").strip())
    y, m = int(dt.year), int(dt.month)
    keys: List[Tuple[int, int]] = []
    for _ in range(max(0, count)):
        keys.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return keys


def label_step_for(n: int) -> int:
    """A label step that yields at most ~7 axis labels."""
    return max(1, (n + 6) // 7)
