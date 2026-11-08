"""סיווג תיאורי הוצאות: every distinct expense description once, with its
count, total and current category; select rows, pick a category, apply, save.

Saving changes only the ``category`` of the matching expense movements and goes
through ``BankMovementService.save_movements`` (local save + push of the changed
movements only, like any other edit)."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..models.bank_movement_service import BankMovementService
from ..models.category_tree import UNCLASSIFIED_NAME, active_tree
from ..models.description_categories import (
    DescriptionGroup,
    apply_description_categories,
    category_choices,
    group_expense_descriptions,
)
from ..qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QWidget,
)
from .dialog_utils import setup_standard_rtl_dialog
from ..widgets.category_combo import CategoryComboBox
from ..utils.safe import QT_ERRORS

_FILTERS = [
    ("all", "כל התיאורים"),
    ("unclassified", "טרם סווג"),
    ("parent_only", "קטגוריה ראשית בלבד"),
    ("mixed", "קטגוריות מעורבות"),
    ("pending", "שינויים שלא נשמרו"),
]
COL_DESC, COL_COUNT, COL_TOTAL, COL_LAST, COL_CURRENT, COL_NEW = range(6)


class _SortItem(QTableWidgetItem):
    """Sorts by the numeric value kept in UserRole."""

    def __lt__(self, other) -> bool:  # type: ignore[override]
        try:
            return float(self.data(Qt.ItemDataRole.UserRole)) < float(
                other.data(Qt.ItemDataRole.UserRole)
            )
        except (TypeError, ValueError):
            return super().__lt__(other)


class ExpenseDescriptionsDialog(QDialog):
    def __init__(
        self,
        *,
        movement_service: BankMovementService,
        categories: List[str],
        parent: Optional[QWidget] = None,
        on_saved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._service = movement_service
        self._on_saved = on_saved
        self._tree = active_tree()
        self._choices = category_choices(self._tree, categories)
        self._movements = list(self._service.list_movements())
        self._groups: List[DescriptionGroup] = group_expense_descriptions(self._movements)
        self._by_key: Dict[str, DescriptionGroup] = {g.key: g for g in self._groups}
        self._pending: Dict[str, str] = {}

        layout = setup_standard_rtl_dialog(
            self, title="סיווג תיאורי הוצאות", margins=(28, 20, 28, 20), spacing=10
        )
        self.setMinimumWidth(980)
        self.setMinimumHeight(640)

        title = QLabel("סיווג תיאורי הוצאות", self)
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)
        self._summary = QLabel(self)
        self._summary.setObjectName("Subtitle")
        layout.addWidget(self._summary)

        # search + filter
        bar = QHBoxLayout()
        self._search = QLineEdit(self)
        self._search.setPlaceholderText("חיפוש תיאור או קטגוריה…")
        self._search.textChanged.connect(self._apply_filter)
        self._filter = QComboBox(self)
        for key, label in _FILTERS:
            self._filter.addItem(label, key)
        self._filter.currentIndexChanged.connect(self._apply_filter)
        bar.addWidget(self._search, 3)
        bar.addWidget(self._filter, 1)
        layout.addLayout(bar)

        # table
        self._table = QTableWidget(0, 6, self)
        self._table.setHorizontalHeaderLabels(
            ["תיאור", "תנועות", "סה״כ ₪", "אחרון", "קטגוריה נוכחית", "קטגוריה חדשה"]
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_DESC, QHeaderView.ResizeMode.Stretch)
        for c in (COL_COUNT, COL_TOTAL, COL_LAST, COL_CURRENT, COL_NEW):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._update_apply_state)
        layout.addWidget(self._table, 1)

        # assign
        assign = QHBoxLayout()
        assign.addWidget(QLabel("קטגוריה לשורות המסומנות:", self))
        self._category = CategoryComboBox(self)  # collapsible category list
        for _label, name in self._choices:
            self._category.addItem(name, name)
        self._category.setMinimumWidth(260)
        assign.addWidget(self._category)
        self._apply_btn = QPushButton("החל", self)
        self._apply_btn.clicked.connect(self._assign_selected)
        assign.addWidget(self._apply_btn)
        self._undo_btn = QPushButton("בטל שינוי", self)
        self._undo_btn.setObjectName("SecondaryButton")
        self._undo_btn.clicked.connect(self._clear_selected)
        assign.addWidget(self._undo_btn)
        assign.addStretch(1)
        layout.addLayout(assign)

        # save / close
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._save_btn = QPushButton("שמור", self)
        self._save_btn.setObjectName("SaveButton")
        self._save_btn.clicked.connect(self._save)
        close_btn = QPushButton("סגור", self)
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(self._save_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self._fill_table()
        self._refresh_summary()
        self._update_apply_state()

    # ── table ──
    def _fill_table(self) -> None:
        t = self._table
        t.setSortingEnabled(False)
        t.setRowCount(len(self._groups))
        for row, g in enumerate(self._groups):
            desc = QTableWidgetItem(g.description or "(ללא תיאור)")
            desc.setData(Qt.ItemDataRole.UserRole, g.key)
            accounts = ", ".join(f"{a} ×{n}" for a, n in g.accounts.most_common())
            desc.setToolTip(f"{g.description}\nחשבונות: {accounts}")
            t.setItem(row, COL_DESC, desc)

            count = _SortItem(str(g.count))
            count.setData(Qt.ItemDataRole.UserRole, g.count)
            t.setItem(row, COL_COUNT, count)

            total = _SortItem(f"{g.total:,.0f}")
            total.setData(Qt.ItemDataRole.UserRole, g.total)
            t.setItem(row, COL_TOTAL, total)

            t.setItem(row, COL_LAST, QTableWidgetItem(g.last_date))

            current = QTableWidgetItem(self._current_label(g))
            if g.is_mixed:
                current.setToolTip(
                    "\n".join(f"{c or '(ריק)'}: {n}" for c, n in g.categories.most_common())
                )
            t.setItem(row, COL_CURRENT, current)
            t.setItem(row, COL_NEW, QTableWidgetItem(""))
        t.setSortingEnabled(True)
        t.sortItems(COL_TOTAL, Qt.SortOrder.DescendingOrder)

    def _current_label(self, g: DescriptionGroup) -> str:
        name = g.main_category or UNCLASSIFIED_NAME
        parent = self._tree.parent_of(name)
        label = f"{parent.name} › {name}" if parent is not None else name
        if g.is_mixed:
            label += f"  (+{len(g.categories) - 1} נוספות)"
        return label

    def _row_key(self, row: int) -> str:
        item = self._table.item(row, COL_DESC)
        return str(item.data(Qt.ItemDataRole.UserRole) or "") if item is not None else ""

    def _matches_filter(self, g: DescriptionGroup) -> bool:
        mode = self._filter.currentData()
        if mode == "unclassified":
            return g.is_unclassified()
        if mode == "parent_only":
            return g.is_parent_only(self._tree)
        if mode == "mixed":
            return g.is_mixed
        if mode == "pending":
            return g.key in self._pending
        return True

    def _apply_filter(self, *_a) -> None:
        text = self._search.text().strip().casefold()
        for row in range(self._table.rowCount()):
            g = self._by_key.get(self._row_key(row))
            if g is None:
                continue
            hay = f"{g.description} {' '.join(g.categories)}".casefold()
            visible = self._matches_filter(g) and (not text or text in hay)
            self._table.setRowHidden(row, not visible)

    def _selected_keys(self) -> List[str]:
        rows = {i.row() for i in self._table.selectedIndexes()}
        return [k for k in (self._row_key(r) for r in sorted(rows)) if k in self._by_key]

    def _update_apply_state(self) -> None:
        has_sel = bool(self._selected_keys())
        self._apply_btn.setEnabled(has_sel)
        self._undo_btn.setEnabled(has_sel)
        self._save_btn.setEnabled(bool(self._pending))

    def _set_new_cell(self, key: str) -> None:
        for row in range(self._table.rowCount()):
            if self._row_key(row) == key:
                item = self._table.item(row, COL_NEW)
                if item is None:
                    continue
                new = self._pending.get(key, "")
                item.setText(new)
                font = item.font()
                font.setBold(bool(new))
                item.setFont(font)
                break

    def _assign_selected(self) -> None:
        name = str(self._category.currentData() or "").strip()
        if not name:
            return
        for key in self._selected_keys():
            g = self._by_key[key]
            if set(g.categories) == {name}:
                self._pending.pop(key, None)  # already exactly that
            else:
                self._pending[key] = name
            self._set_new_cell(key)
        self._refresh_summary()
        self._update_apply_state()

    def _clear_selected(self) -> None:
        for key in self._selected_keys():
            self._pending.pop(key, None)
            self._set_new_cell(key)
        self._refresh_summary()
        self._update_apply_state()

    def _refresh_summary(self) -> None:
        n = len(self._groups)
        uncl = sum(1 for g in self._groups if g.is_unclassified())
        parent = sum(1 for g in self._groups if g.is_parent_only(self._tree))
        mixed = sum(1 for g in self._groups if g.is_mixed)
        pending_mv = sum(self._by_key[k].count for k in self._pending)
        text = (
            f"{n} תיאורים ייחודיים · {uncl} בטרם סווג · {parent} בקטגוריה ראשית בלבד"
            f" · {mixed} מעורבים"
        )
        if self._pending:
            text += f"  —  {len(self._pending)} תיאורים ({pending_mv} תנועות) ממתינים לשמירה"
        self._summary.setText(text)

    # ── save ──
    def _save(self) -> None:
        if not self._pending:
            return
        updated, changed = apply_description_categories(self._movements, self._pending)
        if not changed:
            self._pending.clear()
            self._update_apply_state()
            return
        answer = QMessageBox.question(
            self,
            "שמירת סיווג",
            f"לעדכן את הקטגוריה של {len(changed)} תנועות ב-{len(self._pending)} תיאורים?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self._service.save_movements(updated, changed_movements=changed)
        except QT_ERRORS as exc:
            QMessageBox.warning(self, "שגיאה בשמירה", f"השמירה נכשלה: {exc}")
            return
        if self._on_saved is not None:
            try:
                self._on_saved()
            except QT_ERRORS:
                pass
        # Stay open for the next batch: regroup from the saved movements.
        self._movements = list(updated)
        self._groups = group_expense_descriptions(self._movements)
        self._by_key = {g.key: g for g in self._groups}
        self._pending.clear()
        self._fill_table()
        self._apply_filter()
        self._refresh_summary()
        self._update_apply_state()
        try:
            from ..qt import QCursor, QToolTip

            QToolTip.showText(QCursor.pos(), f"עודכנו {len(changed)} תנועות")
        except QT_ERRORS:
            pass
