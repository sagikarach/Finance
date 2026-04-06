from __future__ import annotations

from dataclasses import replace
from typing import Callable, List, Optional, Tuple, Dict

from ..models.accounts import parse_iso_date
from ..models.accounts import MoneyAccount
from ..models.bank_movement import BankMovement, MovementType
from ..models.bank_movement_service import BankMovementService
from ..qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from .dialog_utils import setup_standard_rtl_dialog, wrap_hebrew_rtl, unwrap_rtl, make_table_danger_button


class SibusExpensesDialog(QDialog):
    def __init__(
        self,
        *,
        account_name: str,
        movement_service: BankMovementService,
        categories: List[str],
        accounts_getter: Callable[[], List[MoneyAccount]],
        accounts_setter: Callable[[List[MoneyAccount]], None],
        parent: Optional[QWidget] = None,
        on_changed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._account_name = str(account_name or "").strip()
        self._movement_service = movement_service
        self._categories = list(categories or [])
        self._accounts_getter = accounts_getter
        self._accounts_setter = accounts_setter
        self._on_changed = on_changed

        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self,
            title="הוצאות סיבוס",
            margins=(32, 24, 32, 24),
            spacing=12,
        )
        self.setMinimumWidth(880)
        self.setMinimumHeight(560)

        title = QLabel(self._account_name or "סיבוס", self)
        title.setObjectName("HeaderTitle")
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title)

        self._table = QTableWidget(self)
        self._table.setObjectName("MovementsTable")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["תאריך", "סכום", "קטגוריה", "סוג", "תיאור", "מחיקה"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        try:
            self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass
        layout.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        refresh_btn = QPushButton("רענן", self)
        refresh_btn.clicked.connect(self.refresh)
        buttons.addWidget(refresh_btn)

        buttons.addStretch(1)

        save_btn = QPushButton("שמור", self)
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self._on_save)
        buttons.addWidget(save_btn)

        close_btn = QPushButton("סגור", self)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)

        layout.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        try:
            all_movements = list(self._movement_service.list_movements())
        except Exception:
            all_movements = []

        expenses: List[BankMovement] = []
        for m in all_movements:
            try:
                if str(m.account_name) != self._account_name:
                    continue
                if bool(getattr(m, "is_transfer", False)):
                    continue
                if float(m.amount) >= 0:
                    continue
            except Exception:
                continue
            expenses.append(m)

        try:
            expenses.sort(key=lambda m: parse_iso_date(str(m.date)), reverse=True)
        except Exception:
            pass

        self._table.setRowCount(len(expenses))

        type_options = [
            MovementType.MONTHLY.value,
            MovementType.YEARLY.value,
            MovementType.ONE_TIME.value,
        ]

        try:
            align = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        except Exception:
            align = None

        for row, m in enumerate(expenses):
            date_item = QTableWidgetItem(str(m.date))
            amount_item = QTableWidgetItem(str(abs(float(m.amount))))
            desc_item = QTableWidgetItem(wrap_hebrew_rtl(m.description or ""))

            # Store movement id for save/delete operations.
            try:
                date_item.setData(Qt.ItemDataRole.UserRole, m.id)
            except Exception:
                pass

            # date + amount are read-only
            for it in (date_item, amount_item):
                try:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                except Exception:
                    pass

            try:
                if align is not None:
                    date_item.setTextAlignment(align)
                    amount_item.setTextAlignment(align)
                    desc_item.setTextAlignment(align)
            except Exception:
                pass

            cat_combo = QComboBox(self._table)
            if self._categories:
                cat_combo.addItems(self._categories)
            if m.category and m.category not in self._categories:
                cat_combo.addItem(m.category)
            if m.category:
                cat_combo.setCurrentText(m.category)

            type_combo = QComboBox(self._table)
            type_combo.addItems([wrap_hebrew_rtl(x) for x in type_options])
            current_type = str(m.type.value)
            for idx, opt in enumerate(type_options):
                if opt == current_type:
                    type_combo.setCurrentIndex(idx)
                    break

            delete_btn = make_table_danger_button("מחק", self._table)
            delete_btn.clicked.connect(
                lambda _=None, mid=str(m.id): self._on_delete(mid)
            )

            self._table.setItem(row, 0, date_item)
            self._table.setItem(row, 1, amount_item)
            self._table.setCellWidget(row, 2, cat_combo)
            self._table.setCellWidget(row, 3, type_combo)
            self._table.setItem(row, 4, desc_item)
            self._table.setCellWidget(row, 5, delete_btn)

        try:
            self._table.resizeColumnsToContents()
        except Exception:
            pass

    def _read_row(self, row: int) -> Tuple[str, MovementType, Optional[str]]:
        category = ""
        mtype: MovementType = MovementType.ONE_TIME
        desc: Optional[str] = None
        cat_widget = self._table.cellWidget(row, 2)
        if isinstance(cat_widget, QComboBox):
            category = str(cat_widget.currentText() or "").strip()

        type_widget = self._table.cellWidget(row, 3)
        if isinstance(type_widget, QComboBox):
            type_str = unwrap_rtl(type_widget.currentText())
            try:
                mtype = MovementType(type_str)
            except Exception:
                if "חודש" in type_str:
                    mtype = MovementType.MONTHLY
                elif "שנת" in type_str:
                    mtype = MovementType.YEARLY
                else:
                    mtype = MovementType.ONE_TIME

        desc_item = self._table.item(row, 4)
        desc_raw = ""
        if desc_item is not None:
            try:
                desc_raw = unwrap_rtl(desc_item.text() or "")
            except Exception:
                desc_raw = desc_item.text() or ""
        desc = str(desc_raw or "").strip() or None
        return category, mtype, desc

    def _on_save(self) -> None:
        try:
            all_movements = list(self._movement_service.list_movements())
        except Exception:
            all_movements = []

        by_id: Dict[str, BankMovement] = {m.id: m for m in all_movements}
        changed: List[BankMovement] = []

        for row in range(self._table.rowCount()):
            date_item = self._table.item(row, 0)
            if date_item is None:
                continue
            try:
                movement_id = date_item.data(Qt.ItemDataRole.UserRole)
            except Exception:
                movement_id = None
            if not isinstance(movement_id, str) or not movement_id:
                continue

            m = by_id.get(movement_id)
            if m is None:
                continue

            category, mtype, desc = self._read_row(row)
            new_m = replace(
                m,
                category=category or m.category,
                type=mtype or m.type,
                description=desc,
            )
            if (
                new_m.category != m.category
                or new_m.type != m.type
                or new_m.description != m.description
            ):
                by_id[movement_id] = new_m
                changed.append(new_m)

        if not changed:
            self.accept()
            return

        updated = list(by_id.values())
        try:
            self._movement_service.save_movements(updated, changed_movements=changed)
        except Exception as _e:
            try:
                from ..qt import QMessageBox
                QMessageBox.warning(self, "שגיאה בשמירה", f"השמירה נכשלה: {_e}")
            except Exception:
                pass
            return

        if self._on_changed is not None:
            try:
                self._on_changed()
            except Exception:
                pass

        self.accept()

    def _on_delete(self, movement_id: str) -> None:
        try:
            accounts = list(self._accounts_getter() or [])
        except Exception:
            accounts = []

        try:
            new_accounts = self._movement_service.delete_movement(
                accounts,
                movement_id=str(movement_id),
                record_history=True,
            )
            self._accounts_setter(list(new_accounts))
        except Exception:
            return

        if self._on_changed is not None:
            try:
                self._on_changed()
            except Exception:
                pass

        self.refresh()
