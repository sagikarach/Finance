from __future__ import annotations


def load_sidebar_light_styles() -> str:
    return """
    QWidget#Sidebar {
        background: #bfdbfe;
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
    QLabel#AvatarCircle {
        width: 72px;
        height: 72px;
        border-radius: 36px;
        background: #bfdbfe;
        border: 2px solid #93c5fd;
        color: #0f172a;
        font-size: 26px;
        font-weight: 800;
    }
    QPushButton#SidebarNavButton {
        background: #bfdbfe;
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
        background: #c9e1fe;
    }
    QPushButton#SidebarNavButton:checked,
    QPushButton#SidebarNavButton:pressed {
        background: #dcecff;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: 2px solid #a0bce2;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButton[collapsibleExpanded="true"] {
        background: #dcecff;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: none;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #dbeafe;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: 2px solid #a0bce2;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButtonSavings {
        background: #bfdbfe;
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
        background: #c9e1fe;
    }
    QPushButton#SidebarNavButtonSavings:checked,
    QPushButton#SidebarNavButtonSavings:pressed {
        background: #dcecff;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: 2px solid #a0bce2;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButtonSavings[collapsibleExpanded="true"] {
        background: #dcecff;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: none;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButtonSavings:disabled {
        background: #dbeafe;
        color: #0f172a;
        border-top: 2px solid #a0bce2;
        border-bottom: 2px solid #a0bce2;
        border-left: none;
        border-right: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavToggle {
        background: #dcecff;
        color: #0f172a;
        padding: 10px 8px;
        border-radius: 0px;
        border-top: 2px solid #a0bce2;
        border-bottom: 2px solid #a0bce2;
        border-left: none;
        border-right: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavToggle:hover {
        background: #c9e1fe;
    }
    QPushButton#SidebarNavToggle:checked {
        background: #dcecff;
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
        background: rgba(201, 225, 254, 0.5);
    }
    QWidget#SidebarActions {
        background: #bfdbfe;
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
        background: rgba(201, 225, 254, 0.35);
    }
    QWidget#SidebarActions QPushButton:pressed {
        background: #dbeafe;
    }
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
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButton[collapsibleExpanded="true"] {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
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
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButtonSavings[collapsibleExpanded="true"] {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: none;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavButtonSavings:disabled {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
    }
    """
