"""Line/area chart colours, matched to the app's pastel palette.

The pastels themselves (``donut_utils.PASTEL_HEX``: lavender, sage, butter,
coral, periwinkle…) are too light for a 2–3px line on a white card, so lines
use a deeper tone of the same hue and fills use the soft pastel. Every colour
here reads on both the light (white/beige) and dark (navy) backgrounds.
"""

from __future__ import annotations

import zlib

from ..qt import QColor

POSITIVE = "#2f9e68"  # green — balances, income, principal (DashCardGreen)
NEGATIVE = "#d66a4e"  # coral — expenses, deficits, interest (MonthExpenseCard)
ACCENT = "#8b7fd4"  # lavender — a single neutral series (mortgage balance)
TODAY = "#d9b44a"  # butter — "today" / history→forecast marker
MILESTONE = "#a8a395"  # warm grey — secondary markers

# Several series at once: deeper tones of PASTEL_HEX, in the same order.
SERIES = [
    "#8b7fd4",  # lavender
    "#2f9e68",  # green
    "#d66a4e",  # coral
    "#6f8fd6",  # periwinkle
    "#c9a43a",  # butter
    "#b77bb0",  # orchid
    "#4f9a9a",  # teal
    "#8a9a5b",  # sage
]


def series_color(index: int) -> QColor:
    return QColor(SERIES[int(index) % len(SERIES)])


def color_for_key(key: str) -> QColor:
    """A stable colour per name (the same category keeps its colour)."""
    h = zlib.crc32(str(key).encode("utf-8")) & 0xFFFFFFFF
    return QColor(SERIES[h % len(SERIES)])


def today_shade(alpha: int = 30) -> QColor:
    c = QColor(TODAY)
    c.setAlpha(alpha)
    return c
