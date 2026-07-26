from __future__ import annotations


def load_cards_light_styles() -> str:
    return """
    QWidget#ChartCard, QWidget#TotalsCard, QWidget#StatCard {
        background: #e8f3fd;
        border: 1px solid #c7dffe;
        border-radius: 12px;
    }
    /* כרטיסי סטטיסטיקה — עיצוב אחיד בסגנון "hero": כרטיס ניטרלי, כותרת
       קטנה ומעומעמת, וערך גדול הצבוע לפי המשמעות (ירוק=כסף, אדום=חוב וכו'). */
    QWidget#StatCardGreen, QWidget#StatCardRed,
    QWidget#StatCardPurple, QWidget#StatCardYellow {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *,
    QWidget#StatCardPurple *, QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#StatTitle, QWidget#StatCardRed QLabel#StatTitle,
    QWidget#StatCardPurple QLabel#StatTitle, QWidget#StatCardYellow QLabel#StatTitle {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
    }
    QWidget#StatCardGreen QLabel#StatValueCard,
    QWidget#StatCardGreen QLabel#StatValueLarge { color: #15803d; }
    QWidget#StatCardRed QLabel#StatValueCard,
    QWidget#StatCardRed QLabel#StatValueLarge { color: #b91c1c; }
    QWidget#StatCardPurple QLabel#StatValueCard,
    QWidget#StatCardPurple QLabel#StatValueLarge { color: #6d28d9; }
    QWidget#StatCardYellow QLabel#StatValueCard,
    QWidget#StatCardYellow QLabel#StatValueLarge { color: #b45309; }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle,
    QWidget#StatCardPurple QLabel#Subtitle, QWidget#StatCardYellow QLabel#Subtitle {
        color: #94a3b8;
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
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
    }
    QWidget#ContentPanel * {
        background: transparent;
    }
    QWidget#AssetTablePanel {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-top: none;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 14px;
        border-bottom-right-radius: 14px;
    }
    QWidget#AssetTablePanel * {
        background: transparent;
    }
    /* ───── כרטיסים רגועים (hero) + שורת caption + פירורי לחם + שורת ניווט ───── */
    QWidget#AssetHeroCard, QWidget#AssetHeroCardAccent {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
    }
    QWidget#AssetHeroCardAccent {
        background: #eff6ff;
        border: 1px solid #93c5fd;
    }
    QWidget#AssetHeroCard *, QWidget#AssetHeroCardAccent * {
        background: transparent;
    }
    QLabel#AssetHeroTitle {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        background: transparent;
    }
    QLabel#AssetHeroValue {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        background: transparent;
    }
    QLabel#AssetHeroValue[tone="accent"] { color: #1d4ed8; }
    QLabel#AssetHeroValue[tone="pos"] { color: #15803d; }
    QLabel#AssetHeroValue[tone="neg"] { color: #b91c1c; }
    QLabel#AssetHeroSub {
        font-size: 12px;
        color: #64748b;
        background: transparent;
    }
    QProgressBar#AssetProgress {
        background: #eef2f7;
        border: none;
        border-radius: 5px;
        min-height: 8px;
        max-height: 8px;
        text-align: center;
    }
    QProgressBar#AssetProgress::chunk {
        background: #1d4ed8;
        border-radius: 5px;
    }
    QLabel#AssetCaption {
        font-size: 13px;
        color: #64748b;
        background: transparent;
    }
    QLabel#AssetCaptionWarn {
        font-size: 13px;
        font-weight: 700;
        color: #c2410c;
        background: transparent;
    }
    QLabel#AssetCaptionSep {
        color: #cbd5e1;
        background: transparent;
    }
    QLabel#AssetBreadcrumb {
        font-size: 12px;
        color: #94a3b8;
        background: transparent;
    }
    QPushButton#AssetNavRow {
        text-align: right;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 600;
        color: #0f172a;
    }
    QPushButton#AssetNavRow:hover {
        background: #eff6ff;
        border: 1px solid #93c5fd;
    }
    """


def load_cards_dark_styles() -> str:
    return """
    QWidget#StatCardGreen, QWidget#StatCardRed,
    QWidget#StatCardPurple, QWidget#StatCardYellow {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
    }
    QWidget#StatCardGreen *, QWidget#StatCardRed *,
    QWidget#StatCardPurple *, QWidget#StatCardYellow * {
        background: transparent;
    }
    QWidget#StatCardGreen QLabel#StatTitle, QWidget#StatCardRed QLabel#StatTitle,
    QWidget#StatCardPurple QLabel#StatTitle, QWidget#StatCardYellow QLabel#StatTitle {
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8;
    }
    QWidget#StatCardGreen QLabel#StatValueCard,
    QWidget#StatCardGreen QLabel#StatValueLarge { color: #4ade80; }
    QWidget#StatCardRed QLabel#StatValueCard,
    QWidget#StatCardRed QLabel#StatValueLarge { color: #f87171; }
    QWidget#StatCardPurple QLabel#StatValueCard,
    QWidget#StatCardPurple QLabel#StatValueLarge { color: #a78bfa; }
    QWidget#StatCardYellow QLabel#StatValueCard,
    QWidget#StatCardYellow QLabel#StatValueLarge { color: #fbbf24; }
    QWidget#StatCardGreen QLabel#Subtitle, QWidget#StatCardRed QLabel#Subtitle,
    QWidget#StatCardPurple QLabel#Subtitle, QWidget#StatCardYellow QLabel#Subtitle {
        color: #64748b;
    }
    QWidget#ContentPanel {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 14px;
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
        border-bottom-left-radius: 14px;
        border-bottom-right-radius: 14px;
    }
    QWidget#AssetTablePanel * {
        background: transparent;
    }
    /* ───── כרטיסים רגועים (hero) + שורת caption + פירורי לחם + שורת ניווט ───── */
    QWidget#AssetHeroCard, QWidget#AssetHeroCardAccent {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 14px;
    }
    QWidget#AssetHeroCardAccent {
        background: #1e293b;
        border: 1px solid #3b82f6;
    }
    QWidget#AssetHeroCard *, QWidget#AssetHeroCardAccent * {
        background: transparent;
    }
    QLabel#AssetHeroTitle {
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8;
        background: transparent;
    }
    QLabel#AssetHeroValue {
        font-size: 26px;
        font-weight: 800;
        color: #f1f5f9;
        background: transparent;
    }
    QLabel#AssetHeroValue[tone="accent"] { color: #60a5fa; }
    QLabel#AssetHeroValue[tone="pos"] { color: #4ade80; }
    QLabel#AssetHeroValue[tone="neg"] { color: #f87171; }
    QLabel#AssetHeroSub {
        font-size: 12px;
        color: #94a3b8;
        background: transparent;
    }
    QProgressBar#AssetProgress {
        background: #0f1620;
        border: none;
        border-radius: 5px;
        min-height: 8px;
        max-height: 8px;
        text-align: center;
    }
    QProgressBar#AssetProgress::chunk {
        background: #3b82f6;
        border-radius: 5px;
    }
    QLabel#AssetCaption {
        font-size: 13px;
        color: #94a3b8;
        background: transparent;
    }
    QLabel#AssetCaptionWarn {
        font-size: 13px;
        font-weight: 700;
        color: #fb923c;
        background: transparent;
    }
    QLabel#AssetCaptionSep {
        color: #475569;
        background: transparent;
    }
    QLabel#AssetBreadcrumb {
        font-size: 12px;
        color: #64748b;
        background: transparent;
    }
    QPushButton#AssetNavRow {
        text-align: right;
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 13px;
        font-weight: 600;
        color: #f1f5f9;
    }
    QPushButton#AssetNavRow:hover {
        background: #243044;
        border: 1px solid #3b82f6;
    }
    """
