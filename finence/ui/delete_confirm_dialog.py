from __future__ import annotations

from typing import Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
)


class DeleteConfirmDialog(QDialog):
    """Dialog for confirming deletion of a SavingsAccount."""

    def __init__(
        self,
        account_name: str,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("מחק סוג חסכון")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        message = QLabel(f"האם אתה בטוח שברצונך למחוק את '{account_name}'?", self)
        message.setObjectName("HeaderTitle")
        try:
            message.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        message.setWordWrap(True)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        cancel_btn = QPushButton("ביטול", self)
        delete_btn = QPushButton("מחק", self)
        delete_btn.setObjectName("DeleteButton")
        delete_btn.setDefault(True)

        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(delete_btn)

        layout.addWidget(message)
        layout.addLayout(buttons_row)

        delete_btn.clicked.connect(self.accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]

