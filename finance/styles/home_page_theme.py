from __future__ import annotations


def load_home_page_light_styles() -> str:
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        letter-spacing: .2px;
        background: transparent;
    }
    QWidget#TrendsControlsBar QLabel {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        background: transparent;
    }
    QWidget#TrendsControlsBar QCheckBox {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        background: transparent;
        spacing: 0px;
        padding: 0px;
        margin: 0px;
    }
    QWidget#TrendsControlsBar QCheckBox::indicator {
        width: 18px;
        height: 18px;
        margin-left: 6px;
        margin-right: 6px;
    }
    QWidget#TrendsControlsBar QComboBox {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
    }
    QLabel#TrendsControlsLabel {
        font-size: 18px;
        font-weight: 700;
        color: #0b1220;
        background: transparent;
    }
    QWidget#TrendsControlsDividerLine {
        background: #0b1220;
        border-radius: 1px;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #0b1220;
        padding: 6px 8px;
        background: transparent;
    }
    QLabel#StatValueCard {
        font-size: 28px;
        font-weight: 900;
        color: #0b1220;
        padding: 0px;
        background: transparent;
    }
    QListWidget#ActionHistoryListWidget {
        background: transparent;
        border: none;
        outline: none;
    }
    QListWidget#ActionHistoryListWidget::item {
        background: transparent;
        border: none;
        margin: 0px;
        padding: 0px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 8px 2px 8px 2px;
        border: none;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical {
        background: #9fc6f7;
        border-radius: 999px;
        min-height: 24px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical:hover {
        background: #9fc6f7;
    }
    QListWidget#ActionHistoryListWidget QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 2px 8px 2px 8px;
        border: none;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal {
        background: #9fc6f7;
        border-radius: 999px;
        min-width: 24px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal:hover {
        background: #9fc6f7;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::add-line:vertical,
    QListWidget#ActionHistoryListWidget QScrollBar::sub-line:vertical,
    QListWidget#ActionHistoryListWidget QScrollBar::add-line:horizontal,
    QListWidget#ActionHistoryListWidget QScrollBar::sub-line:horizontal {
        background: transparent;
        border: none;
        height: 0px;
        width: 0px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::up-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::down-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::left-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::right-arrow {
        background: none;
        border: none;
        width: 0px;
        height: 0px;
    }
    QFrame#ActionHistoryCard {
        background: #dbeafe;
        border: 1px solid #bfdbfe;
        border-radius: 18px;
    }
    QLabel#ActionHistoryTitle {
        color: #0b1220;
        font-size: 15px;
        font-weight: 800;
        background: transparent;
    }
    QLabel#ActionHistoryDate {
        color: #475569;
        font-size: 12px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#ActionHistoryBody {
        color: #0b1220;
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    }
    """


def load_home_page_dark_styles() -> str:
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
        letter-spacing: .2px;
        background: transparent;
    }
    QWidget#TrendsControlsBar QLabel {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
        background: transparent;
    }
    QWidget#TrendsControlsBar QCheckBox {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
        background: transparent;
        spacing: 0px;
        padding: 0px;
        margin: 0px;
    }
    QWidget#TrendsControlsBar QCheckBox::indicator {
        width: 18px;
        height: 18px;
        margin-left: 6px;
        margin-right: 6px;
    }
    QWidget#TrendsControlsBar QComboBox {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
    }
    QLabel#TrendsControlsLabel {
        font-size: 18px;
        font-weight: 700;
        color: #e5e7eb;
        background: transparent;
    }
    QWidget#TrendsControlsDividerLine {
        background: #e5e7eb;
        border-radius: 1px;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #e5e7eb;
        padding: 6px 8px;
        background: transparent;
    }
    QLabel#StatValueCard {
        font-size: 28px;
        font-weight: 900;
        color: #e5e7eb;
        padding: 0px;
        background: transparent;
    }
    QWidget#StatCardGreen {
        background: #16a34a;
        border-radius: 20px;
    }
    QWidget#StatCardPurple {
        background: #4f46e5;
        border-radius: 20px;
    }
    QWidget#StatCardGreen QLabel, QWidget#StatCardPurple QLabel {
        color: #e5e7eb;
    }
    QListWidget#ActionHistoryListWidget {
        background: transparent;
        border: none;
        outline: none;
    }
    QListWidget#ActionHistoryListWidget::item {
        background: transparent;
        border: none;
        margin: 0px;
        padding: 0px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 8px 2px 8px 2px;
        border: none;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical {
        background: #4b5563;
        border-radius: 999px;
        min-height: 24px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical:hover {
        background: #6b7280;
    }
    QListWidget#ActionHistoryListWidget QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 2px 8px 2px 8px;
        border: none;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal {
        background: #4b5563;
        border-radius: 999px;
        min-width: 24px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal:hover {
        background: #6b7280;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::add-line:vertical,
    QListWidget#ActionHistoryListWidget QScrollBar::sub-line:vertical,
    QListWidget#ActionHistoryListWidget QScrollBar::add-line:horizontal,
    QListWidget#ActionHistoryListWidget QScrollBar::sub-line:horizontal {
        background: transparent;
        border: none;
        height: 0px;
        width: 0px;
    }
    QListWidget#ActionHistoryListWidget QScrollBar::up-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::down-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::left-arrow,
    QListWidget#ActionHistoryListWidget QScrollBar::right-arrow {
        background: none;
        border: none;
        width: 0px;
        height: 0px;
    }
    QFrame#ActionHistoryCard {
        background: #020617;
        border: 1px solid #1f2937;
        border-radius: 18px;
    }
    QLabel#ActionHistoryTitle {
        color: #e5e7eb;
        font-size: 15px;
        font-weight: 800;
        background: transparent;
    }
    QLabel#ActionHistoryDate {
        color: #94a3b8;
        font-size: 12px;
        font-weight: 700;
        background: transparent;
    }
    QLabel#ActionHistoryBody {
        color: #e5e7eb;
        font-size: 13px;
        font-weight: 600;
        background: transparent;
    }
    """
