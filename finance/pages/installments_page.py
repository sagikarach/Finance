from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QDialog,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QSpinBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QSizePolicy,
    Qt,
    QDate,
)
from ..models.accounts import BankAccount, BudgetAccount, MoneyAccount, parse_iso_date
from ..models.installment_plan import InstallmentPlan
from ..models.installments_service import InstallmentsService
from ..widgets.installments_selector import InstallmentsSelector
from .base_page import BasePage


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


class InstallmentPlanDialog(QDialog):
    def __init__(
        self,
        *,
        accounts: List[MoneyAccount],
        plan: Optional[InstallmentPlan] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("תכנית תשלומים")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        self._plan: Optional[InstallmentPlan] = plan
        self._accounts = accounts

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("תכנית תשלומים", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם (לדוגמה: טלוויזיה)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._vendor_query = QLineEdit(self)
        self._vendor_query.setPlaceholderText("חיפוש ספק (מופיע בתיאור התנועה)")
        root.addWidget(QLabel("חיפוש ספק", self))
        root.addWidget(self._vendor_query)

        self._account = QComboBox(self)
        self._account.setEditable(False)
        account_names: List[str] = []
        for a in accounts:
            try:
                if isinstance(a, (BankAccount, BudgetAccount)) and bool(
                    getattr(a, "active", False)
                ):
                    name = str(getattr(a, "name", "") or "").strip()
                    if name:
                        account_names.append(name)
            except Exception:
                continue
        account_names = sorted(set(account_names))
        self._account.addItems(account_names)
        root.addWidget(QLabel("חשבון מקור", self))
        root.addWidget(self._account)

        self._start_date = QDateEdit(self)
        self._start_date.setCalendarPopup(True)
        try:
            self._start_date.setDisplayFormat("yyyy-MM-dd")
        except Exception:
            pass
        root.addWidget(QLabel("תאריך התחלה", self))
        root.addWidget(self._start_date)

        self._payments_count = QSpinBox(self)
        self._payments_count.setMinimum(1)
        self._payments_count.setMaximum(240)
        root.addWidget(QLabel("מספר תשלומים", self))
        root.addWidget(self._payments_count)

        self._original_amount = QLineEdit(self)
        self._original_amount.setPlaceholderText("סכום כולל (לדוגמה: 3500)")
        root.addWidget(QLabel("סכום מקורי", self))
        root.addWidget(self._original_amount)

        self._archived = QCheckBox("בארכיון", self)
        root.addWidget(self._archived)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._save_btn = QPushButton("שמור", self)
        self._cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(self._save_btn)
        buttons.addWidget(self._cancel_btn)
        root.addLayout(buttons)

        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)

        self._load_initial()

    def _load_initial(self) -> None:
        p = self._plan
        if p is None:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
                pass
            self._payments_count.setValue(1)
            self._archived.setChecked(False)
            return
        self._name.setText(str(p.name or ""))
        self._vendor_query.setText(str(p.vendor_query or ""))
        if p.account_name:
            self._account.setCurrentText(str(p.account_name))
        try:
            dt = parse_iso_date(str(p.start_date or ""))
            self._start_date.setDate(QDate(dt.year, dt.month, dt.day))
        except Exception:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
                pass
        self._payments_count.setValue(max(1, int(p.payments_count)))
        self._original_amount.setText(str(float(p.original_amount)))
        self._archived.setChecked(bool(getattr(p, "archived", False)))

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        vendor_query = str(self._vendor_query.text() or "").strip()
        account_name = str(self._account.currentText() or "").strip()
        payments_count = int(self._payments_count.value())
        start_date = ""
        try:
            start_date = self._start_date.date().toString("yyyy-MM-dd")
        except Exception:
            start_date = ""
        try:
            original_amount = float(
                str(self._original_amount.text() or "").strip() or 0.0
            )
        except Exception:
            original_amount = 0.0
        archived = bool(self._archived.isChecked())

        if not name:
            QMessageBox.warning(self, "שגיאה", "שם לא יכול להיות ריק")
            return
        if not vendor_query:
            QMessageBox.warning(self, "שגיאה", "חיפוש ספק לא יכול להיות ריק")
            return
        if not account_name:
            QMessageBox.warning(self, "שגיאה", "צריך לבחור חשבון מקור")
            return
        if payments_count <= 0:
            QMessageBox.warning(self, "שגיאה", "מספר תשלומים חייב להיות גדול מ-0")
            return
        if original_amount < 0:
            QMessageBox.warning(self, "שגיאה", "סכום מקורי לא יכול להיות שלילי")
            return

        if self._plan is None:
            self._plan = InstallmentPlan(
                name=name,
                vendor_query=vendor_query,
                account_name=account_name,
                start_date=start_date,
                payments_count=payments_count,
                original_amount=float(original_amount),
                archived=archived,
            )
        else:
            self._plan = InstallmentPlan(
                id=self._plan.id,
                name=name,
                vendor_query=vendor_query,
                account_name=account_name,
                start_date=start_date,
                payments_count=payments_count,
                original_amount=float(original_amount),
                excluded_movement_ids=list(self._plan.excluded_movement_ids),
                archived=archived,
            )
        self.accept()

    def get_plan(self) -> Optional[InstallmentPlan]:
        return self._plan


class InstallmentsPage(BasePage):
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

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("page_title", "תשלומים")
        kwargs.setdefault("current_route", "installments")
        self._service = InstallmentsService()
        self._plans: List[InstallmentPlan] = []
        self._selected_plan_id: Optional[str] = None

        self._selector: Optional[InstallmentsSelector] = None
        self._edit_btn: Optional[QToolButton] = None
        self._table: Optional[QTableWidget] = None
        self._exclude_btn: Optional[QToolButton] = None
        self._card_ratio: Optional[QLabel] = None
        self._card_original: Optional[QLabel] = None
        self._card_paid: Optional[QLabel] = None
        self._card_overpaid: Optional[QLabel] = None

        super().__init__(*args, **kwargs)

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._reload()

    def _build_content(self, content_col: QVBoxLayout) -> None:
        self._clear_content_layout(content_col)

        root = QWidget(self)
        try:
            root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        content_col.addWidget(root, 1)

        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        header_card = QWidget(root)
        header_card.setObjectName("Sidebar")
        try:
            header_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_card_l = QVBoxLayout(header_card)
        header_card_l.setContentsMargins(16, 14, 16, 14)
        header_card_l.setSpacing(0)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self._selector = InstallmentsSelector(
            header_card,
            on_selected=self._on_plan_selected,
            on_add_plan=self._on_add_clicked,
            on_delete_plan=self._on_delete_clicked,
        )
        header_row.addWidget(self._selector, 0)
        header_row.addStretch(1)

        self._exclude_btn = QToolButton(header_card)
        self._exclude_btn.setObjectName("IconButton")
        self._exclude_btn.setText("🚫")
        self._exclude_btn.setToolTip("החרג תנועה מהרשימה")
        self._exclude_btn.clicked.connect(self._on_exclude_selected_row)
        header_row.addWidget(self._exclude_btn)

        self._edit_btn = QToolButton(header_card)
        self._edit_btn.setObjectName("IconButton")
        self._edit_btn.setText("✎")
        self._edit_btn.setToolTip("עריכת תכנית")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        header_row.addWidget(self._edit_btn)

        header_card_l.addLayout(header_row)
        lay.addWidget(header_card, 0)

        row1 = QWidget(root)
        row1_l = QHBoxLayout(row1)
        row1_l.setContentsMargins(0, 0, 0, 0)
        row1_l.setSpacing(12)

        cards_col = QWidget(row1)
        cards_col_l = QVBoxLayout(cards_col)
        cards_col_l.setContentsMargins(0, 0, 0, 0)
        cards_col_l.setSpacing(12)

        def build_card(title_text: str, style: str) -> QLabel:
            card = QWidget(cards_col)
            card.setObjectName(style)
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                card.setAutoFillBackground(True)
            except Exception:
                pass
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(6)
            title = QLabel(title_text, card)
            title.setObjectName("StatTitle")
            value = QLabel("", card)
            value.setObjectName("StatValueCard")
            cl.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(value, 0, Qt.AlignmentFlag.AlignHCenter)
            cards_col_l.addWidget(card, 0)
            return value

        self._card_ratio = build_card("תשלומים (סה״כ/נמצאו)", "StatCardYellow")
        self._card_original = build_card("סכום מקורי", "StatCardPurple")
        self._card_paid = build_card("שולם עד כה", "StatCardGreen")
        self._card_overpaid = build_card("חריגה", "StatCardRed")
        cards_col_l.addStretch(1)

        table_card = QWidget(row1)
        table_card.setObjectName("Sidebar")
        try:
            table_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        table_card_l = QVBoxLayout(table_card)
        table_card_l.setContentsMargins(16, 16, 16, 16)
        table_card_l.setSpacing(8)

        self._table = QTableWidget(table_card)
        self._table.setObjectName("ActionHistoryTableWidget")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["תאריך", "סכום", "קטגוריה", "תיאור"])
        self._table.setRowCount(0)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        try:
            self._table.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            header = self._table.horizontalHeader()
            if header is not None:
                header.setObjectName("ActionHistoryHeader")
        except Exception:
            pass
        table_card_l.addWidget(self._table, 1)

        row1_l.addWidget(cards_col, 1)
        row1_l.addWidget(table_card, 2)
        lay.addWidget(row1, 1)

        self._reload()

    def _reload(self) -> None:
        try:
            self._plans = self._service.list_plans()
        except Exception:
            self._plans = []
        if self._selected_plan_id and not any(
            p.id == self._selected_plan_id for p in self._plans
        ):
            self._selected_plan_id = None
        if self._selected_plan_id is None and self._plans:
            self._selected_plan_id = self._plans[0].id

        if self._selector is not None:
            self._selector.set_plans(self._plans, self._selected_plan_id)

        self._refresh_details()

    def _selected_plan(self) -> Optional[InstallmentPlan]:
        pid = str(self._selected_plan_id or "").strip()
        if not pid:
            return None
        for p in self._plans:
            if p.id == pid:
                return p
        return None

    def _refresh_details(self) -> None:
        plan = self._selected_plan()
        if self._table is None:
            return
        if plan is None:
            self._table.setRowCount(0)
            if self._card_ratio is not None:
                self._card_ratio.setText("")
            if self._card_original is not None:
                self._card_original.setText("")
            if self._card_paid is not None:
                self._card_paid.setText("")
            if self._card_overpaid is not None:
                self._card_overpaid.setText("")
            if self._edit_btn is not None:
                self._edit_btn.setEnabled(False)
            if self._exclude_btn is not None:
                self._exclude_btn.setEnabled(False)
            return

        if self._edit_btn is not None:
            self._edit_btn.setEnabled(True)
        if self._exclude_btn is not None:
            self._exclude_btn.setEnabled(True)

        stats = self._service.compute_stats(plan)
        if self._card_ratio is not None:
            self._card_ratio.setText(
                f"{int(plan.payments_count)}/{int(stats.paid_count)}"
            )
        if self._card_original is not None:
            self._card_original.setText(_fmt_money(float(plan.original_amount)))
        if self._card_paid is not None:
            self._card_paid.setText(_fmt_money(float(stats.total_paid)))
        if self._card_overpaid is not None:
            self._card_overpaid.setText(_fmt_money(float(stats.overpaid)))

        self._table.setRowCount(len(stats.matched_movements))
        for row, m in enumerate(stats.matched_movements):
            self._table.setItem(row, 0, QTableWidgetItem(str(m.date)))
            self._table.setItem(row, 1, QTableWidgetItem(str(m.amount)))
            self._table.setItem(row, 2, QTableWidgetItem(str(m.category)))
            self._table.setItem(row, 3, QTableWidgetItem(str(m.description or "")))
            try:
                for col in range(4):
                    it = self._table.item(row, col)
                    if it is not None:
                        it.setData(Qt.ItemDataRole.UserRole, str(m.id))
            except Exception:
                pass
        try:
            self._table.resizeColumnsToContents()
        except Exception:
            pass

    def _on_plan_selected(self, plan_id: str) -> None:
        self._selected_plan_id = str(plan_id or "").strip() or None
        self._refresh_details()

    def _on_add_clicked(self) -> None:
        dlg = InstallmentPlanDialog(accounts=self._accounts, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        plan = dlg.get_plan()
        if plan is None:
            return
        self._service.upsert_plan(plan)
        self._selected_plan_id = plan.id
        self._reload()

    def _on_edit_clicked(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "עריכה", "בחר תכנית כדי לערוך")
            return
        dlg = InstallmentPlanDialog(accounts=self._accounts, plan=plan, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_plan()
        if updated is None:
            return
        self._service.upsert_plan(updated)
        self._selected_plan_id = updated.id
        self._reload()

    def _on_delete_clicked(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "מחיקה", "בחר תכנית כדי למחוק")
            return
        res = QMessageBox.question(
            self,
            "מחיקה",
            f'למחוק את "{plan.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        self._service.delete_plan(plan.id)
        self._selected_plan_id = None
        self._reload()

    def _selected_row_movement_id(self) -> Optional[str]:
        if self._table is None:
            return None
        try:
            row = self._table.currentRow()
            if row < 0:
                return None
            item = self._table.item(row, 0)
            if item is None:
                return None
            mid = item.data(Qt.ItemDataRole.UserRole)
            mid = str(mid or "").strip()
            return mid if mid else None
        except Exception:
            return None

    def _on_exclude_selected_row(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "בחירה", "בחר תכנית")
            return
        mid = self._selected_row_movement_id()
        if not mid:
            QMessageBox.information(self, "בחירה", "בחר תנועה כדי להחריג")
            return
        self._service.exclude_movement(plan_id=plan.id, movement_id=mid)
        self._reload()
