from __future__ import annotations


def load_default_stylesheet() -> str:
    return """
    /* Base */
    QWidget {
        background: #dbeafe; /* light blue app background */
        color: #111827; /* near-black */
        font-size: 14px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
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
    /* Page wrapper */
    QWidget#PageCard {
        background: #dbeafe; /* light blue */
        border: none;
        border-radius: 16px;
    }
    QWidget#PageCard * {
        background: transparent; /* ensure no child paints white */
    }
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        letter-spacing: .2px;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #0b1220;
        padding: 6px 8px;
    }
    /* Colored stat cards */
    QWidget#StatCardGreen {
        background: #22c55e; /* green-500 */
        border: none;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #6366f1; /* indigo-500 */
        border: none;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardPurple * {
        background: transparent; /* avoid white fill from descendants */
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardPurple QLabel {
        color: #0b1220;
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
    }
    QToolButton#IconButton:hover {
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
