from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    Qt,
)
from .dialog_utils import (
    setup_standard_rtl_dialog,
    create_standard_buttons_row,
    wrap_hebrew_rtl,
)
from .bank_movement_dialog import NewCategoryDialog
from ..models.bank_movement import BankMovement, MovementType


class OutcomeReviewDialog(QDialog):
    """
    Dialog that lets the user manually classify an outcome movement when the
    AI/Ollama confidence is low.
    """

    def __init__(
        self,
        movement: BankMovement,
        suggested_category: Optional[str],
        suggested_type: Optional[MovementType],
        confidence: float,
        categories: List[str],
        on_category_added: Optional[Callable[[str], None]] = None,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._movement = movement
        self._categories = list(categories)
        self._on_category_added = on_category_added
        self._selected_category: Optional[str] = None
        self._selected_type: MovementType = suggested_type or MovementType.ONE_TIME

        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self, title="סיווג הוצאה", margins=(32, 24, 32, 24), spacing=12
        )

        # Info row: description + amount + date
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        desc_text = movement.description or ""
        desc_label = QLabel(f"תיאור: {desc_text}", self)
        amount_label = QLabel(f"סכום: {movement.amount}", self)
        date_label = QLabel(f"תאריך: {movement.date}", self)

        info_col.addWidget(desc_label)
        info_col.addWidget(amount_label)
        info_col.addWidget(date_label)

        layout.addLayout(info_col)

        # AI suggestion row (optional)
        if suggested_category:
            suggestion = (
                f"הצעת AI: {suggested_category} / "
                f"{(suggested_type.value if suggested_type else '')} "
                f"(בטחון {confidence:.0%})"
            )
        else:
            suggestion = "לא נמצאה הצעה מתאימה מה-AI"
        suggestion_label = QLabel(suggestion, self)
        layout.addWidget(suggestion_label)

        # Category row
        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        cat_label = QLabel("קטגוריה:", self)
        cat_label.setMinimumWidth(80)
        self._category_combo = QComboBox(self)
        # Existing categories
        for cat in self._categories:
            self._category_combo.addItem(cat, cat)
        # "Add new category" sentinel
        self._add_category_sentinel = "__add_category__"
        self._category_combo.addItem("הוסף קטגוריה חדשה…", self._add_category_sentinel)

        try:
            self._category_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._category_combo.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        try:
            self._category_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except Exception:
            pass

        # Pre-select suggested category if present in the list
        if suggested_category and suggested_category in self._categories:
            idx = self._categories.index(suggested_category)
            self._category_combo.setCurrentIndex(idx)
        else:
            self._category_combo.setCurrentIndex(0 if self._categories else 0)

        self._category_combo.activated.connect(self._on_category_activated)  # type: ignore[arg-type]

        cat_row.addWidget(cat_label, 0)
        cat_row.addWidget(self._category_combo, 1)
        layout.addLayout(cat_row)

        # Type row
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_label = QLabel("סוג:", self)
        type_label.setMinimumWidth(80)
        self._type_combo = QComboBox(self)
        try:
            self._type_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._type_combo.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        try:
            self._type_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except Exception:
            pass

        for mt in MovementType:
            self._type_combo.addItem(wrap_hebrew_rtl(mt.value), mt)
        # Pre-select suggested type if provided
        if suggested_type is not None:
            for i in range(self._type_combo.count()):
                if self._type_combo.itemData(i) == suggested_type:
                    self._type_combo.setCurrentIndex(i)
                    break

        type_row.addWidget(type_label, 0)
        type_row.addWidget(self._type_combo, 1)
        layout.addLayout(type_row)

        # Buttons
        buttons_row, ok_btn, skip_btn = create_standard_buttons_row(
            self, primary_text="שמור"
        )
        skip_btn.setText("דלג")

        def on_accept() -> None:
            cat = self._category_combo.currentData()
            if cat == self._add_category_sentinel:
                # User clicked "add new" but didn't actually add; ignore.
                return
            if isinstance(cat, str):
                self._selected_category = cat.strip()
            type_data = self._type_combo.currentData()
            if isinstance(type_data, MovementType):
                self._selected_type = type_data
            self.accept()

        def on_skip() -> None:
            # Leave movement uncategorized for now.
            self._selected_category = None
            self.reject()

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        skip_btn.clicked.connect(on_skip)  # type: ignore[arg-type]

        layout.addLayout(buttons_row)

    def _on_category_activated(self, index: int) -> None:
        try:
            data = self._category_combo.itemData(index)
        except Exception:
            return

        if data != self._add_category_sentinel:
            return

        # Add new category via the existing dialog and callback.
        try:
            dialog = NewCategoryDialog(self._categories, parent=self)
            if not dialog.exec():
                # Revert to previous selection
                if self._categories:
                    self._category_combo.setCurrentIndex(0)
                return
            name = dialog.get_name().strip()
            if not name:
                if self._categories:
                    self._category_combo.setCurrentIndex(0)
                return
            if name not in self._categories:
                insert_index = self._category_combo.count() - 1
                self._categories.append(name)
                self._category_combo.insertItem(insert_index, name, name)
                if self._on_category_added is not None:
                    try:
                        self._on_category_added(name)
                    except Exception:
                        pass
                self._category_combo.setCurrentIndex(insert_index)
        except Exception:
            return

    def get_result(self) -> Optional[BankMovement]:
        """
        Return a movement with the user-selected category/type, or None if the
        user skipped classification.
        """
        if not self._selected_category:
            return None

        try:
            return BankMovement(
                amount=self._movement.amount,
                date=self._movement.date,
                account_name=self._movement.account_name,
                category=self._selected_category,
                type=self._selected_type,
                description=self._movement.description,
            )
        except Exception:
            return None
