from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    Qt,
)
from ..models.accounts import SavingsAccount


class EditSavingsAccountDialog(QDialog):
    """Dialog for editing a SavingsAccount with account selection dropdown."""

    def __init__(
        self,
        accounts: List[SavingsAccount],
        existing_names: Optional[List[str]] = None,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = accounts
        self._existing_names = existing_names or []
        self._selected_account: Optional[SavingsAccount] = None

        self.setWindowTitle("ערוך סוג חסכון")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        # Set RTL layout direction for the dialog
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # Account selection dropdown
        account_label = QLabel("בחר חשבון:", self)
        account_label.setObjectName("StatTitle")
        account_label.setMinimumWidth(100)
        try:
            account_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                account_label.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass

        self._account_combo = QComboBox(self)
        self._account_combo.setObjectName("AccountComboBox")
        try:
            self._account_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                self._account_combo.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        for account in accounts:
            self._account_combo.addItem(account.name, account)  # Store account object as data
        if accounts:
            self._account_combo.setCurrentIndex(0)
            self._selected_account = accounts[0]

        # Connect combo box change to update form
        self._account_combo.currentIndexChanged.connect(self._on_account_changed)  # type: ignore[arg-type]

        account_row = QHBoxLayout()
        account_row.setSpacing(8)
        account_row.addWidget(account_label, 0)
        account_row.addWidget(self._account_combo, 1)

        # Name field
        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_label = QLabel("שם:", self)
        name_label.setObjectName("StatTitle")
        name_label.setMinimumWidth(60)

        self._name_edit = QLineEdit(self)
        try:
            self._name_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                self._name_edit.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        try:
            self._name_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
        except Exception:
            pass
        if self._selected_account:
            self._name_edit.setText(self._selected_account.name)

        name_row.addWidget(name_label, 0)
        name_row.addWidget(self._name_edit, 1)

        # Is liquid checkbox
        self._is_liquid_checkbox = QCheckBox("נזיל", self)
        try:
            self._is_liquid_checkbox.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._is_liquid_checkbox.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        if self._selected_account:
            self._is_liquid_checkbox.setChecked(self._selected_account.is_liquid)

        # Error label
        self._error_label = QLabel("", self)
        self._error_label.setStyleSheet("color: #b91c1c;")
        self._error_label.setWordWrap(True)
        self._error_label.setMinimumHeight(0)
        self._error_label.setMaximumHeight(60)
        try:
            self._error_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                self._error_label.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        try:
            self._error_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        except Exception:
            try:
                self._error_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # type: ignore[attr-defined]
            except Exception:
                pass
        self._error_label.hide()

        # Buttons
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        cancel_btn = QPushButton("ביטול", self)
        save_btn = QPushButton("שמור", self)
        save_btn.setDefault(True)
        save_btn.setObjectName("SaveButton")

        buttons_row.addWidget(save_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(cancel_btn)

        layout.addLayout(account_row)
        layout.addLayout(name_row)
        layout.addWidget(self._error_label)
        layout.addWidget(self._is_liquid_checkbox)
        layout.addLayout(buttons_row)

        def validate_and_accept() -> None:
            name = self.get_name()
            if not name:
                self._error_label.setText("שם לא יכול להיות ריק")
                self._error_label.setMinimumHeight(40)
                self._error_label.show()
                self.adjustSize()
                return

            # Check for duplicate names (excluding current account)
            current_account = self.get_selected_account()
            if current_account:
                other_names = [n for n in self._existing_names if n != current_account.name]
            else:
                other_names = self._existing_names

            if name in other_names:
                self._error_label.setText(f"שם '{name}' כבר קיים. אנא בחר שם אחר.")
                self._error_label.setMinimumHeight(40)
                self._error_label.show()
                self.adjustSize()
                return

            self._error_label.setText("")
            self._error_label.setMinimumHeight(0)
            self._error_label.hide()
            self.adjustSize()
            self.accept()

        save_btn.clicked.connect(validate_and_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(self.reject)  # type: ignore[arg-type]

    def _on_account_changed(self, index: int) -> None:
        """Update form when account selection changes."""
        if 0 <= index < len(self._accounts):
            account = self._accounts[index]
            self._selected_account = account
            self._name_edit.setText(account.name)
            self._is_liquid_checkbox.setChecked(account.is_liquid)
            # Clear error when switching accounts
            self._error_label.setText("")
            self._error_label.hide()
            self._error_label.setMinimumHeight(0)
            self.adjustSize()

    def get_selected_account(self) -> Optional[SavingsAccount]:
        """Get the currently selected account."""
        return self._selected_account

    def get_name(self) -> str:
        """Get the entered name."""
        return self._name_edit.text().strip()

    def get_is_liquid(self) -> bool:
        """Get the is_liquid value."""
        return self._is_liquid_checkbox.isChecked()

