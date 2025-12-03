from __future__ import annotations


def load_base_light_styles() -> str:
    """Base styles shared across all pages in light mode."""
    return """
    /* Base */
    QWidget {
        background: #dbeafe; /* light blue app background */
        color: #111827; /* near-black */
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial;
    }
    QMainWindow {
        background: #dbeafe; /* match app background */
    }

    /* Menus */
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

    /* Typography */
    QLabel#Title {
        font-size: 28px;
        font-weight: 800;
        color: #0b1220;
        padding-bottom: 2px;
    }
    QLabel#HeaderTitle {
        font-size: 28px;
        font-weight: 800;
        color: #0b1220;
    }
    QLabel#Subtitle {
        font-size: 16px;
        color: #475569;
    }
    QLabel#StatValue {
        font-size: 18px;
        font-weight: 700;
        color: #0b1220;
        padding: 10px 12px;
        border-radius: 10px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }

    /* Cards */
    QWidget#ChartCard, QWidget#TotalsCard, QWidget#StatCard {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
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
        min-width: 72px;
        min-height: 72px;
        max-width: 72px;
        max-height: 72px;
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
        /* Keep constant border thickness (transparent by default)
           so height doesn't change when pressed. */
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
        /* Constant border thickness (transparent by default) */
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
        /* Keep same padding as normal state to avoid height jump */
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
        background: #bfdbfe;
        color: #0f172a;
        padding: 10px 8px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavToggle:hover {
        background: #c9e1fe;
    }
    QPushButton#SidebarNavToggle:checked {
        background: #c9e1fe;
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
    /* Page wrapper */
    QWidget#PageCard {
        background: #dbeafe;
        border: none;
        border-radius: 16px;
    }
    QWidget#PageCard * {
        background: transparent;
    }

    /* Buttons */
    QPushButton {
        background: #2563eb;
        color: white;
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #1d4ed8;
    }
    QToolButton#IconButton {
        background: transparent;
        border: none;
        padding: 6px;
        font-size: 18px;
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
        font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Varela Round", "Arial Hebrew", Arial;
    }
    QToolButton#IconButton:hover {
        background: rgba(0,0,0,0.05);
        border-radius: 8px;
    }
    QToolButton#PasswordEye {
        background: transparent;
        border: none;
        padding: 4px;
        font-size: 16px;
        color: #111827;
    }
    QToolButton#PasswordEye:hover {
        background: rgba(0,0,0,0.05);
        border-radius: 8px;
    }
    QPushButton:hover {
        background: #1d4ed8;
    }
    QPushButton:pressed {
        background: #1e40af;
    }
    """


def load_base_dark_styles() -> str:
    """Base styles shared across all pages in dark mode."""
    return """
    QWidget {
        background: #020617;
        color: #e5e7eb;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial;
    }
    QMainWindow {
        background: #020617;
    }
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
    QLabel#HeaderTitle, QLabel#Title {
        font-size: 28px;
        font-weight: 800;
        color: #e5e7eb;
    }
    QLabel#Subtitle {
        font-size: 16px;
        color: #9ca3af;
    }
    QWidget#Sidebar {
        background: #111827;
        border-radius: 12px;
    }
    QWidget#Sidebar * {
        background: transparent;
        color: #e5e7eb;
    }
    QLabel#AvatarCircle {
        border: 2px solid #4b5563;
        color: #e5e7eb;
    }
    QPushButton#SidebarNavButton {
        background: #111827;
        color: #e5e7eb;
        padding: 10px 16px;
        border-radius: 0px;
        /* Constant border thickness (transparent by default) */
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
    QPushButton#SidebarNavButton:disabled {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
    }
    QPushButton#SidebarNavToggle {
        background: #111827;
        color: #e5e7eb;
        padding: 10px 8px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavToggle:hover {
        background: #1f2937; /* Same as SidebarNavButton:hover */
    }
    QPushButton#SidebarNavSubButton {
        background: transparent; /* Transparent to show container's pressed background */
        color: #e5e7eb;
        padding: 8px 16px;
        border-radius: 0px;
        border: none;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
    }
    QPushButton#SidebarNavSubButton:hover {
        background: rgba(31, 41, 55, 0.5); /* Semi-transparent hover */
    }
    QLabel#StatValue {
        font-size: 18px;
        font-weight: 700;
        color: #e5e7eb;
        padding: 10px 12px;
        border-radius: 10px;
        background: #1f2937;
        border: 1px solid #374151;
    }
    QLabel#UserName {
        font-size: 16px;
        font-weight: 600;
        color: #e5e7eb;
        margin-top: 4px;
    }
    /* Dark mode savings button (SidebarNavButtonSavings) matches sidebar nav button */
    QPushButton#SidebarNavButtonSavings {
        background: #111827;
        color: #e5e7eb;
        padding: 10px 16px;
        border-radius: 0px;
        /* Constant border thickness, initially transparent */
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
    QPushButton#SidebarNavButtonSavings:disabled {
        background: #020617;
        color: #e5e7eb;
        border-top: 2px solid #1f2937;
        border-bottom: 2px solid #1f2937;
        padding: 10px 16px;
    }
    QPushButton {
        background: #1d4ed8;
        color: #e5e7eb;
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #1e3a8a;
    }
    QPushButton:hover {
        background: #2563eb;
    }
    QPushButton:pressed {
        background: #1e40af;
    }
    QToolButton#IconButton,
    QToolButton#PasswordEye {
        background: transparent;
        border: none;
        padding: 6px;
        font-size: 18px;
        color: #e5e7eb;
    }
    QToolButton#IconButton {
        min-width: 32px;
        max-width: 32px;
        min-height: 32px;
        max-height: 32px;
    }
    QToolButton#IconButton:hover,
    QToolButton#PasswordEye:hover {
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
    }
    """
