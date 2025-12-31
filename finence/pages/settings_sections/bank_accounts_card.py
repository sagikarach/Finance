from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ...qt import (
    QCheckBox,
    QCursor,
    QHBoxLayout,
    QComboBox,
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
from ...data.bank_movement_provider import JsonFileBankMovementProvider
from ...data.action_history_provider import JsonFileActionHistoryProvider
from ...models.accounts import BankAccount, BudgetAccount, MoneyAccount, MoneySnapshot
from ...models.accounts_service import AccountsService
from ...models.bank_movement_service import BankMovementService
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
        from datetime import date as _date

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
        existing_budget: Optional[BudgetAccount] = None
        if isinstance(self._provider, JsonFileAccountsProvider):
            try:
                all_accounts = self._provider.list_accounts()
                for acc in all_accounts:
                    if isinstance(acc, BankAccount):
                        bank_accounts[acc.name] = acc
                    elif isinstance(acc, BudgetAccount) and acc.name == "סיבוס":
                        existing_budget = acc
            except Exception:
                pass

        account_widgets: Dict[str, Dict[str, Any]] = {}

        for account_name in default_account_names:
            account = bank_accounts.get(account_name)
            is_active = account.active if account else False
            baseline_amount = (
                float(getattr(account, "baseline_amount", 0.0) or 0.0)
                if account
                else 0.0
            )

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
                amount_edit.setText(f"{baseline_amount:.2f}")
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

        layout.addSpacing(10)
        budget_title = QLabel("חשבונות תקציב", self)
        budget_title.setObjectName("Subtitle")
        layout.addWidget(budget_title)

        budget_row = QWidget(self)
        budget_row_layout = QVBoxLayout(budget_row)
        budget_row_layout.setContentsMargins(0, 0, 0, 0)
        budget_row_layout.setSpacing(6)

        budget_active = QCheckBox("סיבוס", budget_row)
        budget_active.setChecked(bool(getattr(existing_budget, "active", False)))
        budget_row_layout.addWidget(budget_active)

        budget_inputs = QWidget(budget_row)
        inputs_l = QHBoxLayout(budget_inputs)
        inputs_l.setContentsMargins(0, 0, 0, 0)
        inputs_l.setSpacing(8)

        budget_amount_lbl = QLabel("תקציב חודשי:", budget_inputs)
        budget_amount_edit = QLineEdit(budget_inputs)
        try:
            budget_amount_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                budget_amount_edit.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            budget_amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        try:
            if (
                existing_budget is not None
                and float(existing_budget.monthly_budget) > 0
            ):
                budget_amount_edit.setText(
                    f"{float(existing_budget.monthly_budget):.2f}"
                )
        except Exception:
            pass
        budget_amount_edit.setPlaceholderText("0.00")

        reset_day_lbl = QLabel("יום איפוס:", budget_inputs)
        reset_day_combo = QComboBox(budget_inputs)
        for d in range(1, 29):
            reset_day_combo.addItem(str(d), d)
        try:
            reset_day_val = int(getattr(existing_budget, "reset_day", 1) or 1)
            if reset_day_val < 1:
                reset_day_val = 1
            if reset_day_val > 28:
                reset_day_val = 28
            reset_day_combo.setCurrentIndex(reset_day_val - 1)
        except Exception:
            reset_day_combo.setCurrentIndex(0)

        inputs_l.addWidget(budget_amount_lbl)
        inputs_l.addWidget(budget_amount_edit, 1)
        inputs_l.addWidget(reset_day_lbl)
        inputs_l.addWidget(reset_day_combo, 0)
        budget_row_layout.addWidget(budget_inputs)

        def _toggle_budget_inputs(enabled: bool) -> None:
            budget_amount_edit.setEnabled(bool(enabled))
            reset_day_combo.setEnabled(bool(enabled))

        budget_active.toggled.connect(_toggle_budget_inputs)
        _toggle_budget_inputs(budget_active.isChecked())

        layout.addWidget(budget_row)
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
                out_accounts: List[MoneyAccount] = []
                try:
                    for a in merged_accounts:
                        if isinstance(a, BudgetAccount) and a.name == "סיבוס":
                            continue
                        out_accounts.append(a)
                except Exception:
                    out_accounts = list(merged_accounts)

                if budget_active.isChecked():
                    try:
                        mb = float(budget_amount_edit.text().strip().replace(",", ""))
                    except Exception:
                        mb = 0.0
                    if mb < 0:
                        mb = 0.0
                    rd = reset_day_combo.currentData()
                    try:
                        rd_i = int(rd if rd is not None else 1)
                    except Exception:
                        rd_i = 1
                    if rd_i < 1:
                        rd_i = 1
                    if rd_i > 28:
                        rd_i = 28
                    hist: List[MoneySnapshot] = []
                    last_period = ""
                    cur_total = float(mb)
                    if existing_budget is not None:
                        try:
                            hist = list(existing_budget.history)
                        except Exception:
                            hist = []
                        try:
                            last_period = str(existing_budget.last_reset_period or "")
                        except Exception:
                            last_period = ""
                        try:
                            cur_total = float(existing_budget.total_amount)
                        except Exception:
                            cur_total = float(mb)
                    if cur_total > float(mb):
                        cur_total = float(mb)
                    if not hist:
                        try:
                            hist = [
                                MoneySnapshot(
                                    date=_date.today().isoformat(),
                                    amount=float(cur_total),
                                )
                            ]
                        except Exception:
                            hist = []
                    out_accounts.append(
                        BudgetAccount(
                            name="סיבוס",
                            total_amount=float(cur_total),
                            is_liquid=False,
                            history=hist,
                            active=True,
                            monthly_budget=float(mb),
                            reset_day=int(rd_i),
                            last_reset_period=str(last_period or ""),
                        )
                    )
                try:
                    # Persist accounts, then recompute balances from movements + baseline_amount.
                    # This fixes cases where an old "starter amount" save wrote a latest snapshot of 0.
                    self._accounts_service.save_all(out_accounts)
                    try:
                        movement_provider = JsonFileBankMovementProvider()
                        history_provider = JsonFileActionHistoryProvider()
                        mv_svc = BankMovementService(
                            movement_provider, history_provider, classifier=None
                        )
                        out_accounts = mv_svc.recalculate_account_balances(out_accounts)
                        self._accounts_service.save_all(out_accounts)
                    except Exception:
                        pass
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
                        try:
                            ba = float(
                                getattr(saved_account, "baseline_amount", 0.0) or 0.0
                            )
                        except Exception:
                            ba = 0.0
                        if saved_account.active:
                            amount_edit.setText(f"{ba:.2f}")
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
