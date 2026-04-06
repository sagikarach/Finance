from __future__ import annotations


def load_base_light_styles() -> str:
    return """
    QWidget {
        background: #f5f8ff;
        color: #0f172a;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", "Helvetica Neue", Arial;
    }
    QMainWindow {
        background: #f5f8ff;
    }

    /* ── Dialogs ── */
    QDialog {
        background: #f5f8ff;
    }

    /* ── Text inputs ── */
    QLineEdit {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 20px;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
    }
    QLineEdit:focus {
        border: 1px solid #2563eb;
        background: #ffffff;
    }
    QLineEdit:disabled {
        background: #e2eeff;
        color: #64748b;
        border: 1px solid #c7d9f5;
    }

    /* ── Combo boxes ── */
    QComboBox {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QComboBox:hover {
        border: 1px solid #93c5fd;
    }
    QComboBox:focus {
        border: 1px solid #2563eb;
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
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        selection-background-color: #dbeafe;
        selection-color: #1d4ed8;
        outline: none;
        padding: 4px;
    }
    QComboBox QAbstractItemView::item {
        padding: 7px 12px;
        min-height: 28px;
        border-radius: 6px;
    }
    QComboBox QAbstractItemView::item:hover {
        background: #eff6ff;
    }

    /* ── Spin box ── */
    QSpinBox, QDoubleSpinBox {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 22px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #2563eb;
    }

    /* ── Scroll bars ── */
    QScrollBar:vertical {
        background: transparent;
        width: 8px;
        margin: 4px 2px 4px 2px;
        border: none;
    }
    QScrollBar::handle:vertical {
        background: #93c5fd;
        border-radius: 4px;
        min-height: 28px;
    }
    QScrollBar::handle:vertical:hover {
        background: #60a5fa;
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
        background: #93c5fd;
        border-radius: 4px;
        min-width: 28px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #60a5fa;
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
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
    }
    QTextEdit:focus, QPlainTextEdit:focus {
        border: 1px solid #2563eb;
    }

    /* ── Tables ── */
    QTableWidget, QTableView {
        background: #ffffff;
        alternate-background-color: #f5f8ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px;
        gridline-color: #e8f0fe;
        selection-background-color: #dbeafe;
        selection-color: #1d4ed8;
        outline: none;
    }
    QTableWidget::item, QTableView::item {
        padding: 6px 10px;
        border: none;
    }
    QTableWidget::item:hover, QTableView::item:hover {
        background: #eff6ff;
    }
    QTableWidget::item:selected, QTableView::item:selected {
        background: #dbeafe;
        color: #1d4ed8;
    }
    QHeaderView {
        background: #f5f8ff;
        border: none;
    }
    QHeaderView::section {
        background: #e8f3ff;
        color: #1e40af;
        font-weight: 700;
        font-size: 13px;
        padding: 8px 10px;
        border: none;
        border-bottom: 1px solid #93c5fd;
        border-right: 1px solid #c7dffe;
    }
    QHeaderView::section:first {
        border-top-left-radius: 10px;
    }
    QHeaderView::section:last {
        border-right: none;
        border-top-right-radius: 10px;
    }
    QTableCornerButton::section {
        background: #e8f3ff;
        border: none;
        border-bottom: 1px solid #93c5fd;
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
        border: 2px solid #93c5fd;
        background: #f8faff;
    }
    QCheckBox::indicator:hover {
        border-color: #3b82f6;
        background: #eff6ff;
    }
    QCheckBox::indicator:checked {
        background: #2563eb;
        border-color: #2563eb;
    }
    QCheckBox::indicator:checked:hover {
        background: #1d4ed8;
        border-color: #1d4ed8;
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
