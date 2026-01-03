from __future__ import annotations


def load_cards_light_styles() -> str:
    return """
    QWidget#ChartCard, QWidget#TotalsCard, QWidget#StatCard {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
    }
    QWidget#StatCardGreen {
        background: #22c55e;
        border: 1px solid #22c55e;
        border-radius: 20px;
    }
    QWidget#StatCardRed {
        background: #ef4444;
        border: 1px solid #ef4444;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #6366f1;
        border: 1px solid #6366f1;
        border-radius: 20px;
    }
    QWidget#StatCardYellow {
        background: #fbbf24;
        border: 1px solid #f59e0b;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *, QWidget#StatCardPurple * {
        background: transparent;
    }
    QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle, QWidget#StatCardPurple QLabel#Subtitle {
        color: #0f172a;
    }
    QWidget#StatCardYellow QLabel#Subtitle {
        color: #0f172a;
    }
    QWidget#PageCard {
        background: #dbeafe;
        border: none;
        border-radius: 16px;
    }
    QWidget#PageCard * {
        background: transparent;
    }
    """


def load_cards_dark_styles() -> str:
    return """
    QWidget#StatCardGreen {
        background: #16a34a;
        border: 1px solid #16a34a;
        border-radius: 20px;
    }
    QWidget#StatCardRed {
        background: #dc2626;
        border: 1px solid #dc2626;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #4f46e5;
        border: 1px solid #4f46e5;
        border-radius: 20px;
    }
    QWidget#StatCardYellow {
        background: #f59e0b;
        border: 1px solid #f59e0b;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *, QWidget#StatCardPurple * {
        background: transparent;
    }
    QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle, QWidget#StatCardPurple QLabel#Subtitle {
        color: #0f172a;
    }
    QWidget#StatCardGreen QLabel#StatValueLarge, QWidget#StatCardRed QLabel#StatValueLarge, QWidget#StatCardPurple QLabel#StatValueLarge {
        color: #e5e7eb;
    }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle, QWidget#StatCardPurple QLabel#Subtitle {
        color: #f8fafc;
    }
    QWidget#StatCardYellow QLabel#StatValueLarge, QWidget#StatCardYellow QLabel#StatValueCard {
        color: #0b1220;
    }
    QWidget#StatCardYellow QLabel#Subtitle, QWidget#StatCardYellow QLabel#StatTitle {
        color: #0b1220;
    }
    """
