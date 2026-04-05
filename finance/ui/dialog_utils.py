from __future__ import annotations

from ..qt import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, Qt, QComboBox, QWidget


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
