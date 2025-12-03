from __future__ import annotations

from typing import Callable, Dict, List, Optional

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
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..models.accounts import (
    compute_savings_account_total_amount,
    compute_savings_account_liquid_amount,
    SavingsAccount,
)
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..ui.savings_account_dialog import SavingsAccountDialog
from ..ui.edit_savings_account_dialog import EditSavingsAccountDialog
from ..ui.delete_savings_account_dialog import DeleteSavingsAccountDialog
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
        savings_accounts: List[MoneyAccount] = [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]
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

        # Connect button handlers
        add_button.clicked.connect(lambda: self._handle_add_account())  # type: ignore[arg-type]
        edit_button.clicked.connect(lambda: self._handle_edit_account())  # type: ignore[arg-type]
        delete_button.clicked.connect(lambda: self._handle_delete_account())  # type: ignore[arg-type]

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

    def _save_and_refresh(self) -> None:
        """Save savings accounts to JSON and refresh the page."""
        if not isinstance(self._provider, JsonFileAccountsProvider):
            return

        savings_accounts = self._get_savings_accounts()
        try:
            self._provider.save_savings_accounts(savings_accounts)
        except Exception:
            pass

        # Reload accounts from provider
        self._accounts = self._provider.list_accounts()

        # Update sidebar with new accounts
        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)
            except Exception:
                pass

        # Reload the page by navigating away and back
        if self._navigate is not None:
            # Use a timer to navigate away and back to refresh
            try:
                from PySide6.QtCore import QTimer  # type: ignore
                QTimer.singleShot(50, lambda: self._navigate("home"))  # type: ignore[arg-type]
                QTimer.singleShot(150, lambda: self._navigate("savings"))  # type: ignore[arg-type]
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore
                    QTimer.singleShot(50, lambda: self._navigate("home"))  # type: ignore[arg-type]
                    QTimer.singleShot(150, lambda: self._navigate("savings"))  # type: ignore[arg-type]
                except Exception:
                    pass

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
                    if isinstance(account, SavingsAccount) and account.name == selected_account.name:
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
                    if isinstance(account, SavingsAccount) and account.name == original_name:
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
                    if isinstance(account, SavingsAccount) and account.name == selected_account.name:
                        account_to_remove = account
                        break

            if account_to_remove is None:
                return

            # Remove from accounts list
            if account_to_remove in self._accounts:
                self._accounts.remove(account_to_remove)
            self._save_and_refresh()


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"


