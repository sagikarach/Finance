from __future__ import annotations

from typing import List, Optional

from ..qt import QDialog, QHBoxLayout, QLabel, QComboBox, Qt
from .dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from ..models.accounts import SavingsAccount


class DeleteSavingsAccountDialog(QDialog):
    """Dialog for deleting a SavingsAccount with account selection dropdown."""

    def __init__(
        self,
        accounts: List[SavingsAccount],
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = accounts
        self._selected_account: Optional[SavingsAccount] = None

        self.setWindowTitle("מחק סוג חסכון")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        # Use shared RTL dialog configuration so margins/spacing match other dialogs.
        layout = setup_standard_rtl_dialog(self)

        # Account selection dropdown
        account_label = QLabel("בחר חשבון:", self)
        account_label.setObjectName("StatTitle")
        account_label.setMinimumWidth(100)
        try:
            account_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass

        self._account_combo = QComboBox(self)
        # Use default combo styling like the transfer dialog (avoid the
        # Savings page's special AccountComboBox theme).
        self._account_combo.setObjectName("DialogAccountCombo")
        # Match transfer dialog: combo uses RTL text flow.
        try:
            self._account_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        for account in accounts:
            self._account_combo.addItem(account.name, account)
        if accounts:
            self._account_combo.setCurrentIndex(0)
            self._selected_account = accounts[0]

        self._account_combo.currentIndexChanged.connect(self._on_account_changed)  # type: ignore[arg-type]

        account_row = QHBoxLayout()
        account_row.setSpacing(8)
        account_row.addWidget(account_label, 0)
        account_row.addWidget(self._account_combo, 1)

        # Confirmation message
        self._message_label = QLabel("", self)
        self._message_label.setObjectName("HeaderTitle")
        self._message_label.setWordWrap(True)
        try:
            self._message_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass
        try:
            self._message_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
        except Exception:
            try:
                self._message_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore[attr-defined]
            except Exception:
                pass
        self._update_message()

        # Buttons row using the shared helper so order and spacing match other dialogs.
        buttons_row, delete_btn, cancel_btn = create_standard_buttons_row(
            self,
            primary_text="מחק",
        )

        layout.addLayout(account_row)
        layout.addWidget(self._message_label)
        layout.addLayout(buttons_row)

        delete_btn.clicked.connect(self.accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]

    def _on_account_changed(self, index: int) -> None:
        """Update message when account selection changes."""
        if 0 <= index < len(self._accounts):
            self._selected_account = self._accounts[index]
            self._update_message()

    def _update_message(self) -> None:
        """Update the confirmation message."""
        if self._selected_account:
            self._message_label.setText(
                f"האם אתה בטוח שברצונך למחוק את '{self._selected_account.name}'?"
            )
        else:
            self._message_label.setText("")

    def get_selected_account(self) -> Optional[SavingsAccount]:
        """Get the currently selected account."""
        return self._selected_account
