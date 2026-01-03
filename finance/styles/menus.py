from __future__ import annotations


def load_menus_light_styles() -> str:
    return """
    QMenuBar {
        background: #f8fafc;
        color: #111827;
        padding: 4px 8px;
        border-bottom: 1px solid #e5e7eb;
    }
    QMenuBar::item:selected {
        background: #e5e7eb;
        border-radius: 6px;
    }
    QMenu {
        background: #ffffff;
        color: #111827;
        border: 1px solid #e5e7eb;
    }
    QMenu::item:selected {
        background: #f1f5f9;
    }
    """


def load_menus_dark_styles() -> str:
    return """
    QMenuBar {
        background: #020617;
        color: #e5e7eb;
        padding: 4px 8px;
        border-bottom: 1px solid #1f2937;
    }
    QMenuBar::item:selected {
        background: #1f2937;
        border-radius: 6px;
    }
    QMenu {
        background: #020617;
        color: #e5e7eb;
        border: 1px solid #1f2937;
    }
    QMenu::item:selected {
        background: #111827;
    }
    """
