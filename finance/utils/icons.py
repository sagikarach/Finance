from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# SVG icon data — stroke uses a "{color}" placeholder replaced at runtime.
# Designs follow Feather Icons style (MIT licensed, re-drawn here as strings).
# ---------------------------------------------------------------------------

_SVG_ICONS: dict[str, str] = {
    "gear": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83'
        "l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0"
        "v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83"
        "l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09"
        "A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83"
        "l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09"
        "a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83"
        'l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09'
        'a1.65 1.65 0 0 0-1.51 1z"/>'
        "</svg>"
    ),
    "bell": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
        '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>'
        "</svg>"
    ),
    "moon": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>'
        "</svg>"
    ),
    "sun": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="5"/>'
        '<line x1="12" y1="1" x2="12" y2="3"/>'
        '<line x1="12" y1="21" x2="12" y2="23"/>'
        '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>'
        '<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
        '<line x1="1" y1="12" x2="3" y2="12"/>'
        '<line x1="21" y1="12" x2="23" y2="12"/>'
        '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>'
        '<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>'
        "</svg>"
    ),
    "arrow_left": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="19" y1="12" x2="5" y2="12"/>'
        '<polyline points="12 19 5 12 12 5"/>'
        "</svg>"
    ),
    "plus": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="12" y1="5" x2="12" y2="19"/>'
        '<line x1="5" y1="12" x2="19" y2="12"/>'
        "</svg>"
    ),
    "trash": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="3 6 5 6 21 6"/>'
        '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>'
        "</svg>"
    ),
    "check": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"/>'
        "</svg>"
    ),
    "refresh": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="23 4 23 10 17 10"/>'
        '<polyline points="1 20 1 14 7 14"/>'
        '<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>'
        "</svg>"
    ),
    "hourglass": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M5 22h14"/><path d="M5 2h14"/>'
        '<path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/>'
        '<path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>'
        "</svg>"
    ),
    "edit": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
        '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>'
        "</svg>"
    ),
    "inbox": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>'
        '<path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89'
        'A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>'
        "</svg>"
    ),
    "chevron_down": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 12 15 18 9"/>'
        "</svg>"
    ),
    "chevron_up": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
        ' stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="18 15 12 9 6 15"/>'
        "</svg>"
    ),
}

# Stroke colours per theme
_COLOR_LIGHT = "#374151"   # dark gray — readable on light backgrounds
_COLOR_DARK = "#e5e7eb"    # light gray — readable on dark backgrounds


def _svg_for(name: str, color: str) -> str:
    template = _SVG_ICONS.get(name, "")
    if not template:
        return ""
    return template.replace("{color}", color)


def make_icon(name: str, size: int = 20, is_dark: bool = False) -> "QIcon":
    """
    Render a named SVG icon and return a QIcon at *size* × *size* pixels.
    Falls back to an empty QIcon if QtSvg is unavailable or the name is unknown.
    """
    color = _COLOR_DARK if is_dark else _COLOR_LIGHT
    svg_str = _svg_for(name, color)
    if not svg_str:
        from ..qt import QIcon
        return QIcon()
    try:
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray
        from ..qt import QIcon, QPixmap, QPainter, Qt, QSize

        renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
        pixmap = QPixmap(QSize(size, size))
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except Exception:
        from ..qt import QIcon
        return QIcon()


def apply_icon(
    btn: "QToolButton",
    name: str,
    size: int = 20,
    is_dark: bool = False,
) -> None:
    """
    Set a named SVG icon on *btn*, clear its text, and tag it with the icon
    name so theme-refresh callbacks can update the colour automatically.

    Falls back gracefully: if the SVG renderer is unavailable the button keeps
    whatever text it already had.
    """
    icon = make_icon(name, size=size, is_dark=is_dark)
    if icon.isNull():
        return
    try:
        from ..qt import QSize
        btn.setIcon(icon)
        btn.setIconSize(QSize(size, size))
        btn.setText("")
        btn.setProperty("svg_icon", name)
        btn.setProperty("svg_size", size)
    except Exception:
        pass


def refresh_icon(btn: "QToolButton", is_dark: bool) -> None:
    """Re-render the icon on *btn* for the given theme."""
    try:
        name = str(btn.property("svg_icon") or "")
        size = int(btn.property("svg_size") or 20)
    except Exception:
        return
    if name:
        apply_icon(btn, name, size=size, is_dark=is_dark)
