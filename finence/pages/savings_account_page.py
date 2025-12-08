from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QToolButton,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QDate,
    QLocale,
    QDialog,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts import SavingsAccount
from ..models.accounts_service import AccountsService
from ..ui.dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from ..widgets.savings_history_chart import create_savings_history_chart_card
from .base_page import BasePage
from .savings_page import format_currency


class SavingsAccountPage(BasePage):
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
            page_title="פרטי חסכון",
            # Use a distinct route name so the sidebar can enable the per-account
            # selection arrow, while still treating it as part of the savings
            # section visually (handled in Sidebar.update_route).
            current_route="savings_account",
        )
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        while main_col.count():
            item = main_col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_name = ""
        try:
            selected_name = str(self._app_context.get("selected_savings_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[SavingsAccount] = None
        for acc in self._accounts:
            if isinstance(acc, SavingsAccount) and acc.name == selected_name:
                target = acc
                break

        if target is None:
            # Fallback UI if nothing was selected or account was removed.
            placeholder = QLabel("לא נבחר חשבון חסכון", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        # --- Top third: summary rectangle with total amount and action buttons ---
        top_card = QWidget(self)
        top_card.setObjectName("Sidebar")
        try:
            top_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(16)

        summary_col = QVBoxLayout()
        summary_col.setSpacing(4)

        name_label = QLabel(target.name, top_card)
        name_label.setObjectName("HeaderTitle")
        total_label = QLabel(format_currency(target.total_amount), top_card)
        total_label.setObjectName("StatValueLarge")
        liquid_text = "נזיל" if target.is_liquid else "לא נזיל"
        liquid_label = QLabel(liquid_text, top_card)
        liquid_label.setObjectName("StatTitle")

        # First row: name and liquid status on the same line, on opposite
        # sides, with the total amount displayed on its own row below.
        name_liquid_row = QHBoxLayout()
        name_liquid_row.setSpacing(8)
        # Swap positions: liquid label on the side where the name was, and the
        # name on the opposite side.
        name_liquid_row.addWidget(liquid_label, 0, Qt.AlignmentFlag.AlignRight)
        name_liquid_row.addStretch(1)
        name_liquid_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)

        summary_col.addLayout(name_liquid_row)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignRight)

        # Buttons row: three actions in a single horizontal line, anchored to
        # the bottom of the top card rather than vertically centered.
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        add_saving_btn = QPushButton("הוסף חסכון", top_card)
        add_saving_btn.setObjectName("AddButton")
        update_saving_btn = QPushButton("עדכן חסכון", top_card)
        update_saving_btn.setObjectName("EditButton")
        delete_saving_btn = QPushButton("מחק חסכון", top_card)
        delete_saving_btn.setObjectName("DeleteButton")

        # Switch positions of add and delete in the row: delete, update, add.
        for b in (delete_saving_btn, update_saving_btn, add_saving_btn):
            try:
                b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            buttons_row.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)

        # Wrap the buttons row in a vertical layout with a stretch above so the
        # buttons sit at the bottom of the top card.
        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(0)
        buttons_col.addStretch(1)
        buttons_col.addLayout(buttons_row)

        # Put buttons on one side and the summary on the other.
        top_layout.addLayout(buttons_col, 0)
        top_layout.addStretch(1)
        top_layout.addLayout(summary_col, 1)

        # Connect buttons to dialogs that actually modify savings in this
        # account and then refresh the page + chart.
        add_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_add_saving(target)
        )
        update_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_update_saving(target)
        )
        delete_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_delete_saving(target)
        )

        # --- Bottom 2/3: rectangle with line chart of savings history ---
        chart_card = create_savings_history_chart_card(self, target, format_currency)

        main_col.addWidget(top_card, 1)
        main_col.addWidget(chart_card, 2)

    def on_route_activated(self) -> None:
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _get_savings_accounts(self) -> List[SavingsAccount]:
        return [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]

    def _replace_savings_account(
        self, original: SavingsAccount, updated: SavingsAccount
    ) -> None:
        for i, acc in enumerate(self._accounts):
            if acc is original:
                self._accounts[i] = updated
                return
        for i, acc in enumerate(self._accounts):
            if isinstance(acc, SavingsAccount) and acc.name == original.name:
                self._accounts[i] = updated
                return

    def _save_savings_accounts_and_refresh(self, selected_name: str) -> None:
        if not isinstance(self._provider, JsonFileAccountsProvider):
            return

        savings_accounts = self._get_savings_accounts()
        try:
            self._provider.save_savings_accounts(savings_accounts)
        except Exception:
            return

        try:
            self._accounts = self._provider.list_accounts()
        except Exception:
            pass

        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)  # type: ignore[arg-type]
            except Exception:
                pass

        try:
            self._app_context["selected_savings_account"] = selected_name
        except Exception:
            pass

        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _build_hebrew_date_edit(self, parent: QWidget) -> QDateEdit:
        date_edit = QDateEdit(parent)
        try:
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd/MM/yyyy")
            date_edit.setMinimumWidth(130)
            date_edit.setObjectName("DateEdit")
            date_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_edit.setDate(QDate.currentDate())
            try:
                try:
                    heb = QLocale(QLocale.Language.Hebrew, QLocale.Country.Israel)  # type: ignore[attr-defined]
                except Exception:
                    heb = QLocale(QLocale.Hebrew, QLocale.Israel)  # type: ignore[attr-defined]
                date_edit.setLocale(heb)
                date_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                cal = date_edit.calendarWidget()
                if cal is not None:
                    cal.setLocale(heb)
                    cal.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                pass
        except Exception:
            pass
        return date_edit

    def _handle_add_saving(self, account: SavingsAccount) -> None:
        dlg = QDialog(self)
        layout = setup_standard_rtl_dialog(dlg, title="הוסף חסכון")

        name_row = QHBoxLayout()
        name_label = QLabel("שם חסכון:", dlg)
        name_edit = QLineEdit(dlg)
        name_row.addWidget(name_label, 0)
        name_row.addWidget(name_edit, 1)

        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום התחלתי:", dlg)
        amount_edit = QLineEdit(dlg)
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        # Date picker for the initial history record, defaulting to today.
        date_row = QHBoxLayout()
        date_label = QLabel("תאריך:", dlg)
        date_edit = self._build_hebrew_date_edit(dlg)
        date_row.addWidget(date_label, 0)
        date_row.addWidget(date_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setStyleSheet("color: #b91c1c;")
        error_label.setWordWrap(True)
        error_label.hide()

        buttons_row, ok_btn, cancel_btn = create_standard_buttons_row(dlg, "שמור")

        layout.addLayout(name_row)
        layout.addLayout(amount_row)
        layout.addLayout(date_row)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            name = name_edit.text().strip()
            amount_text = amount_edit.text().replace(",", "").strip()
            if not name or not amount_text:
                error_label.setText("חובה למלא שם וסכום.")
                error_label.show()
                return
            try:
                amount_val = float(amount_text)
            except Exception:
                error_label.setText("סכום לא חוקי.")
                error_label.show()
                return

            # Date for the first history entry
            try:
                date_qt = date_edit.date()
                date_str = date_qt.toString("yyyy-MM-dd")
            except Exception:
                date_str = ""

            # Prevent duplicate saving names inside this account
            if any(s.name == name for s in account.savings):
                error_label.setText("קיים חסכון עם שם זהה בחשבון.")
                error_label.show()
                return

            try:
                all_accounts = self._provider.list_accounts()
                updated_accounts = self._accounts_service.add_saving(
                    all_accounts, account, name, amount_val, date_str
                )
                self._accounts_service.save_all(updated_accounts)
                self._accounts = updated_accounts
                self._save_savings_accounts_and_refresh(account.name)
            except Exception:
                pass

            dlg.accept()

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()

    def _handle_update_saving(self, account: SavingsAccount) -> None:
        if not account.savings:
            return

        dlg = QDialog(self)
        layout = setup_standard_rtl_dialog(dlg, title="עדכן חסכון")

        select_row = QHBoxLayout()
        select_label = QLabel("בחר חסכון:", dlg)
        savings_combo = QComboBox(dlg)
        try:
            savings_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                savings_combo.setLayoutDirection(Qt.LeftToRight)  # type: ignore[attr-defined]
            except Exception:
                pass
        for s in account.savings:
            savings_combo.addItem(s.name, s)
        select_row.addWidget(select_label, 0)
        select_row.addWidget(savings_combo, 1)

        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום חדש:", dlg)
        amount_edit = QLineEdit(dlg)
        # Pre-fill with current amount of first saving
        try:
            first = account.savings[0]
            amount_edit.setText(str(first.amount))
        except Exception:
            pass
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        # Date picker for the new history record
        date_row = QHBoxLayout()
        date_label = QLabel("תאריך:", dlg)
        date_edit = self._build_hebrew_date_edit(dlg)
        date_row.addWidget(date_label, 0)
        date_row.addWidget(date_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setStyleSheet("color: #b91c1c;")
        error_label.setWordWrap(True)
        error_label.hide()

        buttons_row, ok_btn, cancel_btn = create_standard_buttons_row(dlg, "שמור")

        layout.addLayout(select_row)
        layout.addLayout(amount_row)
        layout.addLayout(date_row)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            idx = savings_combo.currentIndex()
            if idx < 0 or idx >= len(account.savings):
                return
            target_saving = account.savings[idx]
            amount_text = amount_edit.text().replace(",", "").strip()
            if not amount_text:
                error_label.setText("סכום לא יכול להיות ריק.")
                error_label.show()
                return
            try:
                amount_val = float(amount_text)
            except Exception:
                error_label.setText("סכום לא חוקי.")
                error_label.show()
                return

            # Use the chosen date for the new history entry
            try:
                date_qt = date_edit.date()
                date_str = date_qt.toString("yyyy-MM-dd")
            except Exception:
                date_str = ""

            try:
                all_accounts = self._provider.list_accounts()
                updated_accounts = self._accounts_service.edit_saving(
                    all_accounts, account, target_saving.name, amount_val, date_str
                )
                self._accounts_service.save_all(updated_accounts)
                self._accounts = updated_accounts
                self._save_savings_accounts_and_refresh(account.name)
            except Exception:
                pass

            dlg.accept()

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()

    def _handle_delete_saving(self, account: SavingsAccount) -> None:
        if not account.savings:
            return

        dlg = QDialog(self)
        layout = setup_standard_rtl_dialog(dlg, title="מחק חסכון")

        select_row = QHBoxLayout()
        select_label = QLabel("בחר חסכון למחיקה:", dlg)
        savings_combo = QComboBox(dlg)
        try:
            savings_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                savings_combo.setLayoutDirection(Qt.LeftToRight)  # type: ignore[attr-defined]
            except Exception:
                pass
        for s in account.savings:
            savings_combo.addItem(s.name, s)
        select_row.addWidget(select_label, 0)
        select_row.addWidget(savings_combo, 1)

        warning = QLabel("האם אתה בטוח שברצונך למחוק חסכון זה?", dlg)
        warning.setWordWrap(True)

        buttons_row, delete_btn, cancel_btn = create_standard_buttons_row(dlg, "מחק")
        delete_btn.setObjectName("DeleteButton")

        layout.addLayout(select_row)
        layout.addWidget(warning)
        layout.addLayout(buttons_row)

        def on_delete() -> None:
            idx = savings_combo.currentIndex()
            if idx < 0 or idx >= len(account.savings):
                return
            saving_to_delete = account.savings[idx]
            saving_name = saving_to_delete.name

            try:
                all_accounts = self._provider.list_accounts()
                updated_accounts = self._accounts_service.delete_saving(
                    all_accounts, account, saving_name
                )
                self._accounts_service.save_all(updated_accounts)
                self._accounts = updated_accounts
                self._save_savings_accounts_and_refresh(account.name)
            except Exception:
                pass

            dlg.accept()

        delete_btn.clicked.connect(on_delete)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()
