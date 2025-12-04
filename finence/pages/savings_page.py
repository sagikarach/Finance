from __future__ import annotations

from typing import Callable, Dict, List, Optional
from datetime import date as _date

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QColor,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QApplication,
    QToolButton,
    QPushButton,
    QDialog,
    QComboBox,
    QLineEdit,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..models.accounts import (
    compute_savings_account_total_amount,
    compute_savings_account_liquid_amount,
    SavingsAccount,
    BankAccount,
    Savings,
    MoneySnapshot,
)
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..ui.savings_account_dialog import SavingsAccountDialog
from ..ui.edit_savings_account_dialog import EditSavingsAccountDialog
from ..ui.delete_savings_account_dialog import DeleteSavingsAccountDialog
from ..ui.dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from .base_page import BasePage


class SavingsPage(BasePage):
    """Savings page showing the state of user accounts."""

    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="חסכונות",
            current_route="savings",
        )

    def on_route_activated(self) -> None:
        """Sync header toggle + sidebar savings list with current theme when opened."""
        app = QApplication.instance()
        is_dark = False
        if app is not None:
            try:
                is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False
        # This will also refresh the sidebar's savings-list background for
        # the active theme via BasePage._on_theme_changed.
        self._on_theme_changed(is_dark)

    def _build_header_left_buttons(self) -> List[QToolButton]:
        """Add settings button to header."""
        buttons = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        """Build savings page content with total and liquid amount cards from SavingsAccount only."""
        total_all = compute_savings_account_total_amount(self._accounts)
        total_liquid = compute_savings_account_liquid_amount(self._accounts)

        total_all_card = QWidget(self)
        total_all_card.setObjectName("StatCardGreen")
        try:
            total_all_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_all_card_layout = QVBoxLayout(total_all_card)
        total_all_card_layout.setContentsMargins(14, 14, 14, 14)
        total_all_card_layout.setSpacing(6)
        try:
            total_all_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_all_title = QLabel("סה״כ כסף", total_all_card)
        total_all_title.setObjectName("StatTitle")
        total_all_label = QLabel(format_currency(total_all), total_all_card)
        total_all_label.setObjectName("StatValueLarge")
        total_all_card_layout.addStretch(1)
        total_all_card_layout.addWidget(
            total_all_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_all_card_layout.addWidget(
            total_all_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_all_card_layout.addStretch(1)

        total_liquid_card = QWidget(self)
        total_liquid_card.setObjectName("StatCardPurple")
        try:
            total_liquid_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_liquid_card_layout = QVBoxLayout(total_liquid_card)
        total_liquid_card_layout.setContentsMargins(14, 14, 14, 14)
        total_liquid_card_layout.setSpacing(6)
        try:
            total_liquid_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_liquid_title = QLabel("סכום נזיל", total_liquid_card)
        total_liquid_title.setObjectName("StatTitle")
        total_liquid_label = QLabel(format_currency(total_liquid), total_liquid_card)
        total_liquid_label.setObjectName("StatValueLarge")
        total_liquid_card_layout.addStretch(1)
        total_liquid_card_layout.addWidget(
            total_liquid_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addWidget(
            total_liquid_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addStretch(1)

        try:
            for card in (total_all_card, total_liquid_card):
                shadow = QGraphicsDropShadowEffect(card)
                shadow.setBlurRadius(36)
                app = QApplication.instance()
                is_dark = False
                if app is not None:
                    try:
                        current_theme = str(app.property("theme") or "light")
                        is_dark = current_theme == "dark"
                    except Exception:
                        pass
                if is_dark:
                    shadow.setColor(QColor(0, 0, 0, 120))
                else:
                    shadow.setColor(QColor(0, 0, 0, 60))
                shadow.setOffset(0, 10)
                card.setGraphicsEffect(shadow)
        except Exception:
            pass

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(total_all_card, 1)
        cards_row.addWidget(total_liquid_card, 1)
        main_col.addLayout(cards_row, 0)

        # Filter to only SavingsAccount for the pie chart
        from ..models.accounts import MoneyAccount

        savings_accounts: List[MoneyAccount] = [
            acc for acc in self._accounts if isinstance(acc, SavingsAccount)
        ]
        chart = AccountsPieChart(accounts=savings_accounts, parent=self)

        chart_card = QWidget(self)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_card_layout = QVBoxLayout(chart_card)
        chart_card_layout.setContentsMargins(4, 4, 4, 4)
        chart_card_layout.setSpacing(0)
        chart_card_layout.addWidget(chart, 1)

        chart_side_card = QWidget(self)
        chart_side_card.setObjectName("Sidebar")
        try:
            chart_side_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_side_layout = QVBoxLayout(chart_side_card)
        chart_side_layout.setContentsMargins(12, 12, 12, 12)
        chart_side_layout.setSpacing(0)

        # Add buttons with equal spacing
        add_button = QPushButton("הוסף סוג חסכון", chart_side_card)
        add_button.setObjectName("AddButton")
        # Make buttons twice as high
        try:
            add_button.setMinimumHeight(add_button.sizeHint().height() * 2)
        except Exception:
            pass

        edit_button = QPushButton("ערוך סוג חסכון", chart_side_card)
        edit_button.setObjectName("EditButton")
        try:
            edit_button.setMinimumHeight(edit_button.sizeHint().height() * 2)
        except Exception:
            pass

        delete_button = QPushButton("מחק סוג חסכון", chart_side_card)
        delete_button.setObjectName("DeleteButton")
        try:
            delete_button.setMinimumHeight(delete_button.sizeHint().height() * 2)
        except Exception:
            pass

        move_button = QPushButton("העבר כסף בין חסכונות", chart_side_card)
        move_button.setObjectName("MoveButton")
        try:
            move_button.setMinimumHeight(move_button.sizeHint().height() * 2)
        except Exception:
            pass

        # Connect button handlers
        add_button.clicked.connect(lambda: self._handle_add_account())  # type: ignore[arg-type]
        edit_button.clicked.connect(lambda: self._handle_edit_account())  # type: ignore[arg-type]
        delete_button.clicked.connect(lambda: self._handle_delete_account())  # type: ignore[arg-type]
        move_button.clicked.connect(lambda: self._handle_move_between_accounts())  # type: ignore[arg-type]

        chart_side_layout.addStretch(1)
        # Order: move money, add, edit, delete.
        chart_side_layout.addWidget(move_button, 0)
        chart_side_layout.addStretch(1)
        chart_side_layout.addWidget(add_button, 0)
        chart_side_layout.addStretch(1)
        chart_side_layout.addWidget(edit_button, 0)
        chart_side_layout.addStretch(1)
        chart_side_layout.addWidget(delete_button, 0)
        chart_side_layout.addStretch(1)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(16)
        chart_row.addWidget(chart_card, 2)
        chart_row.addWidget(chart_side_card, 1)

        main_col.addLayout(chart_row, 1)

    def _get_savings_accounts(self) -> List[SavingsAccount]:
        """Get list of SavingsAccount instances from current accounts."""
        return [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]

    def _get_bank_accounts(self) -> List[BankAccount]:
        """Get list of BankAccount instances from current accounts."""
        return [acc for acc in self._accounts if isinstance(acc, BankAccount)]

    def _save_and_refresh(self) -> None:
        """Save savings accounts to JSON and refresh the page."""
        if not isinstance(self._provider, JsonFileAccountsProvider):
            return

        savings_accounts = self._get_savings_accounts()
        bank_accounts = self._get_bank_accounts()
        try:
            self._provider.save_savings_accounts(savings_accounts)
        except Exception:
            pass
        try:
            # JsonFileAccountsProvider also knows how to persist bank accounts.
            self._provider.save_bank_accounts(bank_accounts)  # type: ignore[attr-defined]
        except Exception:
            pass

        # Reload accounts from provider
        self._accounts = self._provider.list_accounts()

        # Update sidebar with new accounts while preserving the current
        # expanded/collapsed state of the savings list.
        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)
            except Exception:
                pass

        # Refresh this page's content in-place instead of navigating away and
        # back. This avoids the sidebar savings list visibly closing/re-opening
        # when editing an account.
        if isinstance(self._content_col, QVBoxLayout):
            layout = self._content_col
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self._build_content(layout)

    def _handle_add_account(self) -> None:
        """Handle add button click - open dialog to create new SavingsAccount."""
        # Get existing account names for validation
        savings_accounts = self._get_savings_accounts()
        existing_names = [acc.name for acc in savings_accounts]

        dialog = SavingsAccountDialog(existing_names=existing_names, parent=self)
        if dialog.exec():
            name = dialog.get_name()
            if not name:
                return
            is_liquid = dialog.get_is_liquid()

            # Create new SavingsAccount with empty savings
            new_account = SavingsAccount(
                name=name,
                total_amount=0.0,
                is_liquid=is_liquid,
                savings=[],
            )

            # Add to accounts list
            self._accounts.append(new_account)
            self._save_and_refresh()

    def _handle_edit_account(self) -> None:
        """Handle edit button click - open dialog to edit selected SavingsAccount."""
        savings_accounts = self._get_savings_accounts()
        if not savings_accounts:
            return

        # Get existing account names for validation
        existing_names = [acc.name for acc in savings_accounts]

        dialog = EditSavingsAccountDialog(
            accounts=savings_accounts,
            existing_names=existing_names,
            parent=self,
        )
        if dialog.exec():
            selected_account = dialog.get_selected_account()
            if selected_account is None:
                return

            name = dialog.get_name()
            if not name:
                return
            is_liquid = dialog.get_is_liquid()

            # Find the actual account object in self._accounts
            account_to_edit = None
            for account in self._accounts:
                if account is selected_account:
                    account_to_edit = account
                    break

            if account_to_edit is None:
                # Fallback: find by name
                for account in self._accounts:
                    if (
                        isinstance(account, SavingsAccount)
                        and account.name == selected_account.name
                    ):
                        account_to_edit = account
                        break

            if account_to_edit is None:
                return

            # Create a new instance with updated values (dataclass is frozen)
            updated_account = SavingsAccount(
                name=name,
                total_amount=account_to_edit.total_amount,
                is_liquid=is_liquid,
                savings=account_to_edit.savings,
            )

            # Replace the old account with the new one in the list
            for i, account in enumerate(self._accounts):
                if account is account_to_edit:
                    self._accounts[i] = updated_account
                    break
            else:
                # Fallback: find by name
                original_name = account_to_edit.name
                for i, account in enumerate(self._accounts):
                    if (
                        isinstance(account, SavingsAccount)
                        and account.name == original_name
                    ):
                        self._accounts[i] = updated_account
                        break

            self._save_and_refresh()

    def _handle_delete_account(self) -> None:
        """Handle delete button click - open confirmation dialog and delete selected SavingsAccount."""
        savings_accounts = self._get_savings_accounts()
        if not savings_accounts:
            return

        dialog = DeleteSavingsAccountDialog(accounts=savings_accounts, parent=self)
        if dialog.exec():
            selected_account = dialog.get_selected_account()
            if selected_account is None:
                return

            # Find the actual account object in self._accounts
            account_to_remove = None
            for account in self._accounts:
                if account is selected_account:
                    account_to_remove = account
                    break

            if account_to_remove is None:
                # Fallback: find by name
                for account in self._accounts:
                    if (
                        isinstance(account, SavingsAccount)
                        and account.name == selected_account.name
                    ):
                        account_to_remove = account
                        break

            if account_to_remove is None:
                return

            # Remove from accounts list
            if account_to_remove in self._accounts:
                self._accounts.remove(account_to_remove)
            self._save_and_refresh()

    def _handle_move_between_accounts(self) -> None:
        """Move money between individual Savings AND bank accounts.

        The user can choose any source and target from:
        - Bank accounts (label: "חשבון בנק — <account name>")
        - Savings inside savings accounts (label: "<account name> — <saving name>")
        """
        if not self._accounts:
            return

        # Build a flat list of endpoints: (label, kind, account_index, saving_index)
        # kind is "bank" or "saving". For bank accounts saving_index is -1.
        endpoints: List[tuple[str, str, int, int]] = []
        for acc_idx, acc in enumerate(self._accounts):
            if isinstance(acc, BankAccount):
                # For bank accounts show only the account name (no parent
                # prefix), as requested.
                label = acc.name
                endpoints.append((label, "bank", acc_idx, -1))
            elif isinstance(acc, SavingsAccount):
                # For savings, show "account name — saving name".
                for s_idx, s in enumerate(acc.savings):
                    label = f"{acc.name} — {s.name}"
                    endpoints.append((label, "saving", acc_idx, s_idx))

        if len(endpoints) < 2:
            return

        dlg = QDialog(self)
        layout = setup_standard_rtl_dialog(
            dlg,
            title="העבר כסף בין חסכונות",
        )

        # Source endpoint
        src_row = QHBoxLayout()
        src_label = QLabel("העבר מ:", dlg)
        src_combo = QComboBox(dlg)
        try:
            src_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                src_combo.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        for label, _, _, _ in endpoints:
            src_combo.addItem(label)
        # Option B: label on the right, field to its left (text inside field is RTL).
        src_row.addWidget(src_label, 0)
        src_row.addWidget(src_combo, 1)
        src_balance_label = QLabel("", dlg)

        # Target endpoint
        dst_row = QHBoxLayout()
        dst_label = QLabel("אל:", dlg)
        dst_combo = QComboBox(dlg)
        try:
            dst_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                dst_combo.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        for label, _, _, _ in endpoints:
            dst_combo.addItem(label)
        dst_row.addWidget(dst_label, 0)
        dst_row.addWidget(dst_combo, 1)
        dst_balance_label = QLabel("", dlg)

        # Amount
        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום להעברה:", dlg)
        amount_edit = QLineEdit(dlg)
        try:
            amount_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                amount_edit.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        try:
            amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setStyleSheet("color: #b91c1c;")
        error_label.setWordWrap(True)
        error_label.hide()

        (
            buttons_row,
            ok_btn,
            cancel_btn,
        ) = create_standard_buttons_row(dlg, primary_text="בצע העברה")

        layout.addLayout(src_row)
        layout.addWidget(src_balance_label)
        layout.addLayout(dst_row)
        layout.addWidget(dst_balance_label)
        layout.addLayout(amount_row)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def _update_balances() -> None:
            src_idx = src_combo.currentIndex()
            dst_idx = dst_combo.currentIndex()
            src_balance_label.setText("")
            dst_balance_label.setText("")
            if 0 <= src_idx < len(endpoints):
                _, kind, acc_i, s_i = endpoints[src_idx]
                acc = self._accounts[acc_i]
                if kind == "bank" and isinstance(acc, BankAccount):
                    src_balance_label.setText(
                        f"סכום בחשבון זה: {format_currency(acc.total_amount)}"
                    )
                elif kind == "saving" and isinstance(acc, SavingsAccount):
                    try:
                        s_src = acc.savings[s_i]
                        src_balance_label.setText(
                            f"סכום בחסכון זה: {format_currency(s_src.amount)}"
                        )
                    except Exception:
                        pass
            if 0 <= dst_idx < len(endpoints):
                _, kind, acc_i, s_i = endpoints[dst_idx]
                acc = self._accounts[acc_i]
                if kind == "bank" and isinstance(acc, BankAccount):
                    dst_balance_label.setText(
                        f"סכום בחשבון זה: {format_currency(acc.total_amount)}"
                    )
                elif kind == "saving" and isinstance(acc, SavingsAccount):
                    try:
                        s_dst = acc.savings[s_i]
                        dst_balance_label.setText(
                            f"סכום בחסכון זה: {format_currency(s_dst.amount)}"
                        )
                    except Exception:
                        pass

        try:
            src_combo.currentIndexChanged.connect(lambda: _update_balances())  # type: ignore[arg-type]
            dst_combo.currentIndexChanged.connect(lambda: _update_balances())  # type: ignore[arg-type]
        except Exception:
            pass

        _update_balances()

        def on_accept() -> None:
            src_idx = src_combo.currentIndex()
            dst_idx = dst_combo.currentIndex()
            if src_idx < 0 or dst_idx < 0:
                return
            if src_idx == dst_idx:
                error_label.setText("יש לבחור מקורות יעד שונים להעברה.")
                error_label.show()
                return

            _, src_kind, src_acc_i, src_s_i = endpoints[src_idx]
            _, dst_kind, dst_acc_i, dst_s_i = endpoints[dst_idx]

            text = amount_edit.text().replace(",", "").strip()
            if not text:
                error_label.setText("סכום לא יכול להיות ריק.")
                error_label.show()
                return
            try:
                amount = float(text)
            except Exception:
                error_label.setText("סכום לא חוקי.")
                error_label.show()
                return
            if amount <= 0:
                error_label.setText("סכום ההעברה חייב להיות גדול מאפס.")
                error_label.show()
                return
            # Check available balance on source endpoint.
            src_acc = self._accounts[src_acc_i]
            if src_kind == "bank" and isinstance(src_acc, BankAccount):
                if amount > src_acc.total_amount:
                    error_label.setText("אין מספיק כסף בחשבון המקור לביצוע ההעברה.")
                    error_label.show()
                    return
            elif src_kind == "saving" and isinstance(src_acc, SavingsAccount):
                try:
                    src_saving = src_acc.savings[src_s_i]
                except Exception:
                    return
                if amount > src_saving.amount:
                    error_label.setText("אין מספיק כסף בחסכון המקור לביצוע ההעברה.")
                    error_label.show()
                    return

            # Accumulate balance deltas for bank accounts and savings.
            bank_deltas: dict[int, float] = {}
            saving_deltas: dict[tuple[int, int], float] = {}

            if src_kind == "bank":
                bank_deltas[src_acc_i] = bank_deltas.get(src_acc_i, 0.0) - amount
            else:
                saving_deltas[(src_acc_i, src_s_i)] = (
                    saving_deltas.get((src_acc_i, src_s_i), 0.0) - amount
                )

            if dst_kind == "bank":
                bank_deltas[dst_acc_i] = bank_deltas.get(dst_acc_i, 0.0) + amount
            else:
                saving_deltas[(dst_acc_i, dst_s_i)] = (
                    saving_deltas.get((dst_acc_i, dst_s_i), 0.0) + amount
                )

            # Use today's date for new history snapshots so transfers are
            # timestamped correctly.
            today_str = ""
            try:
                today_str = _date.today().isoformat()
            except Exception:
                today_str = ""

            updated_accounts: List = []
            for acc_idx, acc in enumerate(self._accounts):
                # Bank accounts
                if isinstance(acc, BankAccount):
                    delta = bank_deltas.get(acc_idx, 0.0)
                    if delta != 0.0:
                        new_total = acc.total_amount + delta
                        new_history = list(acc.history)
                        try:
                            new_history.append(
                                MoneySnapshot(date=today_str, amount=new_total)
                            )
                        except Exception:
                            pass
                        updated_accounts.append(
                            BankAccount(
                                name=acc.name,
                                total_amount=new_total,
                                is_liquid=acc.is_liquid,
                                history=new_history,
                            )
                        )
                    else:
                        updated_accounts.append(acc)
                    continue

                # Savings accounts
                if isinstance(acc, SavingsAccount):
                    # If no savings in this account are affected, keep as is.
                    has_delta = any(key[0] == acc_idx for key in saving_deltas.keys())
                    if not has_delta:
                        updated_accounts.append(acc)
                        continue

                    new_savings: List[Savings] = []
                    for s_idx, s in enumerate(acc.savings):
                        delta = saving_deltas.get((acc_idx, s_idx), 0.0)
                        if delta != 0.0:
                            new_amount = s.amount + delta
                            new_history = list(s.history)
                            try:
                                new_history.append(
                                    MoneySnapshot(date=today_str, amount=new_amount)
                                )
                            except Exception:
                                pass
                            new_savings.append(
                                Savings(
                                    name=s.name,
                                    amount=new_amount,
                                    history=new_history,
                                )
                            )
                        else:
                            new_savings.append(s)

                    updated_accounts.append(
                        SavingsAccount(
                            name=acc.name,
                            total_amount=0.0,  # recomputed from savings
                            is_liquid=acc.is_liquid,
                            savings=new_savings,
                        )
                    )
                    continue

                # Any other account types (if ever added)
                updated_accounts.append(acc)

            self._accounts = updated_accounts
            dlg.accept()
            self._save_and_refresh()

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"
