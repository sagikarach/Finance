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

        self.setMinimumWidth(420)
        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self, title="סיווג הוצאה", margins=(24, 20, 24, 20), spacing=12
        )

        # Transaction info card
        info_card = QWidget(self)
        info_card.setObjectName("ContentPanel")
        try:
            from ..qt import Qt as _Qt
            info_card.setAttribute(_Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(14, 12, 14, 12)
        info_card_layout.setSpacing(4)

        desc_text = movement.description or ""
        desc_label = QLabel(f"תיאור: {desc_text}", info_card)
        desc_label.setObjectName("ExpenseHeader")
        desc_label.setWordWrap(True)
        amount_label = QLabel(f"סכום: {movement.amount}", info_card)
        amount_label.setObjectName("Subtitle")
        date_label = QLabel(f"תאריך: {movement.date}", info_card)
        date_label.setObjectName("Subtitle")

        info_card_layout.addWidget(desc_label)
        info_card_layout.addWidget(amount_label)
        info_card_layout.addWidget(date_label)
        layout.addWidget(info_card)

        if suggested_category:
            suggestion = (
                f"הצעת AI: {suggested_category} / "
                f"{(suggested_type.value if suggested_type else '')} "
                f"(בטחון {confidence:.0%})"
            )
        else:
            suggestion = "לא נמצאה הצעה מתאימה מה-AI"
        suggestion_label = QLabel(suggestion, self)
        suggestion_label.setObjectName("AiSuggestionLabel")
        layout.addWidget(suggestion_label)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(8)
        cat_label = QLabel("קטגוריה:", self)
        cat_label.setMinimumWidth(80)
        self._category_combo = QComboBox(self)
        for cat in self._categories:
            self._category_combo.addItem(cat, cat)
        self._add_category_sentinel = "__add_category__"
        self._category_combo.addItem("הוסף קטגוריה חדשה…", self._add_category_sentinel)

        try:
            self._category_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._category_combo.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        if suggested_category and suggested_category in self._categories:
            idx = self._categories.index(suggested_category)
            self._category_combo.setCurrentIndex(idx)
        else:
            self._category_combo.setCurrentIndex(0 if self._categories else 0)

        self._category_combo.activated.connect(self._on_category_activated)

        cat_row.addWidget(cat_label, 0)
        cat_row.addWidget(self._category_combo, 1)
        layout.addLayout(cat_row)

        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_label = QLabel("סוג:", self)
        type_label.setMinimumWidth(80)
        self._type_combo = QComboBox(self)
        try:
            self._type_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._type_combo.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        for mt in MovementType:
            self._type_combo.addItem(wrap_hebrew_rtl(mt.value), mt)
        if suggested_type is not None:
            for i in range(self._type_combo.count()):
                if self._type_combo.itemData(i) == suggested_type:
                    self._type_combo.setCurrentIndex(i)
                    break

        type_row.addWidget(type_label, 0)
        type_row.addWidget(self._type_combo, 1)
        layout.addLayout(type_row)

        buttons_row, ok_btn, skip_btn = create_standard_buttons_row(
            self, primary_text="שמור"
        )
        skip_btn.setText("דלג")

        def on_accept() -> None:
            cat = self._category_combo.currentData()
            if cat == self._add_category_sentinel:
                return
            if not isinstance(cat, str) or not cat.strip():
                return
            self._selected_category = cat.strip()
            type_data = self._type_combo.currentData()
            if isinstance(type_data, MovementType):
                self._selected_type = type_data
            self.accept()

        def on_skip() -> None:
            self._selected_category = None
            self.reject()

        ok_btn.clicked.connect(on_accept)
        skip_btn.clicked.connect(on_skip)

        layout.addLayout(buttons_row)

    def _on_category_activated(self, index: int) -> None:
        try:
            data = self._category_combo.itemData(index)
        except Exception:
            return

        if data != self._add_category_sentinel:
            return

        try:
            dialog = NewCategoryDialog(self._categories, parent=self)
            if not dialog.exec():
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
