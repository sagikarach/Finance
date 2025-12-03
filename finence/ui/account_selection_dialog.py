from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    Qt,
)
from ..models.accounts import SavingsAccount


class AccountSelectionDialog(QDialog):
    """Dialog for selecting a SavingsAccount from a list."""

    def __init__(
        self,
        accounts: List[SavingsAccount],
        title: str = "בחר חשבון",
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = accounts
        self._selected_account: Optional[SavingsAccount] = None

        self.setWindowTitle(title)
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title_label = QLabel(title, self)
        title_label.setObjectName("HeaderTitle")
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        self._list_widget = QListWidget(self)
        for account in accounts:
            self._list_widget.addItem(account.name)
        if accounts:
            self._list_widget.setCurrentRow(0)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        cancel_btn = QPushButton("ביטול", self)
        select_btn = QPushButton("בחר", self)
        select_btn.setDefault(True)
        select_btn.setObjectName("SaveButton")

        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(select_btn)

        layout.addWidget(title_label)
        layout.addWidget(self._list_widget)
        layout.addLayout(buttons_row)

        def on_select() -> None:
            current_row = self._list_widget.currentRow()
            if 0 <= current_row < len(self._accounts):
                self._selected_account = self._accounts[current_row]
                self.accept()

        select_btn.clicked.connect(on_select)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]

        # Allow double-click to select
        def on_item_double_clicked(item) -> None:
            on_select()

        try:
            self._list_widget.itemDoubleClicked.connect(on_item_double_clicked)  # type: ignore[attr-defined]
        except Exception:
            pass

    def get_selected_account(self) -> Optional[SavingsAccount]:
        """Get the selected account."""
        return self._selected_account

