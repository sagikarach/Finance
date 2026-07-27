from __future__ import annotations


def load_sidebar_light_styles() -> str:
    return """
    QWidget#Sidebar {
        background: #ffffff;
        border-radius: 12px;
    }
    QWidget#Sidebar * {
        background: transparent;
    }
    QLabel#UserName {
        font-size: 16px;
        font-weight: 600;
        color: #0f172a;
        margin-top: 4px;
    }
    QToolButton#FirebaseAccountMenuButton {
        background: transparent;
        color: #0f172a;
        border: none;
        font-size: 16px;
        font-weight: 700;
        padding: 0px 4px;
        margin-top: 4px;
    }
    QToolButton#FirebaseAccountMenuButton:hover {
        background: rgba(185, 182, 240, 0.35);
        border-radius: 6px;
    }
    QLabel#AvatarCircle {
        width: 72px;
        height: 72px;
        border-radius: 36px;
        background: #ffffff;
        border: 2px solid #b9b6f0;
        color: #0f172a;
        font-size: 26px;
        font-weight: 800;
    }
    QPushButton#SidebarNavButton {
        background: #ffffff;
        color: #0f172a;
        padding: 10px 16px;
        border-radius: 0px;
        border-top: 2px solid transparent;
        border-bottom: 2px solid transparent;
        border-left: none;
        border-right: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButton:hover {
        background: #f1efe7;
    }
    QPushButton#SidebarNavButton:checked,
    QPushButton#SidebarNavButton:pressed {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: 1px solid #ffffff;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButton[collapsibleExpanded="true"] {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: none;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: 1px solid #ffffff;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButtonSavings {
        background: #ffffff;
        color: #0f172a;
        padding: 10px 16px;
        border-radius: 0px;
        border-top: 2px solid transparent;
        border-bottom: 2px solid transparent;
        border-left: none;
        border-right: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButtonSavings:hover {
        background: #f1efe7;
    }
    QPushButton#SidebarNavButtonSavings:checked,
    QPushButton#SidebarNavButtonSavings:pressed {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: 1px solid #ffffff;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButtonSavings[collapsibleExpanded="true"] {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: none;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButtonSavings:disabled {
        background: #deddf8;
        color: #4b4980;
        border-top: 1px solid #ffffff;
        border-bottom: 1px solid #ffffff;
        border-right: none;
        border-left: 4px solid #b9b6f0;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavToggle {
        background: #f1efe7;
        color: #0f172a;
        padding: 10px 8px;
        border-radius: 0px;
        border-top: 2px solid #e6e3f5;
        border-bottom: 2px solid #e6e3f5;
        border-left: none;
        border-right: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavToggle:hover {
        background: #f1efe7;
    }
    QPushButton#SidebarNavToggle:checked {
        background: #f1efe7;
        border-bottom: none;
    }
    QPushButton#SidebarNavSubButton {
        background: transparent;
        color: #0f172a;
        padding: 8px 16px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
    }
    QPushButton#SidebarNavSubButton:hover {
        background: rgba(185, 182, 240, 0.5);
    }
    QWidget#SidebarActions {
        background: #ffffff;
        border-radius: 12px;
        min-height: 130px;
        padding: 8px 8px 0px 8px;
    }
    QWidget#SidebarActions QPushButton {
        background: transparent;
        color: #0f172a;
        padding: 10px 14px;
        min-height: 40px;
        margin-bottom: 8px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QWidget#SidebarActions QPushButton:hover {
        background: rgba(185, 182, 240, 0.35);
    }
    QWidget#SidebarActions QPushButton:pressed {
        background: #deddf8;
    }
    /* Income = green, Outcome = clay (pastel accents). Scoped under the parent
       id so they outrank the generic "#SidebarActions QPushButton" rule. */
    QWidget#SidebarActions QPushButton#SidebarIncomeButton {
        background: #2f9e68;
        color: #ffffff;
        font-weight: 800;
        border: none;
        border-radius: 14px;
        padding: 12px 14px;
        min-height: 40px;
    }
    QWidget#SidebarActions QPushButton#SidebarIncomeButton:hover { background: #278a59; }
    QWidget#SidebarActions QPushButton#SidebarIncomeButton:pressed { background: #226f49; }
    QWidget#SidebarActions QPushButton#SidebarOutcomeButton {
        background: #d66a4e;
        color: #ffffff;
        font-weight: 800;
        border: none;
        border-radius: 14px;
        padding: 12px 14px;
        min-height: 40px;
    }
    QWidget#SidebarActions QPushButton#SidebarOutcomeButton:hover { background: #c25a40; }
    QWidget#SidebarActions QPushButton#SidebarOutcomeButton:pressed { background: #a94c34; }
    """


def load_sidebar_dark_styles() -> str:
    return """
    QWidget#Sidebar {
        background: #111827;
        border-radius: 12px;
    }
    QWidget#Sidebar * {
        background: transparent;
        color: #e5e7eb;
    }
    QLabel#AvatarCircle {
        width: 72px;
        height: 72px;
        border-radius: 36px;
        background: #111827;
        border: 2px solid #4b5563;
        color: #e5e7eb;
        font-size: 26px;
        font-weight: 800;
    }
    QPushButton#SidebarNavButton {
        background: #111827;
        color: #e5e7eb;
        padding: 10px 16px;
        border-radius: 0px;
        border-top: 2px solid transparent;
        border-bottom: 2px solid transparent;
        border-left: none;
        border-right: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButton:hover {
        background: #1f2937;
    }
    QPushButton#SidebarNavButton:checked,
    QPushButton#SidebarNavButton:pressed {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: 1px solid #1e3a5f;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButton[collapsibleExpanded="true"] {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: none;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: 1px solid #1e3a5f;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavToggle {
        background: #020617;
        color: #e5e7eb;
        padding: 10px 8px;
        border-radius: 0px;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        border-left: none;
        border-right: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavToggle:hover {
        background: #1f2937;
    }
    QPushButton#SidebarNavToggle:checked {
        background: #020617;
        border-bottom: none;
    }
    QPushButton#SidebarNavSubButton {
        background: transparent;
        color: #e5e7eb;
        padding: 8px 16px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
    }
    QPushButton#SidebarNavSubButton:hover {
        background: rgba(31, 41, 55, 0.5);
    }
    QWidget#SidebarActions {
        background: #111827;
        border-radius: 12px;
        min-height: 120px;
        padding: 8px 8px 0px 8px;
    }
    QWidget#SidebarActions QPushButton {
        background: transparent;
        color: #e5e7eb;
        padding: 10px 14px;
        min-height: 40px;
        margin-bottom: 8px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QWidget#SidebarActions QPushButton:hover {
        background: rgba(15, 23, 42, 0.6);
    }
    QWidget#SidebarActions QPushButton:pressed {
        background: #020617;
    }
    QLabel#UserName {
        font-size: 16px;
        font-weight: 600;
        color: #e5e7eb;
        margin-top: 4px;
    }
    QToolButton#FirebaseAccountMenuButton {
        background: transparent;
        color: #e5e7eb;
        border: none;
        font-size: 16px;
        font-weight: 700;
        padding: 0px 4px;
        margin-top: 4px;
    }
    QToolButton#FirebaseAccountMenuButton:hover {
        background: rgba(15, 23, 42, 0.6);
        border-radius: 6px;
    }
    QPushButton#SidebarNavButtonSavings {
        background: #111827;
        color: #e5e7eb;
        padding: 10px 16px;
        border-radius: 0px;
        border-top: 2px solid transparent;
        border-bottom: 2px solid transparent;
        border-left: none;
        border-right: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButtonSavings:hover {
        background: #1f2937;
    }
    QPushButton#SidebarNavButtonSavings:checked,
    QPushButton#SidebarNavButtonSavings:pressed {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: 1px solid #1e3a5f;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButtonSavings[collapsibleExpanded="true"] {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: none;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    QPushButton#SidebarNavButtonSavings:disabled {
        background: #0f172a;
        color: #60a5fa;
        border-top: 1px solid #1e3a5f;
        border-bottom: 1px solid #1e3a5f;
        border-right: none;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px 10px 12px;
        font-weight: 700;
    }
    """
