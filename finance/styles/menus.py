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
        color: #1E1E22;
        border: 1px solid #E7E4DB;
        border-radius: 12px;
        padding: 6px;
    }
    QMenu::item {
        background: transparent;
        padding: 9px 18px 9px 14px;
        border-radius: 8px;
        margin: 1px 2px;
    }
    QMenu::item:selected {
        background: #EFEDE4;
        color: #1E1E22;
    }
    QMenu::separator {
        height: 1px;
        background: #ECEAE2;
        margin: 5px 10px;
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
        background: #242219;
        color: #F3F1EA;
        border: 1px solid #332f24;
        border-radius: 12px;
        padding: 6px;
    }
    QMenu::item {
        background: transparent;
        padding: 9px 18px 9px 14px;
        border-radius: 8px;
        margin: 1px 2px;
    }
    QMenu::item:selected {
        background: #3a3428;
        color: #F3F1EA;
    }
    QMenu::separator {
        height: 1px;
        background: #332f24;
        margin: 5px 10px;
    }
    """
