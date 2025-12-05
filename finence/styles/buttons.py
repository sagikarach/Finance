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
