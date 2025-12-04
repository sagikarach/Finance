from __future__ import annotations

from ..qt import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, Qt


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
