from __future__ import annotations

from ..qt import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, Qt, QComboBox


def setup_standard_rtl_dialog(
    dialog: QDialog,
    title: str | None = None,
    margins: tuple[int, int, int, int] = (24, 24, 24, 24),
    spacing: int = 12,
) -> QVBoxLayout:
    """Configure a dialog with the standard RTL look-and-feel.

    - Right-to-left layout direction
    - No context help button
    - Uniform margins/spacing used across the app's dialogs
    """
    if title:
        dialog.setWindowTitle(title)

    dialog.setModal(True)

    try:
        dialog.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    except Exception:
        # Older Qt versions may not support this flag; fail silently.
        pass

    # Ensure RTL layout so labels appear on the right and fields on the left.
    try:
        dialog.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            dialog.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
        except Exception:
            pass

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def create_standard_buttons_row(
    parent: QDialog,
    primary_text: str,
    cancel_text: str = "ביטול",
) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
    """Create a standard buttons row for dialogs.

    Returns (layout, primary_button, cancel_button).
    The visual order in RTL is: [cancel] ... [primary].
    """
    buttons_row = QHBoxLayout()
    buttons_row.setSpacing(12)

    cancel_btn = QPushButton(cancel_text, parent)
    primary_btn = QPushButton(primary_text, parent)

    try:
        primary_btn.setDefault(True)
    except Exception:
        pass

    # In RTL, cancel should appear on the right and primary on the left.
    buttons_row.addWidget(cancel_btn)
    buttons_row.addStretch(1)
    buttons_row.addWidget(primary_btn)

    return buttons_row, primary_btn, cancel_btn


def wrap_hebrew_rtl(text: str) -> str:
    """Wrap Hebrew text with RTL embedding marks to prevent reversal.

    This prevents Hebrew text from being reversed when displayed in Qt widgets
    with RTL layout direction.

    Args:
        text: The text to wrap (may contain Hebrew characters)

    Returns:
        Text wrapped with RLE/PDF marks if it contains Hebrew, otherwise unchanged
    """
    if not text:
        return text
    # Check if text contains Hebrew characters (Unicode range U+0590 to U+05FF)
    if any("\u0590" <= char <= "\u05ff" for char in text):
        RLE = "\u202b"  # Right-to-Left Embedding
        PDF = "\u202c"  # Pop Directional Formatting
        return RLE + text + PDF
    return text


def unwrap_rtl(text: str) -> str:
    """Remove RTL embedding marks from text.

    This is useful when converting user input back to enum values or comparing
    with stored values that don't have RTL marks.

    Args:
        text: The text that may contain RTL marks

    Returns:
        Text with RTL marks removed
    """
    if not text:
        return text
    # Remove RLE at start and PDF at end if present
    if text.startswith("\u202b") and text.endswith("\u202c"):
        return text[1:-1]
    return text


def apply_rtl_alignment(combo: QComboBox) -> None:
    """Ensure that all items in a combo box are aligned to the right (for Hebrew).

    This sets the text alignment for all items in both the closed state and
    the popup list view.

    Args:
        combo: The QComboBox to configure
    """
    try:
        model = combo.model()
    except Exception:
        return

    try:
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    except Exception:
        try:
            # Older Qt enums
            align = Qt.AlignRight  # type: ignore[attr-defined]
        except Exception:
            return

    try:
        role = Qt.ItemDataRole.TextAlignmentRole
    except Exception:
        try:
            role = Qt.TextAlignmentRole  # type: ignore[attr-defined]
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
