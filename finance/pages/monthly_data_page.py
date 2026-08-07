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
        monthly_service: Optional[MonthlyReportService] = None,
    ) -> None:
        self._monthly_service = monthly_service or MonthlyReportService(
            JsonFileBankMovementProvider()
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
        self._net_card: Optional[QWidget] = None
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

    def _chart_panel(self, title: str, chart: QWidget) -> QWidget:
        return self._content_panel(title, chart)

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        # ── month bar: picker (right) + edit (left) ──
        self._month_picker = MonthPickerWidget(
            self, on_changed=self._on_month_changed
        )
        month_bar = QWidget(self)
        try:
            month_bar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass
        month_row = QHBoxLayout(month_bar)
        month_row.setContentsMargins(0, 0, 0, 0)
        month_row.setSpacing(10)
        edit_btn = QPushButton(month_bar)
        edit_btn.setObjectName("MoveButton")
        edit_btn.setText("✎ עריכת תנועות חודשיות")
        edit_btn.setToolTip("עריכת הכנסות/הוצאות לחודש")
        edit_btn.clicked.connect(self._on_edit_month_clicked)
        try:
            edit_btn.setMinimumHeight(36)
            edit_btn.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        month_row.addWidget(edit_btn, 0, Qt.AlignmentFlag.AlignLeft)
        month_row.addStretch(1)
        month_row.addWidget(self._month_picker, 0, Qt.AlignmentFlag.AlignRight)
        main_col.addWidget(month_bar, 0)

        # ── three cards: income / expense / net ──
        self._income_card = self._create_summary_card(
            "הכנסות", "₪0", "MonthIncomeCard"
        )
        self._outcome_card = self._create_summary_card(
            "הוצאות", "₪0", "MonthExpenseCard"
        )
        self._net_card = self._create_summary_card(
            "יתרה חודשית", "₪0", "MonthNetCard"
        )
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(self._income_card, 1)
        cards_row.addWidget(self._outcome_card, 1)
        cards_row.addWidget(self._net_card, 1)
        main_col.addLayout(cards_row, 0)

        # ── two category donuts ──
        self._income_chart = CategoryPieChart(parent=self, is_income=True)
        self._expense_chart = CategoryPieChart(parent=self, is_income=False)
        donuts_row = QHBoxLayout()
        donuts_row.setSpacing(16)
        donuts_row.addWidget(
            self._chart_panel("פילוח הכנסות", self._income_chart), 1
        )
        donuts_row.addWidget(
            self._chart_panel("פילוח הוצאות", self._expense_chart), 1
        )
        main_col.addLayout(donuts_row, 3)

        # ── special movements: yearly + one-time ──
        self._yearly_table = MovementsTableCard("תנועות שנתיות", self)
        self._one_time_table = MovementsTableCard("תנועות חד פעמיות", self)
        special_row = QHBoxLayout()
        special_row.setSpacing(16)
        special_row.addWidget(self._yearly_table, 1)
        special_row.addWidget(self._one_time_table, 1)
        main_col.addLayout(special_row, 2)

        available_months = self._monthly_service.get_available_months()
        self._available_months = list(available_months)

        if not self._available_months:
            placeholder = QLabel("אין נתונים חודשיים להצגה", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
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
            movement_service=self._bank_movement_service,
            parent=None,
            on_saved=_after_save,
            on_delete_movement=self._delete_movement_and_refresh,
        )
        dlg.exec()

    def _delete_movement_and_refresh(self, movement_id: str) -> None:
        movement_id = str(movement_id or "").strip()
        if not movement_id:
            return

        try:
            svc = self._bank_movement_service
            if svc is None:
                return
            self._accounts = svc.delete_movement(
                self._accounts, movement_id=movement_id, record_history=True
            )
        except Exception:
            return

        try:
            if self._accounts_service is not None:
                self._accounts_service.save_all(self._accounts)
        except Exception:
            pass

        try:
            self._load_and_refresh_accounts()
        except Exception:
            pass

        try:
            self._refresh_report_content()
        except Exception:
            pass

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
            try:
                for card in (self._income_card, self._outcome_card, self._net_card):
                    if card is None:
                        continue
                    val = card.findChild(QLabel, "StatValueCard")
                    if val is not None:
                        val.setText(format_currency(0.0))
            except Exception:
                pass
            return

        inc = float(self._current_report.summary.total_income)
        out = float(self._current_report.summary.total_outcome)
        net = inc - out
        try:
            income_val = self._income_card.findChild(QLabel, "StatValueCard")
            if income_val is not None:
                income_val.setText(format_currency(inc))
        except Exception:
            pass
        try:
            outcome_val = self._outcome_card.findChild(QLabel, "StatValueCard")
            if outcome_val is not None:
                outcome_val.setText(format_currency(out))
        except Exception:
            pass
        try:
            net_val = self._net_card.findChild(QLabel, "StatValueCard")
            if net_val is not None:
                sign = "+" if net >= 0 else "−"
                net_val.setText(f"{sign}{format_currency(abs(net))}")
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
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(6)
        try:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        try:
            card.setMinimumHeight(84)
            card.setMaximumHeight(112)
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
            all_movements = self._bank_movement_service.list_movements()
            filtered = [
                m
                for m in all_movements
                if m.type == movement_type
                and self._is_in_month(m.date, self._current_year, self._current_month)
                and not bool(getattr(m, "is_transfer", False))
                and str(getattr(m, "category", "") or "").strip() != "העברה"
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
        super().on_route_activated()
        self._load_and_refresh_accounts()
        if isinstance(self._content_col, QVBoxLayout):
            try:
                self.setUpdatesEnabled(False)
                self._clear_content_layout(self._content_col)
                self._build_content(self._content_col)
            finally:
                self.setUpdatesEnabled(True)
                self.update()

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
