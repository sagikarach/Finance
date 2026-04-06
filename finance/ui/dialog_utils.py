from __future__ import annotations

from ..qt import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, Qt, QComboBox, QWidget, QStyledItemDelegate

try:
    from PySide6.QtWidgets import QCalendarWidget as _BaseCalendar
    from PySide6.QtCore import QDate
    from PySide6.QtGui import QColor, QPainter

    class _LTRCalendarWidget(_BaseCalendar):
        """
        QCalendarWidget replacement that draws all cell text with explicit
        colors, bypassing Qt's palette / RTL-direction rendering that makes
        double-digit day numbers invisible inside RTL parent dialogs.
        """

        def paintCell(self, painter: QPainter, rect, date: QDate) -> None:  # type: ignore[override]
            try:
                align = Qt.AlignmentFlag.AlignCenter
            except AttributeError:
                align = Qt.AlignCenter  # type: ignore[attr-defined]

            today = QDate.currentDate()
            selected = self.selectedDate()
            is_current = (date.month() == self.monthShown()
                          and date.year() == self.yearShown())
            is_weekend = date.dayOfWeek() >= 6  # Saturday=6, Sunday=7

            if date == selected:
                bg = QColor("#2563eb")
                fg = QColor("#ffffff")
            elif date == today:
                bg = QColor("#bfdbfe")
                fg = QColor("#1d4ed8")
            elif not is_current:
                bg = QColor("#e5f0ff")
                fg = QColor("#94a3b8")
            elif is_weekend:
                bg = QColor("#e5f0ff")
                fg = QColor("#ef4444")
            else:
                bg = QColor("#e5f0ff")
                fg = QColor("#0f172a")

            painter.save()
            painter.fillRect(rect, bg)
            painter.setPen(fg)
            font = painter.font()
            font.setPointSize(11)
            painter.setFont(font)
            painter.drawText(rect, align, str(date.day()))
            painter.restore()

except Exception:
    _LTRCalendarWidget = None  # type: ignore[assignment,misc]


class FullCellDelegate(QStyledItemDelegate):
    def updateEditorGeometry(self, editor, option, index):  # type: ignore[override]
        r = option.rect
        editor.setFixedWidth(r.width())
        editor.setGeometry(r)


def setup_standard_rtl_dialog(
    dialog: QDialog,
    title: str | None = None,
    margins: tuple[int, int, int, int] = (24, 24, 24, 24),
    spacing: int = 12,
) -> QVBoxLayout:
    if title:
        dialog.setWindowTitle(title)

    dialog.setModal(True)

    try:
        dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    except Exception:
        pass

    try:
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            dialog.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def set_layout_direction_rtl(widget: QWidget) -> None:
    try:
        widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            widget.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass


def set_layout_direction_ltr(widget: QWidget) -> None:
    try:
        widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    except Exception:
        try:
            widget.setLayoutDirection(Qt.LeftToRight)
        except Exception:
            pass


def create_standard_buttons_row(
    parent: QDialog,
    primary_text: str,
    cancel_text: str = "ביטול",
) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
    buttons_row = QHBoxLayout()
    buttons_row.setSpacing(12)

    cancel_btn = QPushButton(cancel_text, parent)
    cancel_btn.setObjectName("SecondaryButton")
    primary_btn = QPushButton(primary_text, parent)

    try:
        primary_btn.setDefault(True)
    except Exception:
        pass

    buttons_row.addWidget(cancel_btn)
    buttons_row.addStretch(1)
    buttons_row.addWidget(primary_btn)

    return buttons_row, primary_btn, cancel_btn


def setup_calendar_popup(date_edit: "QWidget") -> None:
    try:
        ltr = Qt.LayoutDirection.LeftToRight
    except AttributeError:
        ltr = Qt.LeftToRight  # type: ignore[attr-defined]

    try:
        from PySide6.QtWidgets import QWidget as _QWidget
    except Exception:
        _QWidget = QWidget  # type: ignore[assignment]

    if _LTRCalendarWidget is not None:
        try:
            custom_cal = _LTRCalendarWidget()
            custom_cal.setLayoutDirection(ltr)
            date_edit.setCalendarWidget(custom_cal)  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        date_edit.setLayoutDirection(ltr)
        for child in date_edit.findChildren(_QWidget):
            try:
                child.setLayoutDirection(ltr)
            except Exception:
                pass
    except Exception:
        pass

    try:
        cal = date_edit.calendarWidget()  # type: ignore[attr-defined]
        if cal is None:
            return
        try:
            from PySide6.QtWidgets import QCalendarWidget as _QCal
            cal.setVerticalHeaderFormat(_QCal.VerticalHeaderFormat.NoVerticalHeader)
        except Exception:
            try:
                cal.setVerticalHeaderFormat(0)  # 0 = NoVerticalHeader
            except Exception:
                pass

        try:
            cal.setMinimumSize(280, 220)
        except Exception:
            pass
    except Exception:
        pass


def make_table_danger_button(text: str, parent: QWidget) -> QPushButton:
    """
    Create a red delete button for use as a QTableWidget cell widget.

    Pair with ``FullCellDelegate`` on the column so that Qt's
    ``updateEditorGeometry`` passes the full cell rect (not the padded text
    rect).  Do NOT call ``setFixedWidth`` here — the delegate already gives
    the button exactly the column width and any hard size constraint would
    cause the button to overflow the cell by 1 px.
    """
    btn = QPushButton(text, parent)
    btn.setObjectName("DangerButton")
    btn.setStyleSheet("""
        QPushButton#DangerButton {
            background: #fee2e2;
            border: 1px solid #fca5a5;
            font-weight: 700;
            color: #b91c1c;
            padding: 4px 8px;
            border-radius: 6px;
        }
        QPushButton#DangerButton:hover {
            background: #fecaca;
            border: 1px solid #f87171;
        }
        QPushButton#DangerButton:pressed {
            background: #fca5a5;
        }
    """)
    return btn


def wrap_hebrew_rtl(text: str) -> str:
    if not text:
        return text
    if any("\u0590" <= char <= "\u05ff" for char in text):
        RLE = "\u202b"
        PDF = "\u202c"
        return RLE + text + PDF
    return text


def unwrap_rtl(text: str) -> str:
    if not text:
        return text
    if text.startswith("\u202b") and text.endswith("\u202c"):
        return text[1:-1]
    return text


def apply_rtl_alignment(combo: QComboBox) -> None:
    try:
        model = combo.model()
    except Exception:
        return

    try:
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    except Exception:
        try:
            align = Qt.AlignRight
        except Exception:
            return

    try:
        role = Qt.ItemDataRole.TextAlignmentRole
    except Exception:
        try:
            role = Qt.TextAlignmentRole
        except Exception:
            return

    try:
        row_count = model.rowCount()
    except Exception:
        return

    for row in range(row_count):
        try:
            index = model.index(row, 0)
            model.setData(index, align, role)
        except Exception:
            continue
