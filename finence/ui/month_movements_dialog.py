from __future__ import annotations

from dataclasses import replace
from typing import Callable, Dict, List, Optional, Tuple

from ..models.accounts import parse_iso_date
from ..models.bank_movement import BankMovement, MovementType
from ..models.bank_movement_service import BankMovementService
from ..qt import (
    QComboBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
)
from .dialog_utils import setup_standard_rtl_dialog, wrap_hebrew_rtl, unwrap_rtl


class MonthMovementsDialog(QDialog):
    def __init__(
        self,
        *,
        year: int,
        month: int,
        movement_service: BankMovementService,
        parent: Optional[QDialog] = None,
        on_saved: Optional[Callable[[], None]] = None,
        on_delete_movement: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._year = year
        self._month = month
        self._movement_service = movement_service
        self._on_saved = on_saved
        self._on_delete_movement = on_delete_movement

        self._income_table: Optional[QTableWidget] = None
        self._expense_table: Optional[QTableWidget] = None

        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self,
            title="עריכת תנועות חודשיות",
            margins=(32, 24, 32, 24),
            spacing=12,
        )
        try:
            self.setMinimumSize(1100, 700)
            self.resize(1280, 780)
            self.setSizeGripEnabled(True)
        except Exception:
            try:
                self.setMinimumWidth(1100)
                self.setMinimumHeight(700)
            except Exception:
                pass

        title = QLabel(f"{year:04d}-{month:02d}", self)
        title.setObjectName("HeaderTitle")
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title)

        tables_row = QHBoxLayout()
        tables_row.setSpacing(16)

        income_col = QVBoxLayout()
        income_col.setSpacing(8)
        income_title = QLabel("הכנסות", self)
        income_title.setObjectName("Subtitle")
        income_col.addWidget(income_title)
        self._income_table = self._build_table(self)
        income_col.addWidget(self._income_table, 1)

        expense_col = QVBoxLayout()
        expense_col.setSpacing(8)
        expense_title = QLabel("הוצאות", self)
        expense_title.setObjectName("Subtitle")
        expense_col.addWidget(expense_title)
        self._expense_table = self._build_table(self)
        expense_col.addWidget(self._expense_table, 1)

        tables_row.addLayout(income_col, 1)
        tables_row.addLayout(expense_col, 1)
        layout.addLayout(tables_row, 1)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        cancel_btn = QPushButton("ביטול", self)
        save_btn = QPushButton("שמור שינויים", self)
        save_btn.setDefault(True)
        buttons_row.addWidget(cancel_btn, 0)
        buttons_row.addWidget(save_btn, 0)
        layout.addLayout(buttons_row, 0)

        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._on_save)

        self._load()

    def _build_table(self, parent: QDialog) -> QTableWidget:
        t = QTableWidget(parent)
        t.setColumnCount(7)
        t.setRowCount(0)
        headers = ["תאריך", "חשבון", "סכום", "קטגוריה", "סוג", "תיאור", "מחק"]
        t.setHorizontalHeaderLabels(headers)
        try:
            t.verticalHeader().setVisible(False)
            t.setShowGrid(False)
            t.setAlternatingRowColors(False)
            t.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            t.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        except Exception:
            pass
        try:
            header = t.horizontalHeader()
            header.setStretchLastSection(False)
            if QHeaderView is not None:
                try:
                    rtc = QHeaderView.ResizeMode.ResizeToContents
                    stretch = QHeaderView.ResizeMode.Stretch
                except Exception:
                    rtc = QHeaderView.ResizeToContents
                    stretch = QHeaderView.Stretch

                header.setSectionResizeMode(0, rtc)  # date
                header.setSectionResizeMode(1, rtc)  # account
                header.setSectionResizeMode(2, rtc)  # amount
                header.setSectionResizeMode(3, rtc)  # category
                header.setSectionResizeMode(4, rtc)  # type
                header.setSectionResizeMode(5, stretch)  # description
                header.setSectionResizeMode(6, rtc)  # delete button
        except Exception:
            pass
        return t

    def _list_categories(self, is_income: bool) -> List[str]:
        try:
            return self._movement_service.list_categories(is_income)
        except Exception:
            return []

    def _load(self) -> None:
        try:
            all_movements = list(self._movement_service.list_movements())
        except Exception:
            all_movements = []

        in_month: List[BankMovement] = []
        for m in all_movements:
            try:
                dt = parse_iso_date(m.date)
                if dt.year == self._year and dt.month == self._month:
                    in_month.append(m)
            except Exception:
                continue

        in_month.sort(key=lambda m: parse_iso_date(m.date), reverse=True)

        incomes = [m for m in in_month if float(m.amount) > 0]
        expenses = [m for m in in_month if float(m.amount) <= 0]

        self._populate_table(self._income_table, incomes, is_income=True)
        self._populate_table(self._expense_table, expenses, is_income=False)

    def _populate_table(
        self,
        table: Optional[QTableWidget],
        movements: List[BankMovement],
        *,
        is_income: bool,
    ) -> None:
        if table is None:
            return
        table.setRowCount(len(movements))

        cats = self._list_categories(is_income)
        type_options = [
            MovementType.MONTHLY.value,
            MovementType.YEARLY.value,
            MovementType.ONE_TIME.value,
        ]

        try:
            align = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        except Exception:
            align = None

        for row, m in enumerate(movements):
            date_item = QTableWidgetItem(str(m.date))
            try:
                date_item.setData(Qt.ItemDataRole.UserRole, m.id)
            except Exception:
                pass
            acct_item = QTableWidgetItem(str(m.account_name))
            amount_item = QTableWidgetItem(str(m.amount))
            desc_item = QTableWidgetItem(wrap_hebrew_rtl(m.description or ""))

            for it in (date_item, acct_item, amount_item):
                try:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                except Exception:
                    pass
            try:
                if align is not None:
                    date_item.setTextAlignment(align)
                    acct_item.setTextAlignment(align)
                    amount_item.setTextAlignment(align)
                    desc_item.setTextAlignment(align)
            except Exception:
                pass

            cat_combo = QComboBox(table)
            if cats:
                cat_combo.addItems(cats)
            if m.category and m.category not in cats:
                cat_combo.addItem(m.category)
            if m.category:
                cat_combo.setCurrentText(m.category)

            type_combo = QComboBox(table)
            type_combo.addItems([wrap_hebrew_rtl(x) for x in type_options])
            current_type = m.type.value
            for idx, opt in enumerate(type_options):
                if opt == current_type:
                    type_combo.setCurrentIndex(idx)
                    break

            table.setItem(row, 0, date_item)
            table.setItem(row, 1, acct_item)
            table.setItem(row, 2, amount_item)
            table.setCellWidget(row, 3, cat_combo)
            table.setCellWidget(row, 4, type_combo)
            table.setItem(row, 5, desc_item)
            delete_btn = QPushButton("מחק", table)
            delete_btn.setObjectName("DeleteButton")
            try:
                delete_btn.clicked.connect(
                    lambda _=False, mid=str(m.id): self._delete_movement(mid)
                )
            except Exception:
                pass
            table.setCellWidget(row, 6, delete_btn)

        try:
            table.resizeColumnsToContents()
        except Exception:
            pass

    def _read_row(self, table: QTableWidget, row: int) -> Tuple[str, str]:
        cat = ""
        desc = ""
        try:
            w = table.cellWidget(row, 3)
            if isinstance(w, QComboBox):
                cat = w.currentText().strip()
        except Exception:
            cat = ""
        try:
            item = table.item(row, 5)
            if item is not None:
                desc = unwrap_rtl(item.text()).strip()
        except Exception:
            desc = ""
        return cat, desc

    def _read_type(self, table: QTableWidget, row: int) -> Optional[MovementType]:
        try:
            w = table.cellWidget(row, 4)
            if isinstance(w, QComboBox):
                txt = unwrap_rtl(w.currentText()).strip()
                return MovementType(txt)
        except Exception:
            return None
        return None

    def _on_save(self) -> None:
        try:
            all_movements = list(self._movement_service.list_movements())
        except Exception:
            all_movements = []

        by_id: Dict[str, BankMovement] = {m.id: m for m in all_movements}
        changed: List[BankMovement] = []

        def apply_updates(table: Optional[QTableWidget]) -> None:
            if table is None:
                return
            for row in range(table.rowCount()):
                try:
                    date_item = table.item(row, 0)
                    if date_item is None:
                        continue
                    movement_id = None
                    try:
                        movement_id = date_item.data(Qt.ItemDataRole.UserRole)
                    except Exception:
                        movement_id = None
                    if not isinstance(movement_id, str) or not movement_id:
                        continue
                    m = by_id.get(movement_id)
                    if m is None:
                        continue
                    cat, desc = self._read_row(table, row)
                    mtype = self._read_type(table, row)
                    new_m = replace(
                        m,
                        category=cat or m.category,
                        description=desc,
                        type=mtype or m.type,
                    )
                    by_id[movement_id] = new_m
                    if (
                        new_m.category != m.category
                        or new_m.description != m.description
                        or new_m.type != m.type
                    ):
                        changed.append(new_m)
                except Exception:
                    continue

        apply_updates(self._income_table)
        apply_updates(self._expense_table)

        updated = list(by_id.values())
        try:
            self._movement_service.save_movements(
                updated, changed_movements=changed or None
            )
        except Exception:
            return

        if self._on_saved is not None:
            try:
                self._on_saved()
            except Exception:
                pass
        self.accept()

    def _delete_movement(self, movement_id: str) -> None:
        movement_id = str(movement_id or "").strip()
        if not movement_id:
            return
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("מחיקת תנועה")
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(24, 18, 24, 18)
            msg = QLabel("האם למחוק את התנועה הזו?", dlg)
            msg.setWordWrap(True)
            lay.addWidget(msg)
            row = QHBoxLayout()
            cancel_btn = QPushButton("ביטול", dlg)
            del_btn = QPushButton("מחק", dlg)
            del_btn.setObjectName("DeleteButton")
            row.addWidget(cancel_btn)
            row.addStretch(1)
            row.addWidget(del_btn)
            lay.addLayout(row)
            cancel_btn.clicked.connect(dlg.reject)
            del_btn.clicked.connect(dlg.accept)
            if not dlg.exec():
                return
        except Exception:
            return

        if self._on_delete_movement is not None:
            try:
                self._on_delete_movement(movement_id)
            except Exception:
                return
        else:
            return

        try:
            self._load()
        except Exception:
            pass
        if self._on_saved is not None:
            try:
                self._on_saved()
            except Exception:
                pass
