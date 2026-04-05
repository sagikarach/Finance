from __future__ import annotations


def load_typography_light_styles() -> str:
    return """
    QLabel#Title {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
        padding-bottom: 2px;
    }
    QLabel#HeaderTitle {
        font-size: 28px;
        font-weight: 800;
        color: #0f172a;
    }
    QLabel#Subtitle {
        font-size: 16px;
        color: #475569;
    }
    QLabel#StatValue {
        font-size: 18px;
        font-weight: 700;
        color: #0f172a;
        padding: 10px 12px;
        border-radius: 10px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
    }
    QLabel#ErrorLabel {
        font-size: 13px;
        font-weight: 600;
        color: #dc2626;
        background: transparent;
    }
    QLabel#ExpenseHeader {
        font-size: 15px;
        font-weight: 700;
        color: #0f172a;
        background: transparent;
    }
    QLabel#AiSuggestionLabel {
        font-size: 13px;
        font-weight: 600;
        color: #1d4ed8;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 6px;
        padding: 4px 8px;
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
    QLabel#ErrorLabel {
        font-size: 13px;
        font-weight: 600;
        color: #f87171;
        background: transparent;
    }
    QLabel#ExpenseHeader {
        font-size: 15px;
        font-weight: 700;
        color: #e5e7eb;
        background: transparent;
    }
    QLabel#AiSuggestionLabel {
        font-size: 13px;
        font-weight: 600;
        color: #93c5fd;
        background: #1e3a5f;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        padding: 4px 8px;
    }
    """
