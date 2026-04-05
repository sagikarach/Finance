from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QWidget,
    Qt,
)
from .dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from ..models.accounts import SavingsAccount
from ..models.savings_dialogs import (
    SavingsAccountForm,
    SavingsAccountValidationContext,
    validate_savings_account_form,
)


class EditSavingsAccountDialog(QDialog):
    def __init__(
        self,
        accounts: List[SavingsAccount],
        existing_names: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
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
                self._account_combo.setLayoutDirection(Qt.LeftToRight)
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

        name_row = QHBoxLayout()
        name_row.setSpacing(8)

        name_label = QLabel("שם:", self)
        name_label.setObjectName("StatTitle")
        name_label.setMinimumWidth(60)

        self._name_edit = QLineEdit(self)
        try:
            self._name_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            self._name_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        if self._selected_account:
            self._name_edit.setText(self._selected_account.name)

        name_row.addWidget(name_label, 0)
        name_row.addWidget(self._name_edit, 1)

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

        self._error_label = QLabel("", self)
        self._error_label.setObjectName("ErrorLabel")
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
            self._error_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
        except Exception:
            try:
                self._error_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            except Exception:
                pass
        self._error_label.hide()

        buttons_row, save_btn, cancel_btn = create_standard_buttons_row(
            self,
            primary_text="שמור",
        )

        layout.addLayout(account_row)
        layout.addLayout(name_row)
        layout.addWidget(self._error_label)
        layout.addWidget(self._is_liquid_checkbox)
        layout.addLayout(buttons_row)

        def validate_and_accept() -> None:
            form = SavingsAccountForm(
                name=self.get_name(),
                is_liquid=self.get_is_liquid(),
            )

            current_account = self.get_selected_account()
            if current_account:
                other_names = [
                    n for n in self._existing_names if n != current_account.name
                ]
                ctx = SavingsAccountValidationContext(
                    existing_names=other_names,
                    current_name=current_account.name,
                )
            else:
                ctx = SavingsAccountValidationContext(
                    existing_names=self._existing_names,
                    current_name=None,
                )

            error = validate_savings_account_form(form, ctx)
            if error is not None:
                self._error_label.setText(error.message)
                self._error_label.setMinimumHeight(40)
                self._error_label.show()
                self.adjustSize()
                return

            self._error_label.setText("")
            self._error_label.setMinimumHeight(0)
            self._error_label.hide()
            self.adjustSize()
            self.accept()

        save_btn.clicked.connect(validate_and_accept)
        cancel_btn.clicked.connect(self.reject)

    def _on_account_changed(self, index: int) -> None:
        if 0 <= index < len(self._accounts):
            account = self._accounts[index]
            self._selected_account = account
            self._name_edit.setText(account.name)
            self._is_liquid_checkbox.setChecked(account.is_liquid)
            self._error_label.setText("")
            self._error_label.hide()
            self._error_label.setMinimumHeight(0)
            self.adjustSize()

    def get_selected_account(self) -> Optional[SavingsAccount]:
        return self._selected_account

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def get_is_liquid(self) -> bool:
        return self._is_liquid_checkbox.isChecked()
