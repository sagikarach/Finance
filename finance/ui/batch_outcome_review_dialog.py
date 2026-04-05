from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QScrollArea,
    QWidget,
    QProgressBar,
    Qt,
)
from .dialog_utils import (
    setup_standard_rtl_dialog,
    create_standard_buttons_row,
    wrap_hebrew_rtl,
    unwrap_rtl,
)
from .bank_movement_dialog import NewCategoryDialog
from ..models.bank_movement import BankMovement, MovementType
from ..models.classified_expense import ClassifiedExpense


class BatchOutcomeReviewDialog(QDialog):
    def __init__(
        self,
        expenses: List[ClassifiedExpense],
        categories: List[str],
        on_category_added: Optional[Callable[[str], None]] = None,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._expenses = expenses[:3]
        self._categories = list(categories)
        self._on_category_added = on_category_added
        self._results: List[Optional[BankMovement]] = [None] * len(self._expenses)

        self.setMinimumWidth(500)
        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self,
            title="סיווג הוצאות (3 הוצאות עם בטחון נמוך)",
            margins=(24, 20, 24, 20),
            spacing=12,
        )

        info_label = QLabel(
            f"נמצאו {len(self._expenses)} הוצאות עם בטחון נמוך. אנא סווג אותן:", self
        )
        info_label.setObjectName("Subtitle")
        layout.addWidget(info_label)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)

        self._category_combos: List[QComboBox] = []
        self._type_combos: List[QComboBox] = []
        self._add_category_sentinel = "__add_category__"

        for idx, classified_expense in enumerate(self._expenses):
            movement = classified_expense.movement
            suggested_cat = classified_expense.suggested_category
            suggested_type = classified_expense.suggested_type
            confidence = classified_expense.confidence
            expense_container = QWidget()
            expense_container.setObjectName("ContentPanel")
            try:
                expense_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            expense_layout = QVBoxLayout(expense_container)
            expense_layout.setSpacing(8)
            expense_layout.setContentsMargins(14, 12, 14, 12)

            header_text = (
                f"הוצאה {idx + 1}: {movement.description or 'ללא תיאור'} | "
                f"סכום: {movement.amount} | תאריך: {movement.date}"
            )
            header_label = QLabel(header_text, expense_container)
            header_label.setObjectName("ExpenseHeader")
            expense_layout.addWidget(header_label)

            confidence_row = QHBoxLayout()
            confidence_row.setSpacing(8)

            if suggested_cat:
                suggestion_text = (
                    f"הצעת AI: {suggested_cat} / "
                    f"{(suggested_type.value if suggested_type else '')}"
                )
            else:
                suggestion_text = "לא נמצאה הצעה מתאימה מה-AI"

            suggestion_label = QLabel(suggestion_text, expense_container)
            suggestion_label.setObjectName("AiSuggestionLabel")
            confidence_row.addWidget(suggestion_label)

            confidence_bar = QProgressBar(expense_container)
            confidence_bar.setMinimum(0)
            confidence_bar.setMaximum(100)
            confidence_bar.setValue(int(confidence * 100))
            confidence_bar.setFormat(f"{confidence:.0%}")
            confidence_bar.setMinimumWidth(150)
            confidence_bar.setMaximumWidth(200)

            if confidence < 0.3:
                color = "#ef4444"
                track = "#fecaca"
            elif confidence < 0.7:
                color = "#f59e0b"
                track = "#fde68a"
            else:
                color = "#22c55e"
                track = "#bbf7d0"

            confidence_bar.setStyleSheet(
                f"""
                QProgressBar {{
                    border: 1px solid {track};
                    border-radius: 4px;
                    text-align: center;
                    background: {track};
                    color: #0f172a;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QProgressBar::chunk {{
                    background-color: {color};
                    border-radius: 3px;
                }}
                """
            )

            confidence_row.addWidget(confidence_bar)
            confidence_row.addStretch()
            expense_layout.addLayout(confidence_row)

            cat_row = QHBoxLayout()
            cat_row.setSpacing(8)
            cat_label = QLabel("קטגוריה:", expense_container)
            cat_label.setMinimumWidth(80)
            category_combo = QComboBox(expense_container)

            for cat in self._categories:
                category_combo.addItem(cat, cat)
            category_combo.addItem("הוסף קטגוריה חדשה…", self._add_category_sentinel)

            try:
                category_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    category_combo.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            if suggested_cat and suggested_cat in self._categories:
                idx_cat = self._categories.index(suggested_cat)
                category_combo.setCurrentIndex(idx_cat)
            else:
                category_combo.setCurrentIndex(0 if self._categories else 0)

            def make_handler(exp_idx: int):
                def handler(combo_idx: int) -> None:
                    self._on_category_activated(exp_idx, combo_idx)

                return handler

            category_combo.activated.connect(make_handler(idx))

            self._category_combos.append(category_combo)
            cat_row.addWidget(cat_label, 0)
            cat_row.addWidget(category_combo, 1)
            expense_layout.addLayout(cat_row)

            type_row = QHBoxLayout()
            type_row.setSpacing(8)
            type_label = QLabel("סוג:", expense_container)
            type_label.setMinimumWidth(80)
            type_combo = QComboBox(expense_container)

            try:
                type_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    type_combo.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            for mt in MovementType:
                type_combo.addItem(wrap_hebrew_rtl(mt.value), mt)
            if suggested_type is not None:
                for i in range(type_combo.count()):
                    if type_combo.itemData(i) == suggested_type:
                        type_combo.setCurrentIndex(i)
                        break

            self._type_combos.append(type_combo)
            type_row.addWidget(type_label, 0)
            type_row.addWidget(type_combo, 1)
            expense_layout.addLayout(type_row)

            scroll_layout.addWidget(expense_container)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        buttons_row, ok_btn, skip_btn = create_standard_buttons_row(
            self, primary_text="שמור הכל"
        )
        skip_btn.setText("דלג על הכל")

        def on_accept() -> None:
            for idx in range(len(self._expenses)):
                cat = self._category_combos[idx].currentData()
                if cat == self._add_category_sentinel:
                    try:
                        from ..qt import QMessageBox
                        QMessageBox.warning(
                            self,
                            "קטגוריה חסרה",
                            f"שורה {idx + 1}: יש לבחור קטגוריה לפני השמירה.",
                        )
                    except Exception:
                        pass
                    return
            for idx, classified_expense in enumerate(self._expenses):
                cat = self._category_combos[idx].currentData()
                if cat == self._add_category_sentinel:
                    continue
                if isinstance(cat, str) and cat.strip():
                    type_data = self._type_combos[idx].currentData()
                    type_str = unwrap_rtl(self._type_combos[idx].currentText())

                    movement_type: Optional[MovementType] = None
                    if isinstance(type_data, MovementType):
                        movement_type = type_data
                    elif isinstance(type_str, str):
                        try:
                            movement_type = MovementType(type_str)
                        except Exception:
                            for mt in MovementType:
                                if mt.value == type_str:
                                    movement_type = mt
                                    break

                    if movement_type is not None:
                        try:
                            self._results[idx] = (
                                classified_expense.to_bank_movement_with_user_input(
                                    category=cat.strip(),
                                    movement_type=movement_type,
                                )
                            )
                        except Exception:
                            pass
            for idx, res in enumerate(self._results):
                if res is None:
                    try:
                        from ..qt import QMessageBox
                        QMessageBox.warning(
                            self,
                            "שגיאה",
                            f"שורה {idx + 1}: לא ניתן היה לשמור את הנתונים. בדוק קטגוריה וסוג.",
                        )
                    except Exception:
                        pass
                    return
            self.accept()

        def on_skip() -> None:
            self._results = [None] * len(self._expenses)
            self.reject()

        ok_btn.clicked.connect(on_accept)
        skip_btn.clicked.connect(on_skip)

        layout.addLayout(buttons_row)

    def _on_category_activated(self, expense_idx: int, combo_idx: int) -> None:
        try:
            combo = self._category_combos[expense_idx]
            data = combo.itemData(combo_idx)
        except Exception:
            return

        if data != self._add_category_sentinel:
            return

        try:
            dialog = NewCategoryDialog(self._categories, parent=self)
            if not dialog.exec():
                if self._categories:
                    combo.setCurrentIndex(0)
                return
            name = dialog.get_name().strip()
            if not name:
                if self._categories:
                    combo.setCurrentIndex(0)
                return
            if name not in self._categories:
                insert_index = combo.count() - 1
                self._categories.append(name)
                combo.insertItem(insert_index, name, name)
                if self._on_category_added is not None:
                    try:
                        self._on_category_added(name)
                    except Exception:
                        pass
                combo.setCurrentIndex(insert_index)
        except Exception:
            return

    def get_results(self) -> List[Optional[BankMovement]]:
        return self._results
