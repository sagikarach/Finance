from __future__ import annotations


def load_home_page_light_styles() -> str:
    """Styles specific to the home page in light mode."""
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #0b1220;
        letter-spacing: .2px;
        background: transparent;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #0b1220;
        padding: 6px 8px;
        background: transparent;
    }
    QTableWidget#ActionHistoryTableWidget {
        background: transparent !important;
        border: none;
        font-size: 14px;
        color: #0b1220;
        alternate-background-color: transparent;
    }
    QTableWidget#ActionHistoryTableWidget::viewport {
        background: transparent !important;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar:vertical {
        background: transparent;
        width: 12px;
        border: none;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:vertical {
        background: #cbd5e1;
        border-radius: 6px;
        min-height: 20px;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:vertical:hover {
        background: #94a3b8;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar:horizontal {
        background: transparent;
        height: 12px;
        border: none;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:horizontal {
        background: #cbd5e1;
        border-radius: 6px;
        min-width: 20px;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:horizontal:hover {
        background: #94a3b8;
    }
    QTableWidget#ActionHistoryTableWidget {
        selection-background-color: #e2e8f0;
    }
    QTableWidget#ActionHistoryTableWidget {
        gridline-color: transparent;
    }
    QTableWidget#ActionHistoryTableWidget::item {
        padding: 8px 12px;
        border: none;
        background: transparent !important;
    }
    QTableWidget#ActionHistoryTableWidget::item:selected {
        background: #e2e8f0 !important;
        color: #0b1220;
    }
    QHeaderView#ActionHistoryHeader {
        background: transparent;
        border: none;
        border-bottom: 1px solid #e2e8f0;
    }
    QHeaderView#ActionHistoryHeader::section {
        background: transparent;
        color: #475569;
        font-size: 12px;
        font-weight: 600;
        padding: 8px 12px;
        border: none;
    }
    """


def load_home_page_dark_styles() -> str:
    """Styles specific to the home page in dark mode."""
    return """
    QLabel#StatTitle {
        font-size: 18px;
        font-weight: 600;
        color: #e5e7eb;
        letter-spacing: .2px;
        background: transparent;
    }
    QLabel#StatValueLarge {
        font-size: 56px;
        font-weight: 900;
        color: #e5e7eb;
        padding: 6px 8px;
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
    QTableWidget#ActionHistoryTableWidget {
        background: transparent !important;
        border: none;
        font-size: 14px;
        color: #e5e7eb;
        alternate-background-color: transparent;
    }
    QTableWidget#ActionHistoryTableWidget::viewport {
        background: transparent !important;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar:vertical {
        background: transparent;
        width: 12px;
        border: none;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:vertical {
        background: #4b5563;
        border-radius: 6px;
        min-height: 20px;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:vertical:hover {
        background: #6b7280;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar:horizontal {
        background: transparent;
        height: 12px;
        border: none;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:horizontal {
        background: #4b5563;
        border-radius: 6px;
        min-width: 20px;
    }
    QTableWidget#ActionHistoryTableWidget QScrollBar::handle:horizontal:hover {
        background: #6b7280;
    }
    QTableWidget#ActionHistoryTableWidget {
        selection-background-color: #374151;
    }
    QTableWidget#ActionHistoryTableWidget {
        gridline-color: transparent;
    }
    QTableWidget#ActionHistoryTableWidget::item {
        padding: 8px 12px;
        border: none;
        background: transparent !important;
    }
    QTableWidget#ActionHistoryTableWidget::item:selected {
        background: #374151 !important;
        color: #e5e7eb;
    }
    QHeaderView#ActionHistoryHeader {
        background: transparent;
        border: none;
        border-bottom: 1px solid #374151;
    }
    QHeaderView#ActionHistoryHeader::section {
        background: transparent;
        color: #9ca3af;
        font-size: 12px;
        font-weight: 600;
        padding: 8px 12px;
        border: none;
    }
    """
