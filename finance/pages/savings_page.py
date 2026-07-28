from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QApplication,
    QToolButton,
    QPushButton,
    QDialog,
    QComboBox,
    QLineEdit,
)
from ..data.provider import AccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts import (
    compute_savings_account_total_amount,
    compute_savings_account_liquid_amount,
    SavingsAccount,
    BankAccount,
)
from ..models.transfers import TransferEndpoint, TransferRequest
from ..models.savings_dialogs import SavingsAccountForm
from ..models.accounts_service import AccountsService
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..ui.savings_account_dialog import SavingsAccountDialog
from ..ui.edit_savings_account_dialog import EditSavingsAccountDialog
from ..ui.delete_savings_account_dialog import DeleteSavingsAccountDialog
from ..ui.dialog_utils import setup_standard_rtl_dialog, create_standard_buttons_row
from ..utils.formatting import format_currency
from .base_page import BasePage


class SavingsPage(BasePage):
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
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service = AccountsService(
            self._provider,
            history_provider=self._history_provider,
            movements_provider=self._bank_movement_provider,
        )

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._load_and_refresh_accounts()
        app = QApplication.instance()
        is_dark = False
        if app is not None:
            try:
                is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False

        self._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            try:
                self.setUpdatesEnabled(False)
                self._clear_content_layout(self._content_col)
                self._build_content(self._content_col)
            finally:
                self.setUpdatesEnabled(True)
                self.update()

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
            settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

    _PASTEL = [
        "#B9B6F0", "#C6D3B4", "#F2D06B", "#E9A491", "#9BB4E6",
        "#8FBF9F", "#E0B0D8", "#F7E2A6",
    ]

    def _stat_card(self, object_name: str, title: str, value: str) -> QWidget:
        card = QWidget(self)
        card.setObjectName(object_name)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
            card.setMinimumHeight(112)
            card.setMaximumHeight(150)
        except Exception:
            pass
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)
        t = QLabel(title, card)
        t.setObjectName("StatTitle")
        v = QLabel(value, card)
        v.setObjectName("StatValueLarge")
        lay.addStretch(1)
        lay.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        return card

    def _icon_button(self, glyph: str, *, danger: bool = False) -> QPushButton:
        b = QPushButton(glyph, self)
        try:
            b.setFixedSize(34, 34)
        except Exception:
            pass
        color = "#d66a4e" if danger else "#6b6f66"
        border = "#f0d9d2" if danger else "#ecece2"
        b.setStyleSheet(
            "QPushButton{background:#ffffff;border:1px solid %s;border-radius:10px;"
            "font-size:14px;font-weight:400;color:%s;padding:0;}"
            "QPushButton:hover{background:#f7f5ef;}" % (border, color)
        )
        return b

    def _account_row(self, acc: SavingsAccount, idx: int) -> QWidget:
        row = QWidget(self)
        if idx > 0:
            row.setObjectName("SavRow")
            try:
                row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            row.setStyleSheet("QWidget#SavRow{border-top:1px solid #ecece2;}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(2, 10, 2, 10)
        rl.setSpacing(10)

        dot = QLabel(row)
        try:
            dot.setFixedSize(12, 12)
        except Exception:
            pass
        dot.setStyleSheet(
            f"background:{self._PASTEL[idx % len(self._PASTEL)]};border-radius:4px;"
        )

        info = QVBoxLayout()
        info.setSpacing(1)
        name = QLabel(str(acc.name), row)
        name.setStyleSheet(
            "font-size:14.5px;font-weight:700;color:#26251f;background:transparent;"
        )
        status = QLabel(
            "נזיל" if bool(getattr(acc, "is_liquid", False)) else "לא נזיל", row
        )
        status.setStyleSheet(
            "font-size:11.5px;color:#8b8e86;background:transparent;"
        )
        info.addWidget(name)
        info.addWidget(status)

        amt = QLabel(
            format_currency(float(getattr(acc, "total_amount", 0.0) or 0.0)), row
        )
        amt.setStyleSheet(
            "font-size:15px;font-weight:800;color:#2f9e68;background:transparent;"
        )

        edit_btn = self._icon_button("✎")
        del_btn = self._icon_button("🗑", danger=True)
        edit_btn.clicked.connect(
            lambda _=None, a=acc: self._edit_specific_account(a)
        )
        del_btn.clicked.connect(
            lambda _=None, a=acc: self._delete_specific_account(a)
        )

        rl.addWidget(dot)
        rl.addLayout(info, 1)
        rl.addStretch(1)
        rl.addWidget(amt)
        rl.addWidget(edit_btn)
        rl.addWidget(del_btn)
        return row

    def _build_content(self, main_col: QVBoxLayout) -> None:
        total_all = compute_savings_account_total_amount(self._accounts)
        total_liquid = compute_savings_account_liquid_amount(self._accounts)
        savings_accounts: List[SavingsAccount] = [
            acc for acc in self._accounts if isinstance(acc, SavingsAccount)
        ]
        savings_accounts.sort(
            key=lambda a: float(getattr(a, "total_amount", 0.0) or 0.0),
            reverse=True,
        )

        # ── top row: total hero + liquid + count ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(
            self._stat_card(
                "DashHeroYellow", "סה״כ חסכונות", format_currency(total_all)
            ),
            3,
        )
        cards_row.addWidget(
            self._stat_card("DashCard", "נזיל", format_currency(total_liquid)), 2
        )
        cards_row.addWidget(
            self._stat_card(
                "DashCardGreen", "סוגי חיסכון", str(len(savings_accounts))
            ),
            2,
        )
        main_col.addLayout(cards_row, 0)

        # ── donut panel ──
        chart = AccountsPieChart(accounts=savings_accounts, parent=self)
        donut_panel = QWidget(self)
        donut_panel.setObjectName("ContentPanel")
        try:
            donut_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        dp_lay = QVBoxLayout(donut_panel)
        dp_lay.setContentsMargins(18, 14, 18, 14)
        dp_lay.setSpacing(8)
        dp_title = QLabel("פילוח חסכונות", donut_panel)
        dp_title.setObjectName("PanelTitle")
        dp_lay.addWidget(dp_title)
        dp_lay.addWidget(chart, 1)

        # ── accounts list panel: header actions + per-row edit/delete ──
        list_panel = QWidget(self)
        list_panel.setObjectName("ContentPanel")
        try:
            list_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        lp_lay = QVBoxLayout(list_panel)
        lp_lay.setContentsMargins(18, 14, 18, 14)
        lp_lay.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        lp_title = QLabel("החסכונות שלי", list_panel)
        lp_title.setObjectName("PanelTitle")
        add_btn = QPushButton("＋ הוסף חיסכון", list_panel)
        add_btn.setObjectName("AddButton")
        move_btn = QPushButton("⇄ העבר כסף", list_panel)
        move_btn.setObjectName("MoveButton")
        for b in (add_btn, move_btn):
            try:
                b.setMinimumHeight(38)
                b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
        add_btn.clicked.connect(lambda: self._handle_add_account())
        move_btn.clicked.connect(lambda: self._handle_move_between_accounts())
        header.addWidget(lp_title)
        header.addStretch(1)
        header.addWidget(move_btn)
        header.addWidget(add_btn)
        lp_lay.addLayout(header)
        lp_lay.addSpacing(4)

        if savings_accounts:
            rows_container = QWidget(list_panel)
            rows_lay = QVBoxLayout(rows_container)
            rows_lay.setContentsMargins(0, 0, 0, 0)
            rows_lay.setSpacing(0)
            for idx, acc in enumerate(savings_accounts):
                rows_lay.addWidget(self._account_row(acc, idx))
            rows_lay.addStretch(1)
            lp_lay.addWidget(rows_container, 1)
        else:
            empty = QLabel("אין חסכונות עדיין", list_panel)
            empty.setObjectName("Subtitle")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lp_lay.addWidget(empty, 1)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(donut_panel, 2)
        content_row.addWidget(list_panel, 3)
        main_col.addLayout(content_row, 1)

    def _edit_specific_account(self, acc: SavingsAccount) -> None:
        savings_accounts = self._get_savings_accounts()
        existing_names = [a.name for a in savings_accounts]
        dialog = SavingsAccountDialog(
            account=acc, existing_names=existing_names, parent=self
        )
        if not dialog.exec():
            return
        form = SavingsAccountForm(
            name=dialog.get_name(), is_liquid=dialog.get_is_liquid()
        )
        if not form.name.strip() or self._accounts_service is None:
            return
        target = None
        for a in self._accounts:
            if a is acc or (
                isinstance(a, SavingsAccount) and a.name == acc.name
            ):
                target = a
                break
        if target is None:
            return
        self._accounts = self._accounts_service.edit_savings_account(
            self._accounts, target, form
        )
        self._save_and_refresh()

    def _delete_specific_account(self, acc: SavingsAccount) -> None:
        from ..qt import QMessageBox

        answer = QMessageBox.question(
            self,
            "מחיקת חסכון",
            f"למחוק את '{acc.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self._accounts_service is None:
            return
        self._accounts = self._accounts_service.delete_savings_account(
            self._accounts, acc
        )
        self._save_and_refresh()

    def _get_savings_accounts(self) -> List[SavingsAccount]:
        return [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]

    def _get_bank_accounts(self) -> List[BankAccount]:
        return [acc for acc in self._accounts if isinstance(acc, BankAccount)]

    def _save_and_refresh(self) -> None:
        try:
            if self._accounts_service is None:
                return
            # Savings changes always push to the remote immediately (not only on
            # an explicit Sync), so the remote can never revert a local change.
            self._accounts_service.save_all(self._accounts, force_remote=True)
        except Exception:
            pass
        try:
            if self._accounts_service is not None:
                self._accounts = self._accounts_service.load_accounts()
        except Exception:
            pass

        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)
            except Exception:
                pass

        if isinstance(self._content_col, QVBoxLayout):
            layout = self._content_col
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self._build_content(layout)

    def _handle_add_account(self) -> None:
        savings_accounts = self._get_savings_accounts()
        existing_names = [acc.name for acc in savings_accounts]

        dialog = SavingsAccountDialog(existing_names=existing_names, parent=self)
        if dialog.exec():
            form = SavingsAccountForm(
                name=dialog.get_name(),
                is_liquid=dialog.get_is_liquid(),
            )
            if not form.name.strip():
                return

            if self._accounts_service is None:
                return
            self._accounts = self._accounts_service.add_savings_account(
                self._accounts, form
            )
            self._save_and_refresh()

    def _handle_edit_account(self) -> None:
        savings_accounts = self._get_savings_accounts()
        if not savings_accounts:
            return

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

            account_to_edit = None
            for account in self._accounts:
                if account is selected_account:
                    account_to_edit = account
                    break

            if account_to_edit is None:
                for account in self._accounts:
                    if (
                        isinstance(account, SavingsAccount)
                        and account.name == selected_account.name
                    ):
                        account_to_edit = account
                        break

            if account_to_edit is None:
                return

            form = SavingsAccountForm(
                name=dialog.get_name(),
                is_liquid=dialog.get_is_liquid(),
            )
            if not form.name.strip():
                return

            if self._accounts_service is None:
                return
            self._accounts = self._accounts_service.edit_savings_account(
                self._accounts, account_to_edit, form
            )
            self._save_and_refresh()

    def _handle_delete_account(self) -> None:
        savings_accounts = self._get_savings_accounts()
        if not savings_accounts:
            return

        dialog = DeleteSavingsAccountDialog(accounts=savings_accounts, parent=self)
        if dialog.exec():
            selected_account = dialog.get_selected_account()
            if selected_account is None:
                return

            if self._accounts_service is None:
                return
            self._accounts = self._accounts_service.delete_savings_account(
                self._accounts, selected_account
            )
            self._save_and_refresh()

    def _handle_move_between_accounts(self) -> None:
        try:
            self._accounts = self._provider.list_accounts()
        except Exception:
            pass
        if not self._accounts:
            return

        endpoints: List[tuple[str, str, int, int]] = []
        for acc_idx, acc in enumerate(self._accounts):
            if isinstance(acc, BankAccount):
                if not getattr(acc, "active", True):
                    continue
                label = acc.name
                endpoints.append((label, "bank", acc_idx, -1))
            elif isinstance(acc, SavingsAccount):
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

        src_row = QHBoxLayout()
        src_label = QLabel("העבר מ:", dlg)
        src_combo = QComboBox(dlg)
        try:
            src_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                src_combo.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        for label, _, _, _ in endpoints:
            src_combo.addItem(label)
        src_row.addWidget(src_label, 0)
        src_row.addWidget(src_combo, 1)
        src_balance_label = QLabel("", dlg)

        dst_row = QHBoxLayout()
        dst_label = QLabel("אל:", dlg)
        dst_combo = QComboBox(dlg)
        try:
            dst_combo.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                dst_combo.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        for label, _, _, _ in endpoints:
            dst_combo.addItem(label)
        dst_row.addWidget(dst_label, 0)
        dst_row.addWidget(dst_combo, 1)
        dst_balance_label = QLabel("", dlg)

        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום להעברה:", dlg)
        amount_edit = QLineEdit(dlg)
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
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setObjectName("ErrorLabel")
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
            src_combo.currentIndexChanged.connect(lambda: _update_balances())
            dst_combo.currentIndexChanged.connect(lambda: _update_balances())
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

            src_endpoint = TransferEndpoint(
                kind="bank" if src_kind == "bank" else "saving",
                account_index=src_acc_i,
                savings_index=src_s_i,
            )
            dst_endpoint = TransferEndpoint(
                kind="bank" if dst_kind == "bank" else "saving",
                account_index=dst_acc_i,
                savings_index=dst_s_i,
            )
            request = TransferRequest(
                source=src_endpoint,
                target=dst_endpoint,
                amount=amount,
            )

            result = self._accounts_service.apply_transfer_request(
                self._accounts, request
            )
            if result.error is not None:
                error_label.setText(result.error.message)
                error_label.show()
                return

            self._accounts = result.accounts
            dlg.accept()
            self._save_and_refresh()

        ok_btn.clicked.connect(on_accept)
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()
