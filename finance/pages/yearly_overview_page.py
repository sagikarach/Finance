from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.yearly_report_service import YearlyReportService, forecast_net
from ..qt import (
    QCheckBox,
    QLabel,
    QHBoxLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..utils.formatting import format_currency
from ..widgets.yearly_balance_chart import YearlyBalanceChart
from ..widgets.time_range_bar import TimeRangeBar
from ..widgets.chart_utils import future_month_labels
from .base_page import BasePage


class AutoStatCard(QWidget):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        try:
            self.setMinimumHeight(100)
            self.setMinimumWidth(90)
        except Exception:
            pass

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(2)

        self._title = QLabel(title, self)
        self._title.setObjectName("Subtitle")
        try:
            self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        self._value = QLabel("", self)
        self._value.setObjectName("StatValueLarge")
        try:
            self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        v.addStretch(1)
        v.addWidget(self._title, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(self._value, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addStretch(1)

        self._apply_fonts()

    def value_label(self) -> QLabel:
        return self._value

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_fonts()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_fonts()

    def _clamp(self, v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, int(v)))

    def _apply_fonts(self) -> None:
        base = min(max(1, int(self.width())), max(1, int(self.height())))
        title_px = self._clamp(int(base * 0.7), 8, 18)
        value_px = self._clamp(int(base), 12, 30)
        try:
            f = self._title.font()
            f.setPixelSize(int(title_px))
            self._title.setFont(f)
        except Exception:
            pass
        try:
            f = self._value.font()
            f.setPixelSize(int(value_px))
            self._value.setFont(f)
        except Exception:
            pass


class YearlyOverviewPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._yearly_service = YearlyReportService(self._movement_provider)
        self._current_months: int = 12
        self._include_one_time: bool = False

        self._range_bar: Optional[TimeRangeBar] = None
        self._one_time_checkbox: Optional[QCheckBox] = None
        self._income_value: Optional[QLabel] = None
        self._expense_value: Optional[QLabel] = None
        self._net_value: Optional[QLabel] = None
        self._balance_chart: Optional[YearlyBalanceChart] = None
        self._proj_nets: Optional[List[float]] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="סיכום שנתי",
            current_route="yearly_overview",
        )

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        try:
            container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        # ── stat cards row ────────────────────────────────────────────────
        top_row = QWidget(container)
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(16)

        income_card = AutoStatCard("הכנסות", container)
        expense_card = AutoStatCard("הוצאות", container)
        net_card = AutoStatCard("יתרה", container)
        income_card.setObjectName("MonthIncomeCard")
        expense_card.setObjectName("MonthExpenseCard")
        net_card.setObjectName("MonthNetCard")
        try:
            income_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            expense_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            net_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._income_value = income_card.value_label()
        self._expense_value = expense_card.value_label()
        self._net_value = net_card.value_label()

        top_row_layout.addWidget(income_card, 1)
        top_row_layout.addWidget(expense_card, 1)
        top_row_layout.addWidget(net_card, 1)

        # ── chart card with TimeRangeBar inside ───────────────────────────
        chart_card = QWidget(container)
        chart_card.setObjectName("ContentPanel")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(20, 18, 20, 18)
        chart_layout.setSpacing(12)

        panel_title = QLabel("מאזן חודשי לאורך זמן", chart_card)
        panel_title.setObjectName("PanelTitle")
        chart_layout.addWidget(panel_title)

        controls_row = QWidget(chart_card)
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self._range_bar = TimeRangeBar(controls_row, default_months=self._current_months)
        self._range_bar.range_changed.connect(self._on_range_changed)
        controls_layout.addWidget(self._range_bar)
        controls_layout.addStretch(1)

        self._one_time_checkbox = QCheckBox("כלול תנועות חד-פעמיות", controls_row)
        self._one_time_checkbox.setChecked(self._include_one_time)
        self._one_time_checkbox.toggled.connect(self._on_one_time_toggled)
        # Keep the full label from being squeezed (clipped) when the range bar
        # crowds the row; never shrink below the text's natural width.
        try:
            self._one_time_checkbox.setSizePolicy(
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
            )
            self._one_time_checkbox.setMinimumWidth(
                self._one_time_checkbox.sizeHint().width()
            )
        except Exception:
            pass
        controls_layout.addWidget(self._one_time_checkbox)

        chart_layout.addWidget(controls_row)

        self._balance_chart = YearlyBalanceChart(chart_card)
        chart_layout.addWidget(self._balance_chart, 1)

        layout.addWidget(top_row, 0)
        layout.addWidget(chart_card, 1)
        main_col.addWidget(container, 1)

        self._refresh()

    # ------------------------------------------------------------------ range

    def _on_range_changed(self, months: int) -> None:
        self._current_months = months
        self._recompute_forecast()
        self._refresh()

    def _on_one_time_toggled(self, checked: bool) -> None:
        self._include_one_time = bool(checked)
        self._recompute_forecast()
        self._refresh()

    def _recompute_forecast(self) -> None:
        self._proj_nets = None
        if self._current_months == -1:
            history = self._yearly_service.get_window_nets(
                12, include_one_time=self._include_one_time
            )
            self._proj_nets = forecast_net(history, horizon=6)

    def _refresh(self) -> None:
        forecast = self._current_months == -1
        actual_months = 3 if forecast else self._current_months

        income, expense, net = self._yearly_service.get_window_totals(
            actual_months, include_one_time=self._include_one_time
        )
        if self._income_value is not None:
            self._income_value.setText(format_currency(income))
        if self._expense_value is not None:
            self._expense_value.setText(format_currency(expense))
        if self._net_value is not None:
            self._net_value.setText(format_currency(net))

        window_data = self._yearly_service.get_window_nets(
            actual_months, include_one_time=self._include_one_time
        )
        labels = [lbl for lbl, _ in window_data]
        nets = [n for _, n in window_data]

        if self._balance_chart is not None:
            if forecast and self._proj_nets:
                self._balance_chart.set_monthly_net(
                    nets, labels,
                    proj_values=self._proj_nets,
                    proj_labels=future_month_labels(len(self._proj_nets)),
                )
            else:
                self._balance_chart.set_monthly_net(nets, labels)

    # ------------------------------------------------------------------ lifecycle

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
