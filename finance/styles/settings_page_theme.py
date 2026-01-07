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
        border: 1px solid rgba(59,130,246,0.65);
    }
    QCheckBox#NotificationRuleToggle {
        /* Indent child notification toggles (RTL: margin-right pushes left) */
        margin-right: 24px;
    }

    QPushButton#SaveButton {
        background: #e5e7eb; /* grey */
        border: 1px solid rgba(15,23,42,0.18);
        font-weight: 600;
        min-width: 96px;
        color: #111827;
    }
    QPushButton#SaveButton:hover {
        background: #d1d5db;
    }
    QPushButton#SaveButton:pressed {
        background: #cbd5e1;
    }

    QPushButton#SecondaryButton {
        background: #e5e7eb; /* grey */
        border: 1px solid rgba(15,23,42,0.18);
        font-weight: 600;
        min-width: 96px;
        color: #0f172a;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#SecondaryButton:hover {
        background: #d1d5db;
        border: 1px solid rgba(15,23,42,0.25);
    }
    QPushButton#SecondaryButton:pressed {
        background: #cbd5e1;
    }

    QPushButton#DangerButton {
        background: #e5e7eb; /* grey */
        border: 1px solid rgba(239,68,68,0.55);
        font-weight: 700;
        min-width: 96px;
        color: #b91c1c;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#DangerButton:hover {
        background: #d1d5db;
    }
    QPushButton#DangerButton:pressed {
        background: #cbd5e1;
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
    QLineEdit#SettingsInput {
        background: #0b1220;
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
        background: #374151; /* grey */
        border: 1px solid rgba(148,163,184,0.25);
        font-weight: 600;
        min-width: 96px;
        color: #e5e7eb;
    }
    QPushButton#SaveButton:hover {
        background: #4b5563;
        border: 1px solid rgba(148,163,184,0.35);
    }
    QPushButton#SaveButton:pressed {
        background: #334155;
    }

    QPushButton#SecondaryButton {
        background: #374151; /* grey */
        border: 1px solid rgba(148,163,184,0.25);
        font-weight: 600;
        min-width: 96px;
        color: #e5e7eb;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#SecondaryButton:hover {
        background: #4b5563;
        border: 1px solid rgba(148,163,184,0.35);
    }
    QPushButton#SecondaryButton:pressed {
        background: #334155;
    }

    QPushButton#DangerButton {
        background: #374151; /* grey */
        border: 1px solid rgba(239,68,68,0.55);
        font-weight: 700;
        min-width: 96px;
        color: #fecaca;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#DangerButton:hover {
        background: #4b5563;
        border: 1px solid rgba(239,68,68,0.65);
    }
    QPushButton#DangerButton:pressed {
        background: #334155;
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
