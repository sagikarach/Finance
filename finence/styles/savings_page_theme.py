from __future__ import annotations


def load_savings_page_light_styles() -> str:
    """Styles specific to the savings page in light mode."""
    return """
    QComboBox#AccountComboBox {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 36px;
        font-size: 14px;
        color: #111827;
    }
    QComboBox#AccountComboBox:hover {
        border-color: #94a3b8;
        background: #f8fafc;
    }
    QComboBox#AccountComboBox:focus {
        border-color: #3b82f6;
        background: #ffffff;
    }
    QComboBox#AccountComboBox::drop-down {
        border: none;
        width: 30px;
        background: transparent;
    }
    QComboBox#AccountComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #64748b;
        width: 0;
        height: 0;
        margin-right: 8px;
    }
    QComboBox#AccountComboBox QAbstractItemView {
        background: #ffffff;
        border: 2px solid #cbd5e1;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #e0e7ff;
        selection-color: #111827;
    }
    QComboBox#AccountComboBox QAbstractItemView::item {
        padding: 8px 12px;
        border-radius: 4px;
        min-height: 32px;
    }
    QComboBox#AccountComboBox QAbstractItemView::item:hover {
        background: #f1f5f9;
    }
    QComboBox#AccountComboBox QAbstractItemView::item:selected {
        background: #e0e7ff;
    }

    QPushButton#AddButton {
        background: #a3baed; /* base blue */
        border-color: #c9d5f5;
        font-weight: 600;
        color: #111827;
    }
    QPushButton#AddButton:hover {
        background: #b6d7a8; /* green */
    }
    QPushButton#AddButton:pressed {
        background: #93c47d; /* darker green */
    }

    QPushButton#EditButton {
        background: #a3baed; /* base blue */
        border-color: #c9d5f5;
        font-weight: 600;
        color: #111827;
    }
    QPushButton#EditButton:hover {
        background: #9fc5e8; /* blue */
    }
    QPushButton#EditButton:pressed {
        background: #6fa8dc; /* darker blue */
    }

    QPushButton#DeleteButton {
        background: #a3baed; /* base blue */
        border-color: #c9d5f5;
        font-weight: 600;
        color: #111827;
    }
    QPushButton#DeleteButton:hover {
        background: #ea9999; /* red */
    }
    QPushButton#DeleteButton:pressed {
        background: #e06666; /* darker red */
    }
    """


def load_savings_page_dark_styles() -> str:
    """Styles specific to the savings page in dark mode."""
    return """
    QComboBox#AccountComboBox {
        background: #1e293b;
        border: 2px solid #475569;
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 36px;
        font-size: 14px;
        color: #e5e7eb;
    }
    QComboBox#AccountComboBox:hover {
        border-color: #64748b;
        background: #334155;
    }
    QComboBox#AccountComboBox:focus {
        border-color: #3b82f6;
        background: #1e293b;
    }
    QComboBox#AccountComboBox::drop-down {
        border: none;
        width: 30px;
        background: transparent;
    }
    QComboBox#AccountComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #94a3b8;
        width: 0;
        height: 0;
        margin-right: 8px;
    }
    QComboBox#AccountComboBox QAbstractItemView {
        background: #1e293b;
        border: 2px solid #475569;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #1e3a8a;
        selection-color: #e5e7eb;
    }
    QComboBox#AccountComboBox QAbstractItemView::item {
        padding: 8px 12px;
        border-radius: 4px;
        min-height: 32px;
    }
    QComboBox#AccountComboBox QAbstractItemView::item:hover {
        background: #334155;
    }
    QComboBox#AccountComboBox QAbstractItemView::item:selected {
        background: #1e3a8a;
    }

    QPushButton#AddButton {
        background: #1d4ed8; /* base blue */
        border-color: #1e3a8a;
        font-weight: 600;
        color: #e5e7eb;
    }
    QPushButton#AddButton:hover {
        background: #16a34a; /* green */
    }
    QPushButton#AddButton:pressed {
        background: #15803d; /* darker green */
    }

    QPushButton#EditButton {
        background: #1d4ed8; /* base blue */
        border-color: #1e3a8a;
        font-weight: 600;
        color: #e5e7eb;
    }
    QPushButton#EditButton:hover {
        background: #2563eb; /* blue */
    }
    QPushButton#EditButton:pressed {
        background: #1d4ed8; /* darker blue */
    }

    QPushButton#DeleteButton {
        background: #1d4ed8; /* base blue */
        border-color: #1e3a8a;
        font-weight: 600;
        color: #e5e7eb;
    }
    QPushButton#DeleteButton:hover {
        background: #dc2626; /* red */
    }
    QPushButton#DeleteButton:pressed {
        background: #b91c1c; /* darker red */
    }
    """
