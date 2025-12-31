from __future__ import annotations


def load_buttons_light_styles() -> str:
    return """
    QPushButton {
        background: #2563eb;
        color: white;
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #1d4ed8;
    }
    QPushButton#MonthEditButton {
        background: #d1e6ff;
        color: #0f172a;
        border: 1px solid #87aeda important;
        border-radius: 10px;
        padding: 8px 12px;
    }
    QPushButton#MonthEditButton:hover {
        background: #bfdbfe;
        border: 1px solid #87aeda important;
    }
    QPushButton#MonthEditButton:pressed {
        background: #87aeda;
        border: 1px solid #87aeda important;
    }
    QPushButton:hover {
        background: #1d4ed8;
    }
    QPushButton:pressed {
        background: #1e40af;
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
        font-family: "Apple Color Emoji", "Varela Round", "Arial Hebrew", Arial;
    }
    QToolButton#IconButton:hover {
        background: rgba(0,0,0,0.05);
        border-radius: 8px;
    }
    QToolButton#HeaderIconButton {
        background: transparent;
        border: none;
        padding: 0px;
        font-size: 18px;
        min-width: 44px;
        max-width: 44px;
        min-height: 44px;
        max-height: 44px;
        font-family: "Apple Color Emoji", "Varela Round", "Arial Hebrew", Arial;
    }
    QToolButton#HeaderIconButton:hover {
        background: rgba(0,0,0,0.05);
        border-radius: 10px;
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
    QToolButton#EventSelectorButton {
        background: transparent;
        border: none;
        padding: 4px 8px;
        font-size: 22px;
        font-weight: 800;
        color: #0b1220;
    }
    QToolButton#EventSelectorButton::menu-indicator {
        image: none;
        width: 0px;
        height: 0px;
    }
    QLabel#NotificationsBadge {
        background: #ef4444;
        color: white;
        border-radius: 8px;
        min-width: 16px;
        min-height: 16px;
        font-size: 10px;
        padding: 0px;
    }
    """


def load_buttons_dark_styles() -> str:
    return """
    QPushButton {
        background: #1d4ed8;
        color: #e5e7eb;
        padding: 8px 14px;
        border-radius: 8px;
        border: 1px solid #1e3a8a;
    }
    QPushButton#MonthEditButton {
        background: #111827;
        color: #e5e7eb;
        border: 1px solid #334155 important;
        border-radius: 10px;
        padding: 8px 12px;
    }
    QPushButton#MonthEditButton:hover {
        background: #1f2937;
        border: 1px solid #475569 important;
    }
    QPushButton#MonthEditButton:pressed {
        background: #0b1220;
        border: 1px solid #64748b important;
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
    QToolButton#HeaderIconButton {
        background: transparent;
        border: none;
        padding: 0px;
        font-size: 18px;
        min-width: 44px;
        max-width: 44px;
        min-height: 44px;
        max-height: 44px;
        color: #e5e7eb;
        font-family: "Apple Color Emoji", "Varela Round", "Arial Hebrew", Arial;
    }
    QToolButton#HeaderIconButton:hover {
        background: rgba(255,255,255,0.06);
        border-radius: 10px;
    }
    QToolButton#IconButton:hover,
    QToolButton#PasswordEye:hover {
        background: rgba(255,255,255,0.06);
        border-radius: 8px;
    }
    QToolButton#EventSelectorButton {
        background: transparent;
        border: none;
        padding: 4px 8px;
        font-size: 22px;
        font-weight: 800;
        color: #e5e7eb;
    }
    QToolButton#EventSelectorButton::menu-indicator {
        image: none;
        width: 0px;
        height: 0px;
    }
    QLabel#NotificationsBadge {
        background: #ef4444;
        color: white;
        border-radius: 8px;
        min-width: 16px;
        min-height: 16px;
        font-size: 10px;
        padding: 0px;
    }
    """
