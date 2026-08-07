from __future__ import annotations

from ..qt import QColor

# Shared pastel categorical palette for the donut/pie charts (expense mix).
PASTEL_HEX = [
    "#B9B6F0",
    "#C6D3B4",
    "#F2D06B",
    "#E9A491",
    "#9BB4E6",
    "#8FBF9F",
    "#E0B0D8",
    "#F7E2A6",
]


def qcolor_to_hex(c: QColor) -> str:
    """``QColor`` → ``#rrggbb`` (falls back to black on error)."""
    try:
        return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
    except Exception:
        return "#000000"
