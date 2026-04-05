from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
import threading
import queue

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QToolButton,
    QPushButton,
    QSizePolicy,
    QTimer,
)
from ..data.provider import AccountsProvider
from ..models.accounts import BankAccount, BudgetAccount
from ..models.accounts_service import AccountsService
from ..models.bank_movement import MovementType
from ..models.action_history import (
    ActionHistory,
    UploadOutcomeFileAction,
    generate_action_id,
    get_current_timestamp,
)
from ..widgets.bank_history_chart import create_bank_history_chart_card
from ..utils.formatting import format_currency
from ..ui.sibus_expenses_dialog import SibusExpensesDialog
from ..ui.account_movements_dialog import AccountMovementsDialog
from .base_page import BasePage


class BankAccountPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[Any] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="פרטי חשבון בנק",
            current_route="bank_account",
        )
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[Any]:
        buttons: List[Any] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
            settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        navigate = self._navigate
        if navigate is not None:
            try:
                settings_btn.clicked.connect(lambda: navigate("settings"))
            except Exception:
                pass
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: Any) -> None:
        while main_col.count():
            item = main_col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_name = ""
        try:
            selected_name = str(self._app_context.get("selected_bank_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[BankAccount | BudgetAccount] = None
        for acc in self._accounts:
            if (
                isinstance(acc, (BankAccount, BudgetAccount))
                and acc.name == selected_name
            ):
                target = acc
                break

        if target is None:
            placeholder = QLabel("לא נבחר חשבון בנק", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        top_card = QWidget(self)
        top_card.setObjectName("ContentPanel")
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
        main_value = float(getattr(target, "total_amount", 0.0) or 0.0)
        total_label = QLabel(format_currency(main_value), top_card)
        total_label.setObjectName("StatValueLarge")

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addStretch(1)
        name_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)

        summary_col.addLayout(name_row)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignRight)

        if isinstance(target, BudgetAccount):
            budget = float(getattr(target, "monthly_budget", 0.0) or 0.0)
            reset_day = int(getattr(target, "reset_day", 1) or 1)
            remaining = float(getattr(target, "total_amount", 0.0) or 0.0)
            used = max(0.0, budget - remaining)

            meta_label = QLabel(
                f"תקציב חודשי: {format_currency(budget)}  |  נוצל: {format_currency(used)}  |  איפוס: יום {reset_day}",
                top_card,
            )
            meta_label.setObjectName("Subtitle")
            meta_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            summary_col.addWidget(meta_label, 0, Qt.AlignmentFlag.AlignRight)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        if isinstance(target, BudgetAccount):
            manage_btn = QPushButton("ניהול הוצאות", top_card)
            manage_btn.setObjectName("AddButton")
            try:
                manage_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception:
                pass
            try:
                manage_btn.clicked.connect(
                    lambda _=None, acc=target: self._open_sibus_expenses_dialog(acc)
                )
            except Exception:
                pass
            buttons_row.addWidget(manage_btn, 0, Qt.AlignmentFlag.AlignLeft)
        elif isinstance(target, BankAccount):
            manage_btn = QPushButton("ניהול תנועות", top_card)
            manage_btn.setObjectName("AddButton")
            try:
                manage_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception:
                pass
            try:
                manage_btn.clicked.connect(
                    lambda _=None, acc=target: self._open_account_movements_dialog(acc)
                )
            except Exception:
                pass
            buttons_row.addWidget(manage_btn, 0, Qt.AlignmentFlag.AlignLeft)

        if isinstance(target, BankAccount) and target.name == "בנק":
            import_btn = QPushButton("ייבוא קובץ הוצאות", top_card)
            import_btn.setObjectName("AddButton")
            try:
                if not bool(getattr(target, "active", False)):
                    import_btn.setEnabled(False)
                    import_btn.setToolTip(
                        "החשבון אינו פעיל. הפעל אותו בהגדרות כדי לייבא קובץ."
                    )
            except Exception:
                pass
            try:
                import_btn.clicked.connect(
                    lambda _=None, acc=target: self._on_import_csv(acc)
                )
            except Exception:
                pass
            try:
                import_btn.setSizePolicy(
                    QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
                )
            except Exception:
                pass
            buttons_row.addWidget(import_btn, 0, Qt.AlignmentFlag.AlignLeft)

        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(0)
        buttons_col.addStretch(1)
        buttons_col.addLayout(buttons_row)

        top_layout.addLayout(buttons_col, 0)
        top_layout.addStretch(1)
        top_layout.addLayout(summary_col, 1)

        main_col.addWidget(top_card, 1)
        chart_container = QWidget(self)
        chart_container_layout = QVBoxLayout(chart_container)
        chart_container_layout.setContentsMargins(0, 0, 0, 0)
        chart_container_layout.setSpacing(0)
        try:
            if (
                isinstance(target, BankAccount)
                and str(getattr(target, "name", "") or "") == "בנק"
            ):
                initial_chart = QLabel("טוען גרף...", chart_container)
                initial_chart.setObjectName("Subtitle")
                initial_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif isinstance(target, BankAccount) and getattr(target, "history", None):
                initial_chart = create_bank_history_chart_card(
                    self,
                    target,
                    format_currency,
                    movements=None,
                )
            else:
                initial_chart = QLabel("טוען גרף...", chart_container)
                initial_chart.setObjectName("Subtitle")
                initial_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            initial_chart = QLabel("טוען גרף...", chart_container)
            initial_chart.setObjectName("Subtitle")
            initial_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)

        chart_container_layout.addWidget(initial_chart, 1)

        main_col.addWidget(chart_container, 2)

        build_token = object()
        try:
            self._bank_chart_build_token = build_token  # type: ignore[attr-defined]
        except Exception:
            pass
        result_q: "queue.Queue[List[Any]]" = queue.Queue(maxsize=1)

        def _swap_chart_widget(new_w: Any) -> None:
            try:
                if getattr(self, "_bank_chart_build_token", None) is not build_token:  # type: ignore[attr-defined]
                    return
            except Exception:
                return
            try:
                if chart_container is None or chart_container.parent() is None:
                    return
            except Exception:
                return

            # Clear container and insert the new chart.
            while chart_container_layout.count():
                item = chart_container_layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
            chart_container_layout.addWidget(new_w, 1)

        def _load_and_build() -> None:
            svc = getattr(self, "_bank_movement_service", None)
            try:
                movements_loaded = svc.list_movements() if svc is not None else []
            except Exception:
                movements_loaded = []
            try:
                # Send result back to the UI thread via a queue (thread-safe).
                result_q.put(list(movements_loaded), block=False)
            except Exception:
                pass

        try:
            threading.Thread(target=_load_and_build, daemon=True).start()
        except Exception:
            pass

        def _poll_result() -> None:
            try:
                if getattr(self, "_bank_chart_build_token", None) is not build_token:  # type: ignore[attr-defined]
                    return
            except Exception:
                return

            try:
                movements_loaded = result_q.get(block=False)
            except Exception:
                movements_loaded = None

            if movements_loaded is None:
                try:
                    QTimer.singleShot(80, _poll_result)
                except Exception:
                    pass
                return

            try:
                new_chart = create_bank_history_chart_card(
                    self,
                    target,
                    format_currency,
                    movements=list(movements_loaded),
                )
            except Exception:
                new_chart = QLabel("שגיאה בטעינת הגרף", chart_container)
                new_chart.setObjectName("Subtitle")
                new_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _swap_chart_widget(new_chart)

        try:
            # Start polling from the UI thread (this thread has the Qt event loop).
            QTimer.singleShot(0, _poll_result)
        except Exception:
            pass

    def _on_import_csv(self, account: BankAccount) -> None:
        try:
            if not bool(getattr(account, "active", False)):
                try:
                    from ..qt import QToolTip, QCursor

                    QToolTip.showText(
                        QCursor.pos(),
                        "החשבון אינו פעיל. הפעל אותו בהגדרות כדי לייבא קובץ.",
                    )
                except Exception:
                    pass
                return
        except Exception:
            return
        QFileDialogCls = None
        try:
            import importlib

            QtWidgets = importlib.import_module("PySide6.QtWidgets")
            QFileDialogCls = getattr(QtWidgets, "QFileDialog", None)
        except Exception:
            try:
                import importlib

                QtWidgets = importlib.import_module("PyQt6.QtWidgets")
                QFileDialogCls = getattr(QtWidgets, "QFileDialog", None)
            except Exception:
                QFileDialogCls = None
        if QFileDialogCls is None:
            return

        try:
            file_path, _ = QFileDialogCls.getOpenFileName(
                self,
                "ייבוא הוצאות מקובץ CSV",
                "",
                "CSV Files (*.csv);;All Files (*)",
            )
        except Exception:
            return

        if not file_path:
            return

        service = getattr(self, "_bank_movement_service", None)
        if service is None:
            return

        from_dialog: List = []

        try:
            self._accounts = service.import_outcome_csv(
                self._accounts, account.name, file_path
            )
        except Exception:
            return
        try:
            pending = service.pop_pending_reviews()
        except Exception:
            pending = []
        if pending:
            categories: list[str] = []
            provider = getattr(self, "_bank_movement_provider", None)
            try:
                if provider is not None and hasattr(
                    provider, "list_categories_for_type"
                ):
                    categories = provider.list_categories_for_type(False)
                elif provider is not None and hasattr(provider, "list_categories"):
                    categories = provider.list_categories()
            except Exception:
                categories = []

            on_category_added = None
            try:
                if provider is not None and hasattr(provider, "add_category_for_type"):

                    def _on_cat_added(name: str, *, _prov=provider) -> None:
                        try:
                            _prov.add_category_for_type(name, False)
                        except Exception:
                            pass
                        try:
                            from ..models.firebase_movements_sync import (
                                FirebaseMovementsSyncService,
                            )

                            FirebaseMovementsSyncService().sync_categories_only()
                        except Exception:
                            pass

                    on_category_added = _on_cat_added
                elif provider is not None and hasattr(provider, "add_category"):
                    on_category_added = getattr(provider, "add_category")
            except Exception:
                on_category_added = None

            pending_sorted = sorted(pending, key=lambda x: x.confidence)
            top_3_pending = pending_sorted[:3]

            if top_3_pending:
                dlg: Any = None
                try:
                    from ..ui.batch_outcome_review_dialog import (
                        BatchOutcomeReviewDialog,
                    )

                    dlg = BatchOutcomeReviewDialog(
                        top_3_pending,
                        categories,
                        on_category_added=on_category_added,
                        parent=self,
                    )
                    result = dlg.exec()
                except Exception:
                    result = False

                if result and dlg is not None:
                    try:
                        results = dlg.get_results()
                    except Exception:
                        results = []
                    for idx, updated in enumerate(results):
                        if updated is None:
                            continue

                        try:
                            self._accounts = service.apply_movement(
                                self._accounts,
                                updated,
                                is_income_hint=False,
                                record_history=False,
                            )
                            from_dialog.append(updated)
                            try:
                                service._imported_for_last_csv.append(updated)
                            except Exception:
                                pass

                            if service.classifier is not None and hasattr(
                                service.classifier, "learn"
                            ):
                                try:
                                    type_mapping = {
                                        MovementType.MONTHLY: "חודשית",
                                        MovementType.YEARLY: "שנתית",
                                        MovementType.ONE_TIME: "חד פעמי",
                                    }
                                    expense_type_str = type_mapping.get(
                                        updated.type, "חודשית"
                                    )

                                    confirmed_expense = {
                                        "description": updated.description or "",
                                        "amount": updated.amount,
                                        "category": updated.category,
                                        "expenseType": expense_type_str,
                                    }
                                    service.classifier.learn(confirmed_expense)
                                except Exception:
                                    pass
                        except Exception:
                            continue

        try:
            imported_batch = service.pop_imported_for_last_csv()
        except Exception:
            imported_batch = []

        all_movement_ids = {m.id for m in imported_batch}
        for m in from_dialog:
            if m.id not in all_movement_ids:
                imported_batch.append(m)
                all_movement_ids.add(m.id)

        all_movements = imported_batch

        if all_movements:
            try:
                total_amount = float(sum(m.amount for m in all_movements))
            except Exception:
                total_amount = 0.0

            movement_ids: list[str] = []
            for m in all_movements:
                try:
                    movement_ids.append(m.id)
                except Exception:
                    continue

            try:
                file_name = Path(file_path).name
            except Exception:
                file_name = file_path

            try:
                action_obj = UploadOutcomeFileAction(
                    action_name="upload_outcome_file",
                    account_name=account.name,
                    file_name=file_name,
                    total_amount=total_amount,
                    expenses_count=len(movement_ids),
                    movement_ids=movement_ids,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action_obj,
                )
                self._history_provider.add_action(history_entry)
            except Exception:
                pass

        try:
            history_table = self._find_history_table()
            if history_table is not None and hasattr(
                self._history_provider, "list_history"
            ):
                try:
                    history = self._history_provider.list_history()
                    history_table.set_history(history)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self._accounts = service.recalculate_account_balances(self._accounts)
        except Exception:
            pass

        try:
            self._save_and_refresh_accounts()
        except Exception:
            pass

    def on_route_activated(self) -> None:
        super().on_route_activated()
        svc = getattr(self, "_accounts_service", None)
        if svc is not None:
            try:
                self._accounts = svc.load_accounts()
            except Exception:
                pass
        # Always recompute balances (especially budget/"סיבוס") in case movements
        # changed while on another workspace/view.
        try:
            if hasattr(self, "_bank_movement_service") and self._bank_movement_service:
                self._accounts = (
                    self._bank_movement_service.recalculate_account_balances(
                        self._accounts
                    )
                )
        except Exception:
            pass
        try:
            self._save_and_refresh_accounts()
        except Exception:
            pass

    def _open_sibus_expenses_dialog(self, account: BudgetAccount) -> None:
        svc = getattr(self, "_bank_movement_service", None)
        if svc is None:
            return
        try:
            categories = svc.list_categories(is_income=False)
        except Exception:
            categories = []

        dlg = SibusExpensesDialog(
            account_name=str(getattr(account, "name", "") or ""),
            movement_service=svc,
            categories=list(categories),
            accounts_getter=lambda: list(getattr(self, "_accounts", []) or []),
            accounts_setter=lambda new_accounts: setattr(
                self, "_accounts", list(new_accounts)
            ),
            parent=None,
            on_changed=lambda: self._save_and_refresh_accounts(),
        )
        dlg.exec()

    def _open_account_movements_dialog(self, account: BankAccount) -> None:
        svc = getattr(self, "_bank_movement_service", None)
        if svc is None:
            return
        try:
            income_categories = svc.list_categories(is_income=True)
        except Exception:
            income_categories = []
        try:
            outcome_categories = svc.list_categories(is_income=False)
        except Exception:
            outcome_categories = []

        dlg = AccountMovementsDialog(
            account_name=str(getattr(account, "name", "") or ""),
            movement_service=svc,
            income_categories=list(income_categories),
            outcome_categories=list(outcome_categories),
            accounts_getter=lambda: list(getattr(self, "_accounts", []) or []),
            accounts_setter=lambda new_accounts: setattr(
                self, "_accounts", list(new_accounts)
            ),
            parent=None,
            on_changed=lambda: self._save_and_refresh_accounts(),
        )
        dlg.exec()

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
