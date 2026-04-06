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
        border: 1px solid #87aeda;
        border-radius: 10px;
        padding: 8px 12px;
    }
    QPushButton#MonthEditButton:hover {
        background: #bfdbfe;
        border: 1px solid #6baed6;
    }
    QPushButton#MonthEditButton:pressed {
        background: #87aeda;
        border: 1px solid #5b9fcc;
    }
    QPushButton:hover {
        background: #1d4ed8;
    }
    QPushButton:pressed {
        background: #1e40af;
    }
    QPushButton:focus {
        outline: 2px solid #93c5fd;
        outline-offset: 2px;
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
        color: #0f172a;
    }
    QToolButton#EventSelectorButton::menu-indicator {
        image: none;
        width: 0px;
        height: 0px;
    }
    QPushButton#SecondaryButton {
        background: #e2eeff;
        border: 1px solid #bfdbfe;
        font-weight: 600;
        color: #1e40af;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#SecondaryButton:hover {
        background: #dbeafe;
        border: 1px solid #93c5fd;
    }
    QPushButton#SecondaryButton:pressed {
        background: #bfdbfe;
    }
    QPushButton#DangerButton {
        background: #fee2e2;
        border: 1px solid #fca5a5;
        font-weight: 700;
        color: #b91c1c;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#DangerButton:hover {
        background: #fecaca;
        border: 1px solid #f87171;
    }
    QPushButton#DangerButton:pressed {
        background: #fca5a5;
    }
    QPushButton#RangeBtn {
        background: transparent;
        color: #6b7280;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 12px;
        min-width: 32px;
        max-height: 24px;
    }
    QPushButton#RangeBtn:hover {
        background: #f3f4f6;
        border-color: #9ca3af;
    }
    QPushButton#RangeBtn:checked {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
        font-weight: 600;
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
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 8px 12px;
    }
    QPushButton#MonthEditButton:hover {
        background: #1f2937;
        border: 1px solid #475569;
    }
    QPushButton#MonthEditButton:pressed {
        background: #0f172a;
        border: 1px solid #64748b;
    }
    QPushButton:hover {
        background: #2563eb;
    }
    QPushButton:pressed {
        background: #1e40af;
    }
    QPushButton:focus {
        outline: 2px solid #3b82f6;
        outline-offset: 2px;
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
    QPushButton#SecondaryButton {
        background: #1e293b;
        border: 1px solid #334155;
        font-weight: 600;
        color: #93c5fd;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#SecondaryButton:hover {
        background: #273549;
        border: 1px solid #475569;
    }
    QPushButton#SecondaryButton:pressed {
        background: #0f172a;
    }
    QPushButton#DangerButton {
        background: #3f1515;
        border: 1px solid #7f1d1d;
        font-weight: 700;
        color: #fca5a5;
        padding: 8px 14px;
        border-radius: 8px;
    }
    QPushButton#DangerButton:hover {
        background: #4c1a1a;
        border: 1px solid #991b1b;
    }
    QPushButton#DangerButton:pressed {
        background: #290d0d;
    }
    QPushButton#RangeBtn {
        background: transparent;
        color: #9ca3af;
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 12px;
        min-width: 32px;
        max-height: 24px;
    }
    QPushButton#RangeBtn:hover {
        background: #1f2937;
        border-color: #4b5563;
    }
    QPushButton#RangeBtn:checked {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
        font-weight: 600;
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
