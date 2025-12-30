from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ...qt import (
    QCheckBox,
    QCursor,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QTimer,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from ...data.provider import AccountsProvider, JsonFileAccountsProvider
from ...models.accounts import BankAccount
from ...models.accounts_service import AccountsService
from ...models.bank_settings import BankSettingsRowInput


class BankAccountsCard(QWidget):
    def __init__(
        self,
        *,
        parent: QWidget,
        provider: AccountsProvider,
        accounts_service: AccountsService,
        on_after_save: Optional[Callable[[], None]] = None,
        sidebar: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        self._provider = provider
        self._accounts_service = accounts_service
        self._on_after_save = on_after_save
        self._sidebar = sidebar
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("ניהול חשבונות בנק", self)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)
        layout.addSpacing(8)

        default_account_names = ["בנק", "מזומן", "ביט", "פייבוקס"]

        bank_accounts: Dict[str, BankAccount] = {}
        if isinstance(self._provider, JsonFileAccountsProvider):
            try:
                all_accounts = self._provider.list_accounts()
                for acc in all_accounts:
                    if isinstance(acc, BankAccount):
                        bank_accounts[acc.name] = acc
            except Exception:
                pass

        account_widgets: Dict[str, Dict[str, Any]] = {}

        for account_name in default_account_names:
            account = bank_accounts.get(account_name)
            is_active = account.active if account else False
            current_amount = account.total_amount if account else 0.0

            account_row = QWidget(self)
            account_row_layout = QVBoxLayout(account_row)
            account_row_layout.setContentsMargins(0, 0, 0, 0)
            account_row_layout.setSpacing(4)

            active_checkbox = QCheckBox(account_name, account_row)
            active_checkbox.setChecked(is_active)

            amount_row = QHBoxLayout()
            amount_row.setSpacing(8)
            amount_label = QLabel("סכום התחלתי:", account_row)
            amount_edit = QLineEdit(account_row)
            try:
                amount_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    amount_edit.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            try:
                amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            except Exception:
                pass
            if account:
                amount_edit.setText(f"{current_amount:.2f}")
            amount_edit.setEnabled(is_active)
            amount_edit.setPlaceholderText("0.00")

            dash = QLabel("-", account_row)
            amount_row.addWidget(amount_label)
            amount_row.addWidget(dash)
            amount_row.addWidget(amount_edit, 1)

            def make_toggle_handler(edit: QLineEdit) -> Callable[[bool], None]:
                def handler(checked: bool) -> None:
                    edit.setEnabled(checked)
                    if not checked:
                        edit.clear()

                return handler

            active_checkbox.toggled.connect(make_toggle_handler(amount_edit))

            account_row_layout.addWidget(active_checkbox)
            account_row_layout.addLayout(amount_row)

            layout.addWidget(account_row)

            account_widgets[account_name] = {
                "checkbox": active_checkbox,
                "amount_edit": amount_edit,
                "current_account": account,
            }

        layout.addStretch(1)

        save_button = QPushButton("שמור חשבונות", self)
        save_button.setObjectName("SaveButton")

        def on_save_bank_accounts() -> None:
            try:
                rows: List[BankSettingsRowInput] = []
                for account_name, widgets in account_widgets.items():
                    checkbox = widgets["checkbox"]
                    amount_edit = widgets["amount_edit"]
                    current_account = widgets["current_account"]

                    rows.append(
                        BankSettingsRowInput(
                            name=account_name,
                            is_active=checkbox.isChecked(),
                            starter_amount_text=amount_edit.text(),
                            current_account=current_account,
                        )
                    )

                merged_accounts = self._accounts_service.apply_bank_settings_rows(rows)
                try:
                    self._accounts_service.save_all(merged_accounts)
                except Exception:
                    pass

                latest_accounts = []
                try:
                    latest_accounts = self._provider.list_accounts()
                except Exception:
                    latest_accounts = []

                def update_sidebar() -> None:
                    if self._sidebar is not None and hasattr(
                        self._sidebar, "update_accounts"
                    ):
                        try:
                            self._sidebar.update_accounts(latest_accounts)
                        except Exception:
                            pass

                try:
                    QTimer.singleShot(50, update_sidebar)
                except Exception:
                    update_sidebar()

                saved_bank_by_name = {
                    acc.name: acc
                    for acc in merged_accounts
                    if isinstance(acc, BankAccount)
                }
                for account_name, widgets in account_widgets.items():
                    checkbox = widgets["checkbox"]
                    amount_edit = widgets["amount_edit"]
                    saved_account = saved_bank_by_name.get(account_name)
                    if saved_account:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(saved_account.active)
                        checkbox.blockSignals(False)
                        if saved_account.active and saved_account.total_amount > 0:
                            amount_edit.setText(f"{saved_account.total_amount:.2f}")
                        amount_edit.setEnabled(saved_account.active)

                try:
                    if self._on_after_save is not None:
                        self._on_after_save()
                except Exception:
                    pass

                try:
                    QToolTip.showText(QCursor.pos(), "חשבונות הבנק נשמרו")
                except Exception:
                    pass

            except Exception as e:
                try:
                    QToolTip.showText(QCursor.pos(), f"שגיאה בשמירה: {str(e)}")
                except Exception:
                    pass

        save_button.clicked.connect(on_save_bank_accounts)
        try:
            layout.addWidget(
                save_button,
                0,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
        except Exception:
            layout.addWidget(save_button)
