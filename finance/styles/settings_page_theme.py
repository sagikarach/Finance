from __future__ import annotations


def load_settings_page_light_styles() -> str:
    return """
    QLineEdit#SettingsInput {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid rgba(15,23,42,0.18);
        border-radius: 10px;
        padding: 8px 10px;
        min-height: 18px;
    }
    QLineEdit#SettingsInput:focus {
        border: 1px solid rgba(47,158,104,0.60);
    }
    QCheckBox#NotificationRuleToggle {
        /* Indent child notification toggles (RTL: margin-right pushes left) */
        margin-right: 24px;
    }

    QPushButton#SaveButton {
        background: #2f9e68;
        border: 1px solid #2a8f5e;
        font-weight: 600;
        min-width: 96px;
        color: #ffffff;
    }
    QPushButton#SaveButton:hover {
        background: #2a8f5e;
        border: 1px solid #247e52;
    }
    QPushButton#SaveButton:pressed {
        background: #247e52;
    }

    /* Settings internal sidebar menu (matches app sidebar light theme) */
    QListWidget#SettingsMenu {
        background: #ffffff;
        border: 1px solid #ecece2;
        outline: 0;
        padding: 8px;
        border-radius: 16px;
    }
    QListWidget#SettingsMenu::item {
        background: transparent;
        color: #4a4d45;
        padding: 10px 12px;
        border-radius: 12px;
        margin: 4px 0px;
        font-weight: 600;
    }
    QListWidget#SettingsMenu::item:hover {
        background: #f4f2ec;
    }
    QListWidget#SettingsMenu::item:selected {
        background: #ecebfb;
        color: #4a3f9e;
        border-left: 4px solid #b9b6f0;
        padding-left: 8px;
        font-weight: 700;
    }
    """


def load_settings_page_dark_styles() -> str:
    return """
    QLineEdit#SettingsInput {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid rgba(148,163,184,0.25);
        border-radius: 10px;
        padding: 8px 10px;
        min-height: 18px;
    }
    QLineEdit#SettingsInput:focus {
        border: 1px solid rgba(59,130,246,0.55);
    }
    QCheckBox#NotificationRuleToggle {
        /* Indent child notification toggles (RTL: margin-right pushes left) */
        margin-right: 24px;
    }

    QPushButton#SaveButton {
        background: #2563eb;
        border: 1px solid #1d4ed8;
        font-weight: 600;
        min-width: 96px;
        color: #ffffff;
    }
    QPushButton#SaveButton:hover {
        background: #3b82f6;
        border: 1px solid #2563eb;
    }
    QPushButton#SaveButton:pressed {
        background: #1d4ed8;
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
        background: #0f172a;
        color: #60a5fa;
        border-left: 4px solid #3b82f6;
        padding-left: 8px;
        font-weight: 700;
    }
    """
