from __future__ import annotations


def load_date_picker_light_styles() -> str:
    return """
    QDateEdit, QDateEdit#DateEdit {
        background: #f8faff;
        color: #0f172a;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 28px;
    }
    QDateEdit:focus {
        border: 1px solid #2563eb;
    }
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 24px;
        border-left: 1px solid #bfdbfe;
        background: #dbeafe;
        margin: 0px;
    }
    QDateEdit::down-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #0f172a;
        margin-right: 6px;
    }
    QCalendarWidget {
        background: #e5f0ff;
        border: 1px solid #93c5fd;
        border-radius: 10px;
    }
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background: #dbeafe;
        border-bottom: 1px solid #93c5fd;
    }
    QCalendarWidget QToolButton {
        background: transparent;
        color: #0f172a;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
    }
    QCalendarWidget QToolButton#qt_calendar_prevmonth,
    QCalendarWidget QToolButton#qt_calendar_nextmonth {
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border: 1px solid #93c5fd;
        background: #dbeafe;
    }
    QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
    QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {
        background: #bfdbfe;
    }
    QCalendarWidget QToolButton::menu-indicator {
        image: none;
    }
    QCalendarWidget QAbstractItemView {
        background: #e5f0ff;
        color: #0f172a;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
        outline: none;
        gridline-color: #bfdbfe;
        font-size: 13px;
    }
    """


def load_date_picker_dark_styles() -> str:
    return """
    QDateEdit, QDateEdit#DateEdit {
        background: #111827;
        color: #e5e7eb;
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 6px 10px;
        min-height: 28px;
    }
    QDateEdit::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: right center;
        width: 24px;
        border-left: 1px solid #374151;
        background: #020617;
        margin: 0px;
    }
    QDateEdit::down-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #e5e7eb;
        margin-right: 6px;
    }
    QCalendarWidget {
        background: #020617;
        border: 1px solid #374151;
        border-radius: 10px;
    }
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background: #020617;
        border-bottom: 1px solid #1f2937;
    }
    QCalendarWidget QToolButton {
        background: transparent;
        color: #e5e7eb;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 6px;
    }
    QCalendarWidget QToolButton#qt_calendar_prevmonth,
    QCalendarWidget QToolButton#qt_calendar_nextmonth {
        min-width: 28px;
        max-width: 28px;
        min-height: 28px;
        max-height: 28px;
        border: 1px solid #374151;
        background: #111827;
    }
    QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
    QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {
        background: #1f2937;
    }
    QCalendarWidget QToolButton::menu-indicator {
        image: none;
    }
    QCalendarWidget QAbstractItemView {
        background: #111827;
        color: #e5e7eb;
        selection-background-color: #2563eb;
        selection-color: #ffffff;
        outline: none;
        gridline-color: #1f2937;
        font-size: 13px;
    }
    """
