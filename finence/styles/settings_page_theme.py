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

    /* Settings internal sidebar menu (matches app sidebar light theme) */
    QListWidget#SettingsMenu {
        background: #bfdbfe;
        border: 0;
        outline: 0;
        padding: 8px;
        border-radius: 12px;
    }
    QListWidget#SettingsMenu::item {
        background: transparent;
        color: #0f172a;
        padding: 10px 12px;
        border-radius: 10px;
        margin: 4px 0px;
        font-weight: 600;
    }
    QListWidget#SettingsMenu::item:hover {
        background: #c9e1fe;
    }
    QListWidget#SettingsMenu::item:selected {
        background: #dcecff;
        color: #0f172a;
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

    /* Settings internal sidebar menu (matches app sidebar dark theme) */
    QListWidget#SettingsMenu {
        background: #111827;
        border: 0;
        outline: 0;
        padding: 8px;
        border-radius: 12px;
    }
    QListWidget#SettingsMenu::item {
        background: transparent;
        color: #e5e7eb;
        padding: 10px 12px;
        border-radius: 10px;
        margin: 4px 0px;
        font-weight: 600;
    }
    QListWidget#SettingsMenu::item:hover {
        background: #1f2937;
    }
    QListWidget#SettingsMenu::item:selected {
        background: #020617;
        color: #e5e7eb;
    }
    """
