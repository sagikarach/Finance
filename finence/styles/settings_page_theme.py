from __future__ import annotations


def load_settings_page_light_styles() -> str:
    return """
    QPushButton#SaveButton {
        background: #a3baed; /* slightly lighter blue */
        border-color: #c9d5f5;
        font-weight: 600;
        min-width: 96px;
        color: #111827;
    }
    QPushButton#SaveButton:hover {
        background: #8aa7f7;
    }
    QPushButton#SaveButton:pressed {
        background: #576db5;
    }
    """


def load_settings_page_dark_styles() -> str:
    return """
    QPushButton#SaveButton {
        background: #1d4ed8;
        border-color: #1e3a8a;
        font-weight: 600;
        min-width: 96px;
        color: #e5e7eb;
    }
    """
