from __future__ import annotations

from datetime import date as _date
from typing import Any, Callable, List, Optional

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
    QTimer,
)
from .dialog_utils import (
    setup_standard_rtl_dialog,
    create_standard_buttons_row,
    wrap_hebrew_rtl,
    apply_rtl_alignment,
    setup_calendar_popup,
)
from ..models.accounts import BudgetAccount, MoneyAccount
from ..models.bank_movement import BankMovement, MovementType
from ..widgets.category_combo import CategoryComboBox
from ..utils.safe import QT_ERRORS


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
        suggest_category: Optional[Callable[[str, float], Any]] = None,
    ) -> None:
        super().__init__(parent)
        self._suggest_category = suggest_category
        # True once the user picks a category themselves — a suggestion never
        # overrides that choice.
        self._category_user_set = False
        self._type_user_set = False
        self._suggested_index: Optional[int] = None  # index set by a suggestion
        self._suggested_type = False  # type combo set by a suggestion
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
        except QT_ERRORS:
            try:
                self._amount_edit.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        try:
            self._amount_edit.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except QT_ERRORS:
            try:
                self._amount_edit.setAlignment(Qt.AlignRight)
            except QT_ERRORS:
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
            setup_calendar_popup(self._date_edit)
        except QT_ERRORS:
            pass
        try:
            today = _date.today()
            self._date_edit.setDate(QDate(today.year, today.month, today.day))
        except QT_ERRORS:
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
        except QT_ERRORS:
            try:
                self._account_combo.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        try:
            self._account_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except QT_ERRORS:
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
        # Collapsible list: subcategories appear only after pressing a
        # category's arrow (expense categories; income stays a flat list).
        self._category_combo = CategoryComboBox(self, hierarchical=not is_income)
        self._fill_categories()
        self._add_category_sentinel = "__add_category__"
        self._category_combo.addItem("הוסף קטגוריה חדשה…", self._add_category_sentinel)
        self._category_combo.setCurrentIndex(self._default_category_index)
        self._last_category_index = self._default_category_index
        try:
            self._category_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            try:
                self._category_combo.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        try:
            self._category_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except QT_ERRORS:
            pass
        apply_rtl_alignment(self._category_combo)
        try:
            self._category_combo.activated.connect(self._on_category_activated)
        except QT_ERRORS:
            pass
        category_row.addWidget(category_label, 0)
        category_row.addWidget(self._category_combo, 1)
        self._suggestion_label = QLabel("", self)
        self._suggestion_label.setObjectName("Subtitle")
        self._suggestion_label.setWordWrap(True)
        self._suggestion_label.hide()

        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_label = QLabel("סוג:", self)
        type_label.setMinimumWidth(80)
        self._type_combo = QComboBox(self)
        try:
            self._type_combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            try:
                self._type_combo.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        try:
            self._type_combo.setStyleSheet(
                "QComboBox { text-align: right; } "
                "QComboBox QAbstractItemView::item { text-align: right; }"
            )
        except QT_ERRORS:
            pass
        for mt in MovementType:
            self._type_combo.addItem(wrap_hebrew_rtl(mt.value), mt)
        apply_rtl_alignment(self._type_combo)
        self._default_type_index = self._type_combo.currentIndex()
        try:
            self._type_combo.activated.connect(self._on_type_activated)
        except QT_ERRORS:
            pass
        type_row.addWidget(type_label, 0)
        type_row.addWidget(self._type_combo, 1)

        desc_row = QHBoxLayout()
        desc_row.setSpacing(8)
        desc_label = QLabel("תיאור:", self)
        desc_label.setMinimumWidth(80)
        self._description_edit = QLineEdit(self)
        try:
            self._description_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            try:
                self._description_edit.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        try:
            self._description_edit.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except QT_ERRORS:
            try:
                self._description_edit.setAlignment(Qt.AlignRight)
            except QT_ERRORS:
                pass
        try:
            self._description_edit.setStyleSheet("text-align: right;")
        except QT_ERRORS:
            pass
        desc_row.addWidget(desc_label, 0)
        desc_row.addWidget(self._description_edit, 1)
        self._description_edit.setPlaceholderText(
            "לדוגמה: משכורת" if is_income else "לדוגמה: סופרפארם לוד"
        )
        QTimer.singleShot(0, self._description_edit.setFocus)

        self._error_label = QLabel("", self)
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.setMinimumHeight(0)
        self._error_label.setMaximumHeight(60)
        self._error_label.hide()

        buttons_row, primary_btn, cancel_btn = create_standard_buttons_row(
            self, primary_text="הוסף"
        )

        # What was bought comes first: the category and type are suggested
        # from it (and the amount), then the remaining details.
        layout.addLayout(desc_row)
        layout.addLayout(amount_row)
        layout.addLayout(category_row)
        layout.addWidget(self._suggestion_label)
        layout.addLayout(type_row)
        layout.addLayout(date_row)
        layout.addLayout(account_row)
        layout.addWidget(self._error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            text = self._amount_edit.text().strip()
            if not text:
                self._show_error("יש להזין סכום")
                return
            try:
                amount_value = float(text.replace(",", ""))
            except QT_ERRORS:
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
            except QT_ERRORS:
                selected_acc = None

            if isinstance(selected_acc, BudgetAccount):
                if self._is_income:
                    self._show_error("לא ניתן להוסיף הכנסה לחשבון תקציב")
                    return

            signed_amount = amount_value if self._is_income else -amount_value

            qdate = self._date_edit.date()
            try:
                date_str = qdate.toString("yyyy-MM-dd")
            except QT_ERRORS:
                date_str = ""

            data = self._category_combo.currentData()
            category = (
                str(data).strip()
                if isinstance(data, str) and data != self._add_category_sentinel
                else self._category_combo.currentText().strip()
            )
            if data == self._add_category_sentinel:
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
                except QT_ERRORS:
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

        if self._suggest_category is not None:
            # Debounced: classify once typing pauses, not on every keystroke.
            self._suggest_timer = QTimer(self)
            self._suggest_timer.setSingleShot(True)
            self._suggest_timer.setInterval(300)
            self._suggest_timer.timeout.connect(self._apply_suggestion)
            self._description_edit.textChanged.connect(self._schedule_suggestion)
            self._amount_edit.textChanged.connect(self._schedule_suggestion)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        self._error_label.setMinimumHeight(40)
        self._error_label.show()
        try:
            self.adjustSize()
        except QT_ERRORS:
            pass

    def get_movement(self) -> Optional[BankMovement]:
        return self._movement

    def _fill_categories(self) -> None:
        """Expense categories in hierarchy order (the popup groups them under
        collapsible parents); default "טרם סווג" so an expense nobody
        categorized is never silently filed under the first category."""
        from ..models.category_tree import UNCLASSIFIED_NAME, active_tree
        from ..models.description_categories import category_choices

        tree = active_tree() if not self._is_income else None
        choices = category_choices(tree, self._categories) if tree else []
        seen = {name for _label, name in choices}
        for cat in self._categories:  # anything else the list offers
            if cat not in seen and not (tree and cat in tree.legacy_aliases):
                choices.append((cat, cat))
                seen.add(cat)
        for _label, name in choices:
            # Plain names: the popup shows the hierarchy itself.
            self._category_combo.addItem(name, name)
        idx = self._category_combo.findData(UNCLASSIFIED_NAME) if tree else -1
        self._default_category_index = max(idx, 0)

    def _schedule_suggestion(self, *_args) -> None:
        if not (self._category_user_set and self._type_user_set):
            self._suggest_timer.start()

    def _apply_suggestion(self) -> None:
        """Fill in the category (and type) learned from past expenses with the
        same description. Never overrides a field the user set themselves."""
        if self._suggest_category is None:
            return
        description = self._description_edit.text().strip()
        try:
            amount = float(self._amount_edit.text().strip().replace(",", "") or 0)
        except ValueError:
            amount = 0.0
        found = None
        if description:
            try:
                found = self._suggest_category(description, amount)
            except QT_ERRORS:
                found = None
        if isinstance(found, tuple):
            suggestion, mtype = found
        else:
            suggestion, mtype = found, None
        index = self._category_combo.findData(suggestion) if suggestion else -1
        if index < 0:
            self._suggestion_label.hide()
            if self._suggested_index is not None and not self._category_user_set:
                # The earlier suggestion no longer applies: back to the default.
                self._category_combo.setCurrentIndex(self._default_category_index)
                self._last_category_index = self._default_category_index
            if self._suggested_type and not self._type_user_set:
                self._type_combo.setCurrentIndex(self._default_type_index)
            self._suggested_index = None
            self._suggested_type = False
            return
        parts = []
        if not self._category_user_set:
            self._category_combo.setCurrentIndex(index)
            self._last_category_index = index
            self._suggested_index = index
            parts.append(str(suggestion))
        if mtype is not None and not self._type_user_set:
            t_index = self._type_combo.findData(mtype)
            if t_index >= 0:
                self._type_combo.setCurrentIndex(t_index)
                self._suggested_type = True
                parts.append(str(getattr(mtype, "value", mtype)))
        if parts:
            # The values are already in the fields; just say where they came from.
            self._suggestion_label.setText("✓ מולא לפי הוצאות קודמות (אפשר לשנות)")
            self._suggestion_label.setToolTip(" · ".join(parts))
            self._suggestion_label.show()

    def _on_type_activated(self, _index: int) -> None:
        self._type_user_set = True
        self._suggested_type = False

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
                        except QT_ERRORS:
                            pass
                    self._category_combo.setCurrentIndex(insert_index)
                    self._last_category_index = insert_index
            else:
                self._last_category_index = index
            self._category_user_set = True
            self._suggestion_label.hide()
        except QT_ERRORS:
            pass
