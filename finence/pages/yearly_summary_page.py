from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.accounts import parse_iso_date
from ..models.bank_movement import BankMovement, MovementType
from ..models.yearly_report_service import YearlyReportService
from ..qt import (
    QLabel,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
)
from ..utils.formatting import format_currency
from ..widgets.category_pie_chart import CategoryPieChart
from ..widgets.collapsible_card import CollapsibleCard
from ..widgets.movements_table_card import MovementsTableCard
from ..widgets.year_picker import YearPickerWidget
from ..widgets.yearly_months_table_card import YearlyMonthsTableCard
from .base_page import BasePage


class YearlySummaryPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
        yearly_service: Optional[YearlyReportService] = None,
        chart_types: Optional[Set[MovementType]] = None,
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._yearly_service = yearly_service or YearlyReportService(
            self._movement_provider
        )
        self._chart_types: Set[MovementType] = chart_types or {MovementType.MONTHLY}

        self._current_year: Optional[int] = None
        self._available_years: List[int] = []

        self._year_picker: Optional[YearPickerWidget] = None
        self._income_chart: Optional[CategoryPieChart] = None
        self._expense_chart: Optional[CategoryPieChart] = None
        self._income_card: Optional[QWidget] = None
        self._outcome_card: Optional[QWidget] = None
        self._yearly_table: Optional[MovementsTableCard] = None
        self._one_time_table: Optional[MovementsTableCard] = None
        self._months_card: Optional[CollapsibleCard] = None
        self._months_table: Optional[YearlyMonthsTableCard] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="סיכום שנתי",
            current_route="yearly_data",
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

        self._year_picker = YearPickerWidget(
            left_container, on_changed=self._on_year_changed
        )
        left_layout.addWidget(self._year_picker, 0, Qt.AlignmentFlag.AlignHCenter)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addStretch(1)
        self._income_card = self._create_summary_card("הכנסות", "₪0", "StatCardGreen")
        self._outcome_card = self._create_summary_card("הוצאות", "₪0", "StatCardPurple")
        cards_row.addWidget(self._income_card, 0)
        cards_row.addWidget(self._outcome_card, 0)
        cards_row.addStretch(1)
        left_layout.addLayout(cards_row, 0)

        self._months_card = CollapsibleCard(
            "סיכום לפי חודשים", left_container, expanded=False
        )
        self._months_table = YearlyMonthsTableCard(self._months_card)
        self._months_card.set_content(self._months_table)
        left_layout.addWidget(self._months_card, 0)

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

        self._available_years = list(self._yearly_service.get_available_years())
        if not self._available_years:
            placeholder = QLabel("אין נתונים שנתיים להצגה", left_container)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            left_layout.addWidget(placeholder, 1)
            return

        if (
            self._current_year is None
            or self._current_year not in self._available_years
        ):
            self._current_year = self._available_years[0]

        if self._year_picker is not None:
            self._year_picker.set_years(
                self._available_years, current=self._current_year
            )

        self._refresh_report()

    def _refresh_report(self) -> None:
        if (
            self._income_chart is None
            or self._expense_chart is None
            or self._yearly_table is None
            or self._one_time_table is None
            or self._income_card is None
            or self._outcome_card is None
            or self._current_year is None
            or self._months_table is None
        ):
            return

        report = self._yearly_service.get_yearly_report(
            self._current_year,
            movement_types=set(self._chart_types),
        )

        if report is None:
            self._yearly_table.set_movements([])
            self._one_time_table.set_movements([])
            self._income_chart.set_breakdowns([], is_income=True)
            self._expense_chart.set_breakdowns([], is_income=False)
            return

        try:
            income_val = self._income_card.findChild(QLabel, "StatValueCard")
            if income_val is not None:
                income_val.setText(
                    format_currency(report.summary.total_income, use_compact=True)
                )
        except Exception:
            pass
        try:
            outcome_val = self._outcome_card.findChild(QLabel, "StatValueCard")
            if outcome_val is not None:
                outcome_val.setText(
                    format_currency(report.summary.total_outcome, use_compact=True)
                )
        except Exception:
            pass

        self._income_chart.set_breakdowns(report.category_breakdowns, is_income=True)
        self._expense_chart.set_breakdowns(report.category_breakdowns, is_income=False)

        self._yearly_table.set_movements(
            self._get_movements_by_year_and_type(
                self._current_year, MovementType.YEARLY
            )
        )
        self._one_time_table.set_movements(
            self._get_movements_by_year_and_type(
                self._current_year, MovementType.ONE_TIME
            )
        )
        self._months_table.set_rows(
            self._yearly_service.get_month_type_summaries(self._current_year)
        )

    def _get_movements_by_year_and_type(
        self, year: int, movement_type: MovementType
    ) -> List[BankMovement]:
        try:
            all_movements = self._movement_provider.list_movements()
        except Exception:
            return []

        items: List[BankMovement] = []
        for m in all_movements:
            try:
                if m.type != movement_type:
                    continue
                if parse_iso_date(m.date).year != year:
                    continue
                items.append(m)
            except Exception:
                continue

        return sorted(items, key=lambda x: parse_iso_date(x.date), reverse=True)

    def _on_year_changed(self, year: int) -> None:
        if year == self._current_year:
            return
        self._current_year = year
        self._refresh_report()

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

    def on_route_activated(self) -> None:
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
