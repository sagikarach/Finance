from __future__ import annotations


def load_base_light_styles() -> str:
    """Base styles shared across all pages in light mode."""
    return """
    /* Base */
    QWidget {
        background: #dbeafe; /* light blue app background */
        color: #111827; /* near-black */
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial, sans-serif;
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
        background: #bfdbfe; /* slightly brighter, still darker than background */
        border-radius: 12px;
    }
    QWidget#Sidebar * {
        background: transparent; /* avoid lighter blocks under title or icons */
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
        border-radius: 36px; /* perfect circle */
        background: #bfdbfe; /* light blue circle */
        border: 2px solid #93c5fd;
        color: #0f172a;
        font-size: 26px;
        font-weight: 800;
    }
    QPushButton#SidebarNavButton {
        background: #bfdbfe; /* Same as Sidebar background */
        color: #0f172a;
        padding: 10px 16px;
        border-radius: 0px; /* No border radius to match sidebar edges */
        border: none;
        border-top: none;
        border-bottom: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButton:hover {
        background: #c9e1fe; /* Lighter blue for hover, between normal and pressed */
    }
    QPushButton#SidebarNavButton:checked,
    QPushButton#SidebarNavButton:pressed {
        background: #dcecff; /* Darker blue for pressed effect */
        color: #0f172a;
        border-top: 2px solid #a0bce2; /* Darker blue border on top */
        border-bottom: 2px solid #a0bce2; /* Darker blue border on bottom */
        border-left: none;
        border-right: none;
        padding: 8px 14px;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #dbeafe;
        color: #0f172a;
        border-top: 2px solid #a0bce2; /* Darker blue border on top */
        border-bottom: 2px solid #a0bce2; /* Darker blue border on bottom */
        border-left: none;
        border-right: none;
        padding: 8px 14px;
    }
    /* Page wrapper */
    QWidget#PageCard {
        background: #dbeafe; /* light blue */
        border: none;
        border-radius: 16px;
    }
    QWidget#PageCard * {
        background: transparent; /* ensure no child paints white */
    }

    /* Buttons */
    QPushButton {
        background: #2563eb; /* blue-600 */
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
        font-family: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", "Varela Round", "Arial Hebrew", Arial, sans-serif;
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
        font-family: "Varela Round", "Arial Hebrew", ".SF Hebrew", Arial, sans-serif;
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
        background: #111827; /* Same as Sidebar background */
        color: #e5e7eb;
        padding: 10px 16px;
        border-radius: 0px; /* No border radius to match sidebar edges */
        border: none;
        font-size: 16px;
        font-weight: 600;
        text-align: center;
    }
    QPushButton#SidebarNavButton:hover {
        background: #1f2937; /* Lighter gray for hover, between normal and pressed */
    }
    QPushButton#SidebarNavButton:checked,
    QPushButton#SidebarNavButton:pressed {
        background: #020617; /* App background color for pressed effect */
        color: #e5e7eb;
        padding: 8px 14px;
    }
    QPushButton#SidebarNavButton:disabled {
        background: #020617; /* App background color */
        color: #e5e7eb;
        padding: 8px 14px;
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
