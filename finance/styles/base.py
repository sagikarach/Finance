from __future__ import annotations


def load_base_light_styles() -> str:
    return """
    QWidget {
        background: #dbeafe;
        color: #0f172a;
        font-size: 14px;
        font-family: "Varela Round", "Arial Hebrew", "Helvetica Neue", Arial;
    }
    QMainWindow {
        background: #dbeafe;
    }

    /* ── Dialogs ── */
    QDialog {
        background: #dbeafe;
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
    """
