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
    QWidget,
    Qt,
)
from ..models.accounts import SavingsAccount
from ..models.savings_dialogs import (
    SavingsAccountForm,
    SavingsAccountValidationContext,
    validate_savings_account_form,
)


class SavingsAccountDialog(QDialog):
    def __init__(
        self,
        account: Optional[SavingsAccount] = None,
        existing_names: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._account = account
        self._is_edit_mode = account is not None
        self._existing_names = existing_names or []
        if account and account.name in self._existing_names:
            self._existing_names = [
                n for n in self._existing_names if n != account.name
            ]

        title_text = "ערוך סוג חסכון" if self._is_edit_mode else "הוסף סוג חסכון"
        self.setWindowTitle(title_text)
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

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
        if account:
            self._name_edit.setText(account.name)

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
        if account:
            self._is_liquid_checkbox.setChecked(account.is_liquid)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        cancel_btn = QPushButton("ביטול", self)
        save_btn = QPushButton("שמור", self)
        save_btn.setDefault(True)
        save_btn.setObjectName("SaveButton")

        buttons_row.addWidget(save_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(cancel_btn)

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
            self._error_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
        except Exception:
            try:
                self._error_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            except Exception:
                pass
        self._error_label.hide()

        layout.addLayout(name_row)
        layout.addWidget(self._error_label)
        layout.addWidget(self._is_liquid_checkbox)
        layout.addLayout(buttons_row)

        def validate_and_accept() -> None:
            form = SavingsAccountForm(
                name=self.get_name(),
                is_liquid=self.get_is_liquid(),
            )
            ctx = SavingsAccountValidationContext(
                existing_names=self._existing_names,
                current_name=self._account.name if self._account else None,
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

    def get_name(self) -> str:
        return self._name_edit.text().strip()

    def get_is_liquid(self) -> bool:
        return self._is_liquid_checkbox.isChecked()
