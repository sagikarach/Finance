from __future__ import annotations

from datetime import date as _date
from typing import Callable, List, Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QDateEdit,
    Qt,
    QDate,
)
from .dialog_utils import (
    setup_standard_rtl_dialog,
    create_standard_buttons_row,
    wrap_hebrew_rtl,
    apply_rtl_alignment,
)
from ..models.accounts import BudgetAccount, MoneyAccount
from ..models.bank_movement import BankMovement, MovementType


class NewCategoryDialog(QDialog):
    def __init__(
        self,
        existing_names: List[str],
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._existing = existing_names
        self._name: str = ""

        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self, title="קטגוריה חדשה", margins=(32, 24, 32, 24), spacing=12
        )

        row = QHBoxLayout()
        row.setSpacing(8)
        label = QLabel("שם קטגוריה:", self)
        label.setMinimumWidth(90)
        self._edit = QLineEdit(self)
        row.addWidget(label, 0)
        row.addWidget(self._edit, 1)

        self._error_label = QLabel("", self)
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.hide()

        buttons_row, primary_btn, cancel_btn = create_standard_buttons_row(
            self, primary_text="הוסף"
        )

        layout.addLayout(row)
        layout.addWidget(self._error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            name = self._edit.text().strip()
            if not name:
                self._show_error("יש להזין שם קטגוריה")
                return
            if name in self._existing:
                self._show_error("הקטגוריה כבר קיימת")
                return
            self._name = name
            self.accept()

        primary_btn.clicked.connect(on_accept)
        cancel_btn.clicked.connect(self.reject)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.show()

    def get_name(self) -> str:
        return self._name


class BankMovementDialog(QDialog):
    def __init__(
        self,
        accounts: List[MoneyAccount],
        categories: List[str],
        is_income: bool,
        parent: Optional[QDialog] = None,
        on_category_added: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._accounts = accounts
        self._categories = list(categories)
        self._on_category_added = on_category_added
        self._is_income = is_income
        self._movement: Optional[BankMovement] = None
        self._last_category_index = 0

        title = "הוספת הכנסה" if is_income else "הוספת הוצאה"
        layout: QVBoxLayout = setup_standard_rtl_dialog(
            self, title=title, margins=(32, 24, 32, 24), spacing=12
        )

        amount_row = QHBoxLayout()
        amount_row.setSpacing(8)
        amount_label = QLabel("סכום:", self)
        amount_label.setMinimumWidth(80)
        self._amount_edit = QLineEdit(self)
        try:
            self._amount_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._amount_edit.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            self._amount_edit.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            try:
                self._amount_edit.setAlignment(Qt.AlignRight)
            except Exception:
                pass
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(self._amount_edit, 1)

        date_row = QHBoxLayout()
        date_row.setSpacing(8)
        date_label = QLabel("תאריך:", self)
        date_label.setMinimumWidth(80)
        self._date_edit = QDateEdit(self)
        try:
            self._date_edit.setCalendarPopup(True)
        except Exception:
            pass
        try:
            today = _date.today()
            self._date_edit.setDate(QDate(today.year, today.month, today.day))
        except Exception:
            pass
        date_row.addWidget(date_label, 0)
        date_row.addWidget(self._date_edit, 1)

        account_row = QHBoxLayout()
        account_row.setSpacing(8)
        account_label = QLabel("חשבון:", self)
        account_label.setMinimumWidth(80)
        self._account_combo = QComboBox(self)
        try:
            self._account_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._account_combo.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            self._account_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except Exception:
            pass
        for acc in self._accounts:
            self._account_combo.addItem(acc.name)
        apply_rtl_alignment(self._account_combo)
        account_row.addWidget(account_label, 0)
        account_row.addWidget(self._account_combo, 1)

        category_row = QHBoxLayout()
        category_row.setSpacing(8)
        category_label = QLabel("קטגוריה:", self)
        category_label.setMinimumWidth(80)
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
        try:
            self._category_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except Exception:
            pass
        apply_rtl_alignment(self._category_combo)
        try:
            self._category_combo.activated.connect(self._on_category_activated)
        except Exception:
            pass
        category_row.addWidget(category_label, 0)
        category_row.addWidget(self._category_combo, 1)

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
        try:
            self._type_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except Exception:
            pass
        for mt in MovementType:
            self._type_combo.addItem(wrap_hebrew_rtl(mt.value), mt)
        apply_rtl_alignment(self._type_combo)
        type_row.addWidget(type_label, 0)
        type_row.addWidget(self._type_combo, 1)

        desc_row = QHBoxLayout()
        desc_row.setSpacing(8)
        desc_label = QLabel("תיאור:", self)
        desc_label.setMinimumWidth(80)
        self._description_edit = QLineEdit(self)
        try:
            self._description_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self._description_edit.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            self._description_edit.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            try:
                self._description_edit.setAlignment(Qt.AlignRight)
            except Exception:
                pass
        try:
            self._description_edit.setStyleSheet("text-align: right;")
        except Exception:
            pass
        desc_row.addWidget(desc_label, 0)
        desc_row.addWidget(self._description_edit, 1)

        self._error_label = QLabel("", self)
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.setMinimumHeight(0)
        self._error_label.setMaximumHeight(60)
        self._error_label.hide()

        buttons_row, primary_btn, cancel_btn = create_standard_buttons_row(
            self, primary_text="הוסף"
        )

        layout.addLayout(amount_row)
        layout.addLayout(date_row)
        layout.addLayout(account_row)
        layout.addLayout(category_row)
        layout.addLayout(type_row)
        layout.addLayout(desc_row)
        layout.addWidget(self._error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            text = self._amount_edit.text().strip()
            if not text:
                self._show_error("יש להזין סכום")
                return
            try:
                amount_value = float(text.replace(",", ""))
            except Exception:
                self._show_error("הסכום חייב להיות מספר")
                return
            if amount_value <= 0:
                self._show_error("הסכום חייב להיות גדול מ-0")
                return

            if self._account_combo.count() == 0:
                self._show_error("אין חשבון זמין")
                return

            account_name = self._account_combo.currentText().strip()
            if not account_name:
                self._show_error("יש לבחור חשבון")
                return

            selected_acc: Optional[MoneyAccount] = None
            try:
                for a in self._accounts:
                    if a.name == account_name:
                        selected_acc = a
                        break
            except Exception:
                selected_acc = None

            if isinstance(selected_acc, BudgetAccount):
                if self._is_income:
                    self._show_error("לא ניתן להוסיף הכנסה לחשבון תקציב")
                    return

            signed_amount = amount_value if self._is_income else -amount_value

            qdate = self._date_edit.date()
            try:
                date_str = qdate.toString("yyyy-MM-dd")
            except Exception:
                date_str = ""

            category = self._category_combo.currentText().strip()
            if self._category_combo.currentData() == self._add_category_sentinel:
                self._show_error("יש לבחור קטגוריה")
                return
            type_data = self._type_combo.currentData()
            mtype: MovementType
            if isinstance(type_data, MovementType):
                mtype = type_data
            else:
                try:
                    from .dialog_utils import unwrap_rtl

                    type_text = unwrap_rtl(self._type_combo.currentText())
                    mtype = MovementType(type_text)
                except Exception:
                    mtype = MovementType.ONE_TIME

            description = self._description_edit.text().strip() or None

            self._movement = BankMovement(
                amount=signed_amount,
                date=date_str,
                account_name=account_name,
                category=category,
                type=mtype,
                description=description,
            )
            self.accept()

        primary_btn.clicked.connect(on_accept)
        cancel_btn.clicked.connect(self.reject)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setMinimumHeight(40)
        self._error_label.show()
        try:
            self.adjustSize()
        except Exception:
            pass

    def get_movement(self) -> Optional[BankMovement]:
        return self._movement

    def _on_category_activated(self, index: int) -> None:
        try:
            data = self._category_combo.itemData(index)
            if data == self._add_category_sentinel:
                dialog = NewCategoryDialog(self._categories, parent=self)
                result = dialog.exec()
                if not result:
                    self._category_combo.setCurrentIndex(self._last_category_index)
                    return
                name = dialog.get_name().strip()
                if not name:
                    self._category_combo.setCurrentIndex(self._last_category_index)
                    return
                if name not in self._categories:
                    insert_index = self._category_combo.count() - 1
                    self._categories.append(name)
                    self._category_combo.insertItem(insert_index, name, name)
                    apply_rtl_alignment(self._category_combo)
                    if self._on_category_added is not None:
                        try:
                            self._on_category_added(name)
                        except Exception:
                            pass
                    self._category_combo.setCurrentIndex(insert_index)
                    self._last_category_index = insert_index
            else:
                self._last_category_index = index
        except Exception:
            pass
