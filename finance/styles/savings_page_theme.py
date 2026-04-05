from __future__ import annotations


def load_savings_page_light_styles() -> str:
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
        background: #22c55e;
        border: 1px solid #16a34a;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#AddButton:hover {
        background: #16a34a;
        border: 1px solid #15803d;
    }
    QPushButton#AddButton:pressed {
        background: #15803d;
    }

    QPushButton#EditButton {
        background: #2563eb;
        border: 1px solid #1d4ed8;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#EditButton:hover {
        background: #1d4ed8;
        border: 1px solid #1e40af;
    }
    QPushButton#EditButton:pressed {
        background: #1e40af;
    }

    QPushButton#DeleteButton {
        background: #ef4444;
        border: 1px solid #dc2626;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#DeleteButton:hover {
        background: #dc2626;
        border: 1px solid #b91c1c;
    }
    QPushButton#DeleteButton:pressed {
        background: #b91c1c;
    }

    QPushButton#MoveButton {
        background: #8b5cf6;
        border: 1px solid #7c3aed;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#MoveButton:hover {
        background: #7c3aed;
        border: 1px solid #6d28d9;
    }
    QPushButton#MoveButton:pressed {
        background: #6d28d9;
    }
    """


def load_savings_page_dark_styles() -> str:
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
        background: #16a34a;
        border: 1px solid #15803d;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#AddButton:hover {
        background: #15803d;
        border: 1px solid #166534;
    }
    QPushButton#AddButton:pressed {
        background: #166534;
    }

    QPushButton#EditButton {
        background: #1d4ed8;
        border: 1px solid #1e3a8a;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#EditButton:hover {
        background: #2563eb;
        border: 1px solid #1d4ed8;
    }
    QPushButton#EditButton:pressed {
        background: #1e40af;
    }

    QPushButton#DeleteButton {
        background: #dc2626;
        border: 1px solid #b91c1c;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#DeleteButton:hover {
        background: #b91c1c;
        border: 1px solid #991b1b;
    }
    QPushButton#DeleteButton:pressed {
        background: #991b1b;
    }

    QPushButton#MoveButton {
        background: #7c3aed;
        border: 1px solid #6d28d9;
        font-weight: 600;
        color: #ffffff;
    }
    QPushButton#MoveButton:hover {
        background: #6d28d9;
        border: 1px solid #5b21b6;
    }
    QPushButton#MoveButton:pressed {
        background: #5b21b6;
    }
    """
