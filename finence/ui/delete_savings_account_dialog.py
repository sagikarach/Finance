from __future__ import annotations

from typing import List, Optional

from ..qt import QDialog, QHBoxLayout, QLabel, QComboBox, QWidget, Qt
from .dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from ..models.accounts import SavingsAccount


class DeleteSavingsAccountDialog(QDialog):
    def __init__(
        self,
        accounts: List[SavingsAccount],
        parent: Optional[QWidget] = None,
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

        layout = setup_standard_rtl_dialog(self)

        account_label = QLabel("בחר חשבון:", self)
        account_label.setObjectName("StatTitle")
        account_label.setMinimumWidth(100)
        try:
            account_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass

        self._account_combo = QComboBox(self)
        self._account_combo.setObjectName("DialogAccountCombo")
        try:
            self._account_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                self._account_combo.setLayoutDirection(Qt.LeftToRight)  # type: ignore[attr-defined]
            except Exception:
                pass
        for account in accounts:
            self._account_combo.addItem(account.name, account)
        if accounts:
            self._account_combo.setCurrentIndex(0)
            self._selected_account = accounts[0]

        self._account_combo.currentIndexChanged.connect(self._on_account_changed)

        account_row = QHBoxLayout()
        account_row.setSpacing(8)
        account_row.addWidget(account_label, 0)
        account_row.addWidget(self._account_combo, 1)

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

        buttons_row, delete_btn, cancel_btn = create_standard_buttons_row(
            self,
            primary_text="מחק",
        )

        layout.addLayout(account_row)
        layout.addWidget(self._message_label)
        layout.addLayout(buttons_row)

        delete_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def _on_account_changed(self, index: int) -> None:
        if 0 <= index < len(self._accounts):
            self._selected_account = self._accounts[index]
            self._update_message()

    def _update_message(self) -> None:
        if self._selected_account:
            self._message_label.setText(
                f"האם אתה בטוח שברצונך למחוק את '{self._selected_account.name}'?"
            )
        else:
            self._message_label.setText("")

    def get_selected_account(self) -> Optional[SavingsAccount]:
        return self._selected_account
