"""Theme-aware colours for styles written in code (setStyleSheet / QColor).

Pages rebuild their content when the theme changes (and when they are shown),
so picking the colour at build time is enough.
"""

from __future__ import annotations

from ..utils.safe import QT_ERRORS


def is_dark() -> bool:
    try:
        from ..qt import QApplication

        app = QApplication.instance()
        return bool(app) and str(app.property("theme") or "light") == "dark"
    except QT_ERRORS:
        return False


def tc(light: str, dark: str) -> str:
    """``light`` in the light theme, ``dark`` in the dark theme."""
    return dark if is_dark() else light


# Text on the app's neutral surfaces.
def ink() -> str:  # primary text
    return tc("#1e1e22", "#e5e7eb")


def ink_soft() -> str:  # secondary text
    return tc("#6b6f66", "#9ca3af")


def ink_faint() -> str:  # hints / captions
    return tc("#a8aca1", "#6b7280")


# Money colours that read on both backgrounds.
def money_pos() -> str:
    return tc("#2f9e68", "#5fc28c")


def money_neg() -> str:
    return tc("#d66a4e", "#e9a491")


# The butter hero card (DashHeroYellow): its title / pill buttons / captions.
def hero_title() -> str:
    return tc("#5c4d15", "#e8c766")


def hero_caption() -> str:
    return tc("#7a6420", "#b8a46a")


def hero_pill_style() -> str:
    """Pill buttons on the butter hero card."""
    if is_dark():
        return (
            "QPushButton{background:rgba(242,208,107,0.14);color:#f2d06b;border:none;"
            "border-radius:12px;padding:9px 16px;font-weight:700;font-size:13px;}"
            "QPushButton:hover{background:rgba(242,208,107,0.24);}"
            "QPushButton:disabled{color:rgba(242,208,107,0.4);}"
        )
    return (
        "QPushButton{background:rgba(44,38,18,0.16);color:#3f3616;border:none;"
        "border-radius:12px;padding:9px 16px;font-weight:700;font-size:13px;}"
        "QPushButton:hover{background:rgba(44,38,18,0.26);}"
        "QPushButton:disabled{color:rgba(63,54,22,0.4);}"
    )


def hero_chip_style() -> str:
    """A small tag on the butter hero card (e.g. "לא נזיל")."""
    return (
        "font-size:12px;font-weight:700;color:%s;background:%s;"
        "border-radius:9px;padding:3px 10px;"
        % tc(("#7a6420", "rgba(44,38,18,0.12)"), ("#e8c766", "rgba(242,208,107,0.14)"))
    )


def budget_bar_style(over: bool) -> str:
    """The rounded progress bar of a plan / event budget (QProgressBar#BudgetBar)."""
    if over:
        stops = tc(("#e9a491", "#d66a4e"), ("#8a4a3a", "#e9a491"))
    else:
        stops = tc(("#8FBF9F", "#2f9e68"), ("#3f7a58", "#5fc28c"))
    track = tc("#eef1ea", "#1e293b")
    return (
        "QProgressBar#BudgetBar{background:%s;border:none;border-radius:7px;}"
        "QProgressBar#BudgetBar::chunk{border-radius:7px;background:"
        "qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 %s,stop:1 %s);}" % (track, stops[0], stops[1])
    )


def status_badge_colors(status_text: str) -> tuple:
    """(background, text) of an event status badge."""
    light = {
        "פעיל": ("#eaf5ef", "#2f9e68"),
        "מתוכנן": ("#ecebfb", "#4a3f9e"),
        "הסתיים": ("#eef1ea", "#5b5f57"),
        "בארכיון": ("#f0eee6", "#8a8d83"),
    }
    dark = {
        "פעיל": ("#14241c", "#5fc28c"),
        "מתוכנן": ("#1d1c33", "#b9b6f0"),
        "הסתיים": ("#1e293b", "#9ca3af"),
        "בארכיון": ("#1a2233", "#6b7280"),
    }
    table = dark if is_dark() else light
    return table.get(status_text, table["הסתיים"])
