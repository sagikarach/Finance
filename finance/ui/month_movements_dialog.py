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
    QToolButton,
    Qt,
    QVBoxLayout,
    QWidget,
)
from .dialog_utils import setup_standard_rtl_dialog, make_table_danger_button, FullCellDelegate


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
        self._income_container: Optional[QWidget] = None
        self._expense_container: Optional[QWidget] = None
        self._income_toggle: Optional[QPushButton] = None
        self._expense_toggle: Optional[QPushButton] = None
        self._title_label: Optional[QLabel] = None

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

        # Header: ← / → arrows flanking the month title to step between months.
        is_dark = False
        try:
            from ..qt import QApplication

            app = QApplication.instance()
            if app is not None:
                is_dark = str(app.property("theme") or "light") == "dark"
        except Exception:
            is_dark = False

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.addStretch(1)

        # Left arrow steps to the previous (older) month, right arrow to the next
        # (newer) one. In RTL the first-added widget sits on the right, so add the
        # "next" button first to keep ← on the left and → on the right.
        self._prev_btn = QToolButton(self)
        self._prev_btn.setObjectName("IconButton")
        self._prev_btn.setToolTip("חודש קודם")
        self._next_btn = QToolButton(self)
        self._next_btn.setObjectName("IconButton")
        self._next_btn.setToolTip("חודש הבא")
        for b, icon, fallback in (
            (self._prev_btn, "arrow_left", "←"),
            (self._next_btn, "arrow_right", "→"),
        ):
            try:
                from ..utils.icons import apply_icon

                apply_icon(b, icon, size=20, is_dark=is_dark)
                if b.icon().isNull():
                    b.setText(fallback)
            except Exception:
                b.setText(fallback)
            try:
                b.setCursor(Qt.CursorShape.PointingHandCursor)
            except Exception:
                pass
        self._prev_btn.clicked.connect(lambda: self._shift_month(-1))
        self._next_btn.clicked.connect(lambda: self._shift_month(1))

        self._title_label = QLabel(self._month_title(year, month), self)
        self._title_label.setObjectName("HeaderTitle")
        try:
            self._title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        header_row.addWidget(self._next_btn, 0)
        header_row.addWidget(self._title_label, 0)
        header_row.addWidget(self._prev_btn, 0)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        # Tab selector (asset-page style): show the outcome OR the income table,
        # never both. The active tab merges into the panel directly below it.
        tabs_wrap = QWidget(self)
        tabs_wrap_l = QVBoxLayout(tabs_wrap)
        tabs_wrap_l.setContentsMargins(0, 0, 0, 0)
        tabs_wrap_l.setSpacing(0)

        tab_bar_w = QWidget(tabs_wrap)
        tab_bar = QHBoxLayout(tab_bar_w)
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.setSpacing(4)
        self._expense_toggle = QPushButton("הוצאות", tab_bar_w)
        self._expense_toggle.setObjectName("AssetTabButton")
        self._income_toggle = QPushButton("הכנסות", tab_bar_w)
        self._income_toggle.setObjectName("AssetTabButton")
        for btn in (self._expense_toggle, self._income_toggle):
            btn.setCheckable(True)
            try:
                btn.setMinimumHeight(34)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
            except Exception:
                pass
        self._expense_toggle.clicked.connect(
            lambda: self._set_view(show_income=False)
        )
        self._income_toggle.clicked.connect(
            lambda: self._set_view(show_income=True)
        )
        tab_bar.addWidget(self._expense_toggle, 0)
        tab_bar.addWidget(self._income_toggle, 0)
        tab_bar.addStretch(1)
        tabs_wrap_l.addWidget(tab_bar_w, 0)

        self._expense_container = self._build_table_panel(tabs_wrap)
        self._expense_table = self._build_table(self._expense_container)
        self._expense_container.layout().addWidget(self._expense_table, 1)

        self._income_container = self._build_table_panel(tabs_wrap)
        self._income_table = self._build_table(self._income_container)
        self._income_container.layout().addWidget(self._income_table, 1)

        tabs_wrap_l.addWidget(self._expense_container, 1)
        tabs_wrap_l.addWidget(self._income_container, 1)
        layout.addWidget(tabs_wrap, 1)

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
        # Default to the outcome (expenses) table.
        self._set_view(show_income=False)

    @staticmethod
    def _month_title(year: int, month: int) -> str:
        return f"{int(month)}.{int(year)}"

    def _shift_month(self, delta: int) -> None:
        m = self._month + int(delta)
        y = self._year
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        self._year, self._month = y, m
        if self._title_label is not None:
            self._title_label.setText(self._month_title(y, m))
        self._load()

    def _build_table_panel(self, parent: QWidget) -> QWidget:
        panel = QWidget(parent)
        panel.setObjectName("AssetTablePanel")
        try:
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        col = QVBoxLayout(panel)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(8)
        return panel

    def _set_view(self, *, show_income: bool) -> None:
        if self._income_container is not None:
            self._income_container.setVisible(show_income)
        if self._expense_container is not None:
            self._expense_container.setVisible(not show_income)
        if self._income_toggle is not None:
            self._income_toggle.setChecked(show_income)
        if self._expense_toggle is not None:
            self._expense_toggle.setChecked(not show_income)

    def _build_table(self, parent: QDialog) -> QTableWidget:
        t = QTableWidget(parent)
        t.setColumnCount(7)
        t.setRowCount(0)
        headers = ["תאריך", "חשבון", "סכום", "קטגוריה", "סוג", "תיאור", "מחק"]
        t.setHorizontalHeaderLabels(headers)
        try:
            t.verticalHeader().setVisible(False)
            t.verticalHeader().setDefaultSectionSize(38)
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

                fixed = QHeaderView.ResizeMode.Fixed

                header.setSectionResizeMode(0, rtc)  # date
                header.setSectionResizeMode(1, rtc)  # account
                header.setSectionResizeMode(2, rtc)  # amount
                # category/type hold combo boxes; ResizeToContents ignores the
                # widget width, so we keep them Fixed and size each to fit the
                # widest combo after populating (see _fit_combo_columns).
                header.setSectionResizeMode(3, fixed)  # category
                header.setSectionResizeMode(4, fixed)  # type
                header.setSectionResizeMode(5, stretch)  # description
                header.setSectionResizeMode(6, fixed)  # מחק
                t.setColumnWidth(6, 80)
        except Exception:
            pass
        t.setItemDelegateForColumn(6, FullCellDelegate(t))
        return t

    @staticmethod
    def _make_combo_fit(combo: QComboBox) -> None:
        """Let the combo's size hint grow to fit its widest item + arrow."""
        try:
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToContents
            )
        except Exception:
            try:
                combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            except Exception:
                pass

    def _fit_combo_columns(self, table: QTableWidget) -> None:
        """Size the category/type columns to the widest combo they hold.

        ResizeToContents ignores cell-widget widths, so we measure the combos
        directly and size the (Fixed-mode) columns to fit — re-run on every
        populate so month navigation keeps the right widths.
        """
        try:
            for col in (3, 4):  # category, type
                width = 0
                for row in range(table.rowCount()):
                    w = table.cellWidget(row, col)
                    if w is not None:
                        width = max(width, w.sizeHint().width())
                if width <= 0:
                    hdr = table.horizontalHeaderItem(col)
                    text = hdr.text() if hdr is not None else ""
                    width = table.fontMetrics().horizontalAdvance(text)
                table.setColumnWidth(col, int(width) + 24)
        except Exception:
            pass

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
            desc_item = QTableWidgetItem(m.description or "")

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
            self._make_combo_fit(cat_combo)
            if cats:
                cat_combo.addItems(cats)
            if m.category and m.category not in cats:
                cat_combo.addItem(m.category)
            if m.category:
                cat_combo.setCurrentText(m.category)

            type_combo = QComboBox(table)
            self._make_combo_fit(type_combo)
            type_combo.addItems(type_options)
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
            delete_btn = make_table_danger_button("מחק", table)
            delete_btn.clicked.connect(
                lambda _=False, mid=str(m.id): self._delete_movement(mid)
            )
            table.setCellWidget(row, 6, delete_btn)

        self._fit_combo_columns(table)

        # Note: do NOT call resizeColumnsToContents() here. The header already
        # drives column widths (cols 0-4 ResizeToContents, col 5 Stretch, col 6
        # Fixed); a manual resize collapses the Stretch description column and it
        # only recovers on a geometry event — so it would break after an in-place
        # reload (e.g. stepping months via the arrows).
        try:
            table.resizeRowsToContents()
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
                desc = item.text().strip()
        except Exception:
            desc = ""
        return cat, desc

    def _read_type(self, table: QTableWidget, row: int) -> Optional[MovementType]:
        try:
            w = table.cellWidget(row, 4)
            if isinstance(w, QComboBox):
                txt = w.currentText().strip()
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
        except Exception as _e:
            try:
                from ..qt import QMessageBox
                QMessageBox.warning(self, "שגיאה בשמירה", f"השמירה נכשלה: {_e}")
            except Exception:
                pass
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
