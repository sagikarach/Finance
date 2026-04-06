from __future__ import annotations


def load_cards_light_styles() -> str:
    return """
    QWidget#ChartCard, QWidget#TotalsCard, QWidget#StatCard {
        background: #e8f3fd;
        border: 1px solid #c7dffe;
        border-radius: 12px;
    }
    QWidget#StatCardGreen {
        background: #4ade80;
        border: 1px solid #22c55e;
        border-radius: 20px;
    }
    QWidget#StatCardRed {
        background: #f87171;
        border: 1px solid #ef4444;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #818cf8;
        border: 1px solid #6366f1;
        border-radius: 20px;
    }
    QWidget#StatCardYellow {
        background: #fcd34d;
        border: 1px solid #fbbf24;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *,
    QWidget#StatCardPurple *, QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardRed QLabel,
    QWidget#StatCardPurple QLabel, QWidget#StatCardYellow QLabel {
        color: #0f172a;
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle,
    QWidget#StatCardPurple QLabel#Subtitle, QWidget#StatCardYellow QLabel#Subtitle {
        color: rgba(15,23,42,0.65);
    }
    QWidget#PageCard {
        background: transparent;
        border: none;
        border-radius: 16px;
    }
    QWidget#PageCard * {
        background: transparent;
    }
    QWidget#ContentPanel {
        background: #e8f3fd;
        border: 1px solid #c7dffe;
        border-radius: 12px;
    }
    QWidget#ContentPanel * {
        background: transparent;
    }
    """


def load_cards_dark_styles() -> str:
    return """
    QWidget#StatCardGreen {
        background: #16a34a;
        border: 1px solid #15803d;
        border-radius: 20px;
    }
    QWidget#StatCardRed {
        background: #dc2626;
        border: 1px solid #b91c1c;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #4f46e5;
        border: 1px solid #4338ca;
        border-radius: 20px;
    }
    QWidget#StatCardYellow {
        background: #d97706;
        border: 1px solid #b45309;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *,
    QWidget#StatCardPurple *, QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardRed QLabel,
    QWidget#StatCardPurple QLabel, QWidget#StatCardYellow QLabel {
        color: #ffffff;
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle,
    QWidget#StatCardPurple QLabel#Subtitle, QWidget#StatCardYellow QLabel#Subtitle {
        color: rgba(255,255,255,0.75);
    }
    QWidget#ContentPanel {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 12px;
    }
    QWidget#ContentPanel * {
        background: transparent;
    }
    """
