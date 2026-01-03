from __future__ import annotations


def load_typography_light_styles() -> str:
    return """
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
    """


def load_typography_dark_styles() -> str:
    return """
    QLabel#HeaderTitle, QLabel#Title {
        font-size: 28px;
        font-weight: 800;
        color: #e5e7eb;
    }
    QLabel#Subtitle {
        font-size: 16px;
        color: #9ca3af;
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
    """
