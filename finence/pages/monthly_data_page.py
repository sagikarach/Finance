from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QToolButton,
    QPushButton,
)
from ..data.provider import AccountsProvider
from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..models.monthly_report_service import MonthlyReportService
from ..models.monthly_report import MonthlyReport
from ..models.bank_movement import BankMovement, MovementType
from ..models.accounts import parse_iso_date
from ..utils.formatting import format_currency
from ..widgets.category_pie_chart import CategoryPieChart
from ..widgets.month_picker import MonthPickerWidget, MonthKey
from ..widgets.movements_table_card import MovementsTableCard
from ..ui.month_movements_dialog import MonthMovementsDialog
from .base_page import BasePage


class MonthlyDataPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
        monthly_service: Optional[MonthlyReportService] = None,
    ) -> None:
        self._bank_movement_provider = (
            movement_provider or JsonFileBankMovementProvider()
        )
        self._monthly_service = monthly_service or MonthlyReportService(
            self._bank_movement_provider
        )
        self._current_year: Optional[int] = None
        self._current_month: Optional[int] = None
        self._current_report: Optional[MonthlyReport] = None
        self._available_months: List[tuple[int, int]] = []
        self._month_picker: Optional[MonthPickerWidget] = None
        self._income_chart: Optional[CategoryPieChart] = None
        self._expense_chart: Optional[CategoryPieChart] = None
        self._income_card: Optional[QWidget] = None
        self._outcome_card: Optional[QWidget] = None
        self._yearly_table: Optional[MovementsTableCard] = None
        self._one_time_table: Optional[MovementsTableCard] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="סיכום חודשי",
            current_route="monthly_data",
        )

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

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        main_row_container = QWidget(self)
        main_row = QHBoxLayout(main_row_container)
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(16)

        right_container = QWidget(main_row_container)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        left_container = QWidget(main_row_container)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        self._month_picker = MonthPickerWidget(
            left_container,
            on_changed=self._on_month_changed,
        )
        month_row_container = QWidget(left_container)
        try:
            month_row_container.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass
        month_row = QHBoxLayout(month_row_container)
        month_row.setContentsMargins(0, 0, 0, 0)
        month_row.setSpacing(10)
        edit_btn = QPushButton(month_row_container)
        edit_btn.setObjectName("MonthEditButton")
        edit_btn.setText("✎ עריכת תנועות חודשיות")
        edit_btn.setToolTip("עריכת הכנסות/הוצאות לחודש")
        edit_btn.clicked.connect(self._on_edit_month_clicked)
        try:
            edit_btn.setMinimumHeight(32)
            edit_btn.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        month_row.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignLeft)
        month_row.addStretch(1)
        month_row.addWidget(self._month_picker, 0, Qt.AlignmentFlag.AlignRight)
        left_layout.addWidget(month_row_container, 0)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addStretch(1)
        self._income_card = self._create_summary_card("הכנסות", "₪0", "StatCardGreen")
        self._outcome_card = self._create_summary_card("הוצאות", "₪0", "StatCardPurple")
        cards_row.addWidget(self._income_card, 0)
        cards_row.addWidget(self._outcome_card, 0)
        cards_row.addStretch(1)
        left_layout.addLayout(cards_row, 0)

        self._yearly_table = MovementsTableCard("תנועות שנתיות", left_container)
        self._one_time_table = MovementsTableCard("תנועות חד פעמיות", left_container)
        left_layout.addWidget(self._yearly_table, 1)
        left_layout.addWidget(self._one_time_table, 1)

        chart_card_income = QWidget(right_container)
        chart_card_income.setObjectName("Sidebar")
        try:
            chart_card_income.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_income_layout = QVBoxLayout(chart_card_income)
        chart_income_layout.setContentsMargins(16, 16, 16, 16)
        chart_income_layout.setSpacing(12)
        self._income_chart = CategoryPieChart(parent=chart_card_income, is_income=True)
        chart_income_layout.addWidget(self._income_chart, 1)

        chart_card_expense = QWidget(right_container)
        chart_card_expense.setObjectName("Sidebar")
        try:
            chart_card_expense.setAttribute(
                Qt.WidgetAttribute.WA_StyledBackground, True
            )
        except Exception:
            pass
        chart_expense_layout = QVBoxLayout(chart_card_expense)
        chart_expense_layout.setContentsMargins(16, 16, 16, 16)
        chart_expense_layout.setSpacing(12)
        self._expense_chart = CategoryPieChart(
            parent=chart_card_expense, is_income=False
        )
        chart_expense_layout.addWidget(self._expense_chart, 1)

        right_layout.addWidget(chart_card_income, 1)
        right_layout.addWidget(chart_card_expense, 1)

        main_row.addWidget(right_container, 4)
        main_row.addWidget(left_container, 3)
        main_col.addWidget(main_row_container, 1)

        available_months = self._monthly_service.get_available_months()
        self._available_months = list(available_months)

        if not self._available_months:
            placeholder = QLabel("אין נתונים חודשיים להצגה", left_container)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(placeholder, 1)
            return

        if (
            self._current_year is None
            or self._current_month is None
            or (self._current_year, self._current_month) not in self._available_months
        ):
            self._current_year, self._current_month = self._available_months[0]

        if self._month_picker is not None:
            self._month_picker.set_months(
                self._available_months,
                current=(self._current_year, self._current_month),
            )

        self._refresh_report_content()

    def _on_edit_month_clicked(self) -> None:
        if self._current_year is None or self._current_month is None:
            return

        def _after_save() -> None:
            self._refresh_report_content()

        dlg = MonthMovementsDialog(
            year=self._current_year,
            month=self._current_month,
            movement_provider=self._bank_movement_provider,
            parent=None,
            on_saved=_after_save,
        )
        dlg.exec()

    def _refresh_report_content(self) -> None:
        if (
            self._income_chart is None
            or self._expense_chart is None
            or self._yearly_table is None
            or self._one_time_table is None
            or self._income_card is None
            or self._outcome_card is None
        ):
            return

        if self._current_year is not None and self._current_month is not None:
            self._current_report = self._monthly_service.get_monthly_report(
                self._current_year, self._current_month
            )
        else:
            self._current_report = None

        if self._current_report is None:
            self._yearly_table.set_movements([])
            self._one_time_table.set_movements([])
            self._income_chart.set_breakdowns([], is_income=True)
            self._expense_chart.set_breakdowns([], is_income=False)
            return

        try:
            income_val = self._income_card.findChild(QLabel, "StatValueCard")
            if income_val is not None:
                income_val.setText(
                    format_currency(
                        self._current_report.summary.total_income, use_compact=True
                    )
                )
        except Exception:
            pass
        try:
            outcome_val = self._outcome_card.findChild(QLabel, "StatValueCard")
            if outcome_val is not None:
                outcome_val.setText(
                    format_currency(
                        self._current_report.summary.total_outcome, use_compact=True
                    )
                )
        except Exception:
            pass

        self._yearly_table.set_movements(
            self._get_movements_by_type(MovementType.YEARLY)
        )
        self._one_time_table.set_movements(
            self._get_movements_by_type(MovementType.ONE_TIME)
        )
        self._income_chart.set_breakdowns(
            self._current_report.category_breakdowns, is_income=True
        )
        self._expense_chart.set_breakdowns(
            self._current_report.category_breakdowns, is_income=False
        )

    def _create_summary_card(self, title: str, value: str, card_style: str) -> QWidget:
        card = QWidget(self)
        card.setObjectName(card_style)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setAutoFillBackground(True)
        except Exception:
            pass
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        try:
            card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        try:
            card.setMinimumHeight(64)
            card.setMaximumHeight(98)
        except Exception:
            pass
        try:
            card.setMinimumWidth(210)
            card.setMaximumWidth(320)
        except Exception:
            pass

        title_label = QLabel(title, card)
        title_label.setObjectName("StatTitle")
        value_label = QLabel(value, card)
        value_label.setObjectName("StatValueCard")

        layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(value_label, 0, Qt.AlignmentFlag.AlignHCenter)

        return card

    def _get_movements_by_type(self, movement_type: MovementType) -> List[BankMovement]:
        if self._current_year is None or self._current_month is None:
            return []
        try:
            all_movements = self._bank_movement_provider.list_movements()
            filtered = [
                m
                for m in all_movements
                if m.type == movement_type
                and self._is_in_month(m.date, self._current_year, self._current_month)
            ]
            return sorted(filtered, key=lambda x: parse_iso_date(x.date), reverse=True)
        except Exception:
            return []

    def _is_in_month(self, date_str: str, year: int, month: int) -> bool:
        try:
            dt = parse_iso_date(date_str)
            return dt.year == year and dt.month == month
        except Exception:
            return False

    def _on_month_changed(self, month_key: MonthKey) -> None:
        year, month = month_key
        if year == self._current_year and month == self._current_month:
            return

        self._current_year = year
        self._current_month = month
        self._current_report = None
        self._refresh_report_content()

    def _clear_content_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout_recursive(sub_layout)
                    sub_layout.deleteLater()

        try:
            from ..qt import QApplication

            QApplication.processEvents()
        except Exception:
            pass

    def _clear_layout_recursive(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout_recursive(sub_layout)
                    sub_layout.deleteLater()

    def on_route_activated(self) -> None:
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
