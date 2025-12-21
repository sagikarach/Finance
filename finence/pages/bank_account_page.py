from __future__ import annotations

from typing import Callable, Dict, List, Optional
from pathlib import Path

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QToolButton,
    QPushButton,
    QSizePolicy,
)
from ..data.provider import AccountsProvider
from ..models.accounts import BankAccount
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
from .base_page import BasePage


class BankAccountPage(BasePage):
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
            page_title="פרטי חשבון בנק",
            current_route="bank_account",
        )
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
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
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
            selected_name = str(self._app_context.get("selected_bank_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[BankAccount] = None
        for acc in self._accounts:
            if isinstance(acc, BankAccount) and acc.name == selected_name:
                target = acc
                break

        if target is None:
            placeholder = QLabel("לא נבחר חשבון בנק", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

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

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        name_row.addStretch(1)
        name_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)

        summary_col.addLayout(name_row)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignRight)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        if target.name == "בנק":
            import_btn = QPushButton("ייבוא קובץ הוצאות", top_card)
            import_btn.setObjectName("AddButton")
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

        chart_card = create_bank_history_chart_card(self, target, format_currency)

        main_col.addWidget(top_card, 1)
        main_col.addWidget(chart_card, 2)

    def _on_import_csv(self, account: BankAccount) -> None:
        try:
            from PySide6.QtWidgets import QFileDialog
        except Exception:
            try:
                from PyQt6.QtWidgets import QFileDialog  # type: ignore
            except Exception:
                return

        try:
            file_path, _ = QFileDialog.getOpenFileName(
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

                    on_category_added = _on_cat_added
                elif provider is not None and hasattr(provider, "add_category"):
                    on_category_added = getattr(provider, "add_category")
            except Exception:
                on_category_added = None

            pending_sorted = sorted(pending, key=lambda x: x.confidence)
            top_3_pending = pending_sorted[:3]

            if top_3_pending:
                try:
                    from ..ui.batch_outcome_review_dialog import (
                        BatchOutcomeReviewDialog,
                    )

                    dlg = BatchOutcomeReviewDialog(
                        top_3_pending,
                        categories,
                        on_category_added=on_category_added,
                        parent=None,
                    )
                    result = dlg.exec()
                except Exception:
                    result = False

                if result:
                    results = dlg.get_results()
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
        svc = getattr(self, "_accounts_service", None)
        if svc is not None:
            try:
                self._accounts = svc.load_accounts()
            except Exception:
                pass
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
