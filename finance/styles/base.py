from __future__ import annotations


def load_base_light_styles() -> str:
    return """
    QWidget {
        background: #f4f2ec;
        color: #0f172a;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", "Helvetica Neue", Arial;
    }
    QMainWindow {
        background: #f4f2ec;
    }

    /* ── Dialogs ── */
    QDialog {
        background: #f4f2ec;
    }

    /* ── Text inputs ── */
    QLineEdit {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #dcdad0;
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 20px;
        selection-background-color: #8b7fd4;
        selection-color: #ffffff;
    }
    QLineEdit:focus {
        border: 1px solid #8b7fd4;
        background: #ffffff;
    }
    QLineEdit:disabled {
        background: #ece9e0;
        color: #64748b;
        border: 1px solid #dcdad0;
    }

    /* ── Combo boxes ── */
    QComboBox {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #dcdad0;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QComboBox:hover {
        border: 1px solid #cfcbe8;
    }
    QComboBox:focus {
        border: 1px solid #8b7fd4;
    }
    QComboBox::drop-down {
        border: none;
        width: 26px;
        background: transparent;
    }
    QComboBox::down-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #475569;
        margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        background: #ffffff;
        color: #0f172a;
        border: 1px solid #dcdad0;
        border-radius: 8px;
        selection-background-color: #deddf8;
        selection-color: #4b4980;
        outline: none;
        padding: 4px;
    }
    QComboBox QAbstractItemView::item {
        padding: 7px 12px;
        min-height: 28px;
        border-radius: 6px;
    }
    QComboBox QAbstractItemView::item:hover {
        background: #f7f5ef;
    }

    /* ── Spin box ── */
    QSpinBox, QDoubleSpinBox {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #dcdad0;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #8b7fd4;
    }

    /* ── Scroll bars ── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 2px 4px 2px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #cfcbe8;
        border-radius: 4px;
        min-height: 28px;
    }
    QScrollBar::handle:vertical:hover {
        background: #b9b6f0;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        background: transparent;
        border: none;
        height: 0px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 2px 4px 2px 4px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #cfcbe8;
        border-radius: 4px;
        min-width: 28px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #b9b6f0;
    }
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        background: transparent;
        border: none;
        width: 0px;
    }
    QScrollBar::up-arrow, QScrollBar::down-arrow,
    QScrollBar::left-arrow, QScrollBar::right-arrow {
        background: none;
        border: none;
        width: 0px;
        height: 0px;
    }
    QScrollBar::add-page, QScrollBar::sub-page {
        background: none;
    }

    /* ── Text edit (multi-line) ── */
    QTextEdit, QPlainTextEdit {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #dcdad0;
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: #8b7fd4;
        selection-color: #ffffff;
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #8b7fd4;
    }

    /* ── Tables ── */
    QTableWidget, QTableView {
        background: #ffffff;
        alternate-background-color: #f4f2ec;
        border: 1px solid #dcdad0;
        border-radius: 10px;
        gridline-color: #f1efe7;
        selection-background-color: #deddf8;
        selection-color: #4b4980;
        outline: none;
    }
    QTableWidget::item, QTableView::item {
        padding: 6px 10px;
        border: none;
    }
    QTableWidget::item:hover, QTableView::item:hover {
        background: #f7f5ef;
    }
    QTableWidget::item:selected, QTableView::item:selected {
        background: #deddf8;
        color: #4b4980;
    }
    QHeaderView {
        background: #f4f2ec;
        border: none;
    }
    QHeaderView::section {
        background: #f4f2ec;
        color: #55584f;
        font-weight: 700;
        font-size: 13px;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid #cfcbe8;
        border-right: 1px solid #ecece2;
    }
    QHeaderView::section:first {
        border-top-left-radius: 10px;
    }
    QHeaderView::section:last {
        border-right: none;
        border-top-right-radius: 10px;
    }
    QTableCornerButton::section {
        background: #f4f2ec;
        border: none;
        border-bottom: 1px solid #cfcbe8;
        border-top-left-radius: 10px;
    }

    /* ── Checkboxes ── */
    QCheckBox {
        spacing: 8px;
        color: #0f172a;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 2px solid #cfcbe8;
        background: #f8faff;
    }
    QCheckBox::indicator:hover {
        border-color: #8b7fd4;
        background: #f7f5ef;
    }
    QCheckBox::indicator:checked {
        background: #8b7fd4;
        border-color: #8b7fd4;
    }
    QCheckBox::indicator:checked:hover {
        background: #4b4980;
        border-color: #4b4980;
    }
    QCheckBox::indicator:disabled {
        background: #e2e8f0;
        border-color: #cbd5e1;
    }
    """


def load_base_dark_styles() -> str:
    return """
    QWidget {
        background: #020617;
        color: #e5e7eb;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", "Helvetica Neue", Arial;
    }
    QMainWindow {
        background: #020617;
    }

    /* ── Dialogs ── */
    QDialog {
        background: #020617;
    }

    /* ── Text inputs ── */
    QLineEdit {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 20px;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
    }
    QLineEdit:focus {
        border: 1px solid #3b82f6;
        background: #111827;
    }
    QLineEdit:disabled {
        background: #0d1424;
        color: #4b5563;
        border: 1px solid #1e293b;
    }

    /* ── Combo boxes ── */
    QComboBox {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QComboBox:hover {
        border: 1px solid #2d5a8e;
    }
    QComboBox:focus {
        border: 1px solid #3b82f6;
    }
    QComboBox::drop-down {
        border: none;
        width: 26px;
        background: transparent;
    }
    QComboBox::down-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #94a3b8;
        margin-right: 8px;
    }
    QComboBox QAbstractItemView {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        selection-background-color: #1e3a5f;
        selection-color: #93c5fd;
        outline: none;
        padding: 4px;
    }
    QComboBox QAbstractItemView::item {
        padding: 7px 12px;
        min-height: 28px;
        border-radius: 6px;
    }
    QComboBox QAbstractItemView::item:hover {
        background: #1e293b;
    }

    /* ── Spin box ── */
    QSpinBox, QDoubleSpinBox {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #3b82f6;
    }

    /* ── Scroll bars ── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 2px 4px 2px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #1e3a5f;
        border-radius: 4px;
        min-height: 28px;
    }
    QScrollBar::handle:vertical:hover {
        background: #2d5a8e;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        background: transparent;
        border: none;
        height: 0px;
    }
    QScrollBar:horizontal {
        background: transparent;
        height: 8px;
        margin: 2px 4px 2px 4px;
        border: none;
    }
    QScrollBar::handle:horizontal {
        background: #1e3a5f;
        border-radius: 4px;
        min-width: 28px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #2d5a8e;
    }
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {
        background: transparent;
        border: none;
        width: 0px;
    }
    QScrollBar::up-arrow, QScrollBar::down-arrow,
    QScrollBar::left-arrow, QScrollBar::right-arrow {
        background: none;
        border: none;
        width: 0px;
        height: 0px;
    }
    QScrollBar::add-page, QScrollBar::sub-page {
        background: none;
    }

    /* ── Text edit (multi-line) ── */
    QTextEdit, QPlainTextEdit {
        background: #0f172a;
        color: #e5e7eb;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #3b82f6;
    }

    /* ── Tables ── */
    QTableWidget, QTableView {
        background: #0f172a;
        alternate-background-color: #111827;
        border: 1px solid #1e3a5f;
        border-radius: 10px;
        gridline-color: #1e293b;
        selection-background-color: #1e3a5f;
        selection-color: #93c5fd;
        outline: none;
    }
    QTableWidget::item, QTableView::item {
        padding: 6px 10px;
        border: none;
    }
    QTableWidget::item:hover, QTableView::item:hover {
        background: #1e293b;
    }
    QTableWidget::item:selected, QTableView::item:selected {
        background: #1e3a5f;
        color: #93c5fd;
    }
    QHeaderView {
        background: #020617;
        border: none;
    }
    QHeaderView::section {
        background: #111827;
        color: #60a5fa;
        font-weight: 700;
        font-size: 13px;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid #1e3a5f;
        border-right: 1px solid #1e293b;
    }
    QHeaderView::section:first {
        border-top-left-radius: 10px;
    }
    QHeaderView::section:last {
        border-right: none;
        border-top-right-radius: 10px;
    }
    QTableCornerButton::section {
        background: #111827;
        border: none;
        border-bottom: 1px solid #1e3a5f;
        border-top-left-radius: 10px;
    }

    /* ── Checkboxes ── */
    QCheckBox {
        spacing: 8px;
        color: #e5e7eb;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 5px;
        border: 2px solid #2d5a8e;
        background: #0f172a;
    }
    QCheckBox::indicator:hover {
        border-color: #3b82f6;
        background: #1e293b;
    }
    QCheckBox::indicator:checked {
        background: #2563eb;
        border-color: #2563eb;
    }
    QCheckBox::indicator:checked:hover {
        background: #3b82f6;
        border-color: #3b82f6;
    }
    QCheckBox::indicator:disabled {
        background: #1e293b;
        border-color: #374151;
    }
    """
