from __future__ import annotations


def load_cards_light_styles() -> str:
    return """
    QWidget#ChartCard, QWidget#TotalsCard, QWidget#StatCard {
        background: #e8f3fd;
        border: 1px solid #c7dffe;
        border-radius: 12px;
    }
    QWidget#StatCardGreen {
        background: #dcfce7;
        border: 1px solid #86efac;
        border-radius: 20px;
    }
    QWidget#StatCardRed {
        background: #fee2e2;
        border: 1px solid #fca5a5;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #e0e7ff;
        border: 1px solid #a5b4fc;
        border-radius: 20px;
    }
    QWidget#StatCardYellow {
        background: #fef9c3;
        border: 1px solid #fde047;
        border-radius: 20px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *,
    QWidget#StatCardPurple *, QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel {
        color: #166534;
        background: transparent;
    }
    QWidget#StatCardRed QLabel {
        color: #b91c1c;
        background: transparent;
    }
    QWidget#StatCardPurple QLabel {
        color: #4338ca;
        background: transparent;
    }
    QWidget#StatCardYellow QLabel {
        color: #854d0e;
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#Subtitle {
        color: rgba(22,101,52,0.70);
    }
    QWidget#StatCardRed QLabel#Subtitle {
        color: rgba(185,28,28,0.70);
    }
    QWidget#StatCardPurple QLabel#Subtitle {
        color: rgba(67,56,202,0.70);
    }
    QWidget#StatCardYellow QLabel#Subtitle {
        color: rgba(133,77,14,0.70);
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
    QWidget#AssetTablePanel {
        background: #e8f3fd;
        border: 1px solid #c7dffe;
        border-top: none;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }
    QWidget#AssetTablePanel * {
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
    QWidget#AssetTablePanel {
        background: #111827;
        border: 1px solid #1e293b;
        border-top: none;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }
    QWidget#AssetTablePanel * {
        background: transparent;
    }
    """
