from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional, Set, Tuple

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.bank_movement import MovementType
from ..models.yearly_report_service import YearlyReportService, forecast_category_totals
from ..qt import (
    QLabel,
    QCheckBox,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    Qt,
)
from ..widgets.category_trends_chart import CategoryTrendsChart
from ..widgets.time_range_bar import TimeRangeBar
from .base_page import BasePage


def _future_month_labels(horizon: int) -> List[str]:
    heb = ["ינו", "פבר", "מרץ", "אפר", "מאי", "יוני",
           "יול", "אוג", "ספט", "אוק", "נוב", "דצמ"]
    today = date.today()
    labels: List[str] = []
    y, m = today.year, today.month
    for _ in range(horizon):
        m += 1
        if m > 12:
            m = 1
            y += 1
        labels.append(f"{heb[m - 1]} {y % 100:02d}")
    return labels


class YearlyCategoryTrendsPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
        yearly_service: Optional[YearlyReportService] = None,
        movement_types: Optional[Set[MovementType]] = None,
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._yearly_service = yearly_service or YearlyReportService(
            self._movement_provider
        )
        self._initial_movement_types = movement_types
        self._current_months: int = 12

        self._range_bar: Optional[TimeRangeBar] = None
        self._combined_chart: Optional[CategoryTrendsChart] = None

        self._show_income: bool = True
        self._show_expense: bool = True
        if movement_types is not None:
            self._type_monthly: bool = MovementType.MONTHLY in movement_types
            self._type_one_time: bool = MovementType.ONE_TIME in movement_types
            self._type_yearly: bool = MovementType.YEARLY in movement_types
        else:
            self._type_monthly = True
            self._type_one_time = False
            self._type_yearly = False
        self._income_cb: Optional[QCheckBox] = None
        self._expense_cb: Optional[QCheckBox] = None
        self._monthly_cb: Optional[QCheckBox] = None
        self._one_time_cb: Optional[QCheckBox] = None
        self._yearly_cb: Optional[QCheckBox] = None

        self._proj_income: Optional[Dict[str, List[float]]] = None
        self._proj_expense: Optional[Dict[str, List[float]]] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="מגמות לפי קטגוריה",
            current_route="yearly_category_trends",
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
            settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── top controls: TimeRangeBar + filters ─────────────────────────
        top_controls = QWidget(container)
        top_controls.setObjectName("TrendsControlsBar")
        try:
            top_controls.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        top_controls_layout = QHBoxLayout(top_controls)
        top_controls_layout.setContentsMargins(0, 0, 0, 0)
        top_controls_layout.setSpacing(8)

        self._range_bar = TimeRangeBar(
            top_controls, default_months=self._current_months
        )
        self._range_bar.range_changed.connect(self._on_range_changed)

        filters_box = QWidget(container)
        try:
            filters_box.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        filters_box_layout = QHBoxLayout(filters_box)
        filters_box_layout.setContentsMargins(0, 0, 0, 0)
        filters_box_layout.setSpacing(8)

        show_label = QLabel("הצג:", filters_box)
        show_label.setObjectName("TrendsControlsLabel")
        self._income_cb = QCheckBox("הכנסות", filters_box)
        self._expense_cb = QCheckBox("הוצאות", filters_box)
        self._income_cb.setChecked(bool(self._show_income))
        self._expense_cb.setChecked(bool(self._show_expense))
        self._income_cb.toggled.connect(self._on_filters_changed)
        self._expense_cb.toggled.connect(self._on_filters_changed)

        types_label = QLabel("סוגים:", filters_box)
        types_label.setObjectName("TrendsControlsLabel")
        self._monthly_cb = QCheckBox("חודשי", filters_box)
        self._one_time_cb = QCheckBox("חד-פעמי", filters_box)
        self._yearly_cb = QCheckBox("שנתי", filters_box)

        self._monthly_cb.setChecked(bool(self._type_monthly))
        self._one_time_cb.setChecked(bool(self._type_one_time))
        self._yearly_cb.setChecked(bool(self._type_yearly))
        self._monthly_cb.toggled.connect(self._on_filters_changed)
        self._one_time_cb.toggled.connect(self._on_filters_changed)
        self._yearly_cb.toggled.connect(self._on_filters_changed)

        def _fix_min_width(w: QWidget) -> None:
            try:
                w.ensurePolished()
            except Exception:
                pass
            try:
                w.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            try:
                hint = w.sizeHint()
                w.setMinimumWidth(int(hint.width()) + 2)
            except Exception:
                pass

        def _fix_checkbox_min_width(cb: QCheckBox) -> None:
            try:
                cb.ensurePolished()
                fm = cb.fontMetrics()
                text = cb.text() or ""
                try:
                    text_w = int(fm.horizontalAdvance(text))
                except Exception:
                    text_w = int(len(text) * 10)
                cb.setMinimumWidth(text_w + 18 + 12 + 8)
            except Exception:
                _fix_min_width(cb)

        for w in (
            show_label, self._income_cb, self._expense_cb,
            types_label, self._monthly_cb, self._one_time_cb, self._yearly_cb,
        ):
            if w is not None:
                if isinstance(w, QCheckBox):
                    _fix_checkbox_min_width(w)
                else:
                    _fix_min_width(w)

        divider = QWidget(filters_box)
        divider.setObjectName("TrendsControlsDividerLine")
        try:
            divider.setFixedWidth(3)
            divider.setFixedHeight(22)
        except Exception:
            pass

        filters_box_layout.addWidget(show_label, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addWidget(self._income_cb, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addWidget(self._expense_cb, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addSpacing(8)
        filters_box_layout.addWidget(
            divider, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        filters_box_layout.addSpacing(8)
        filters_box_layout.addWidget(types_label, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addWidget(self._monthly_cb, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addWidget(self._one_time_cb, 0, Qt.AlignmentFlag.AlignRight)
        filters_box_layout.addWidget(self._yearly_cb, 0, Qt.AlignmentFlag.AlignRight)

        top_controls_layout.addWidget(self._range_bar, 0, Qt.AlignmentFlag.AlignRight)
        top_controls_layout.addSpacing(8)
        top_controls_layout.addWidget(filters_box, 0, Qt.AlignmentFlag.AlignRight)
        top_controls_layout.addStretch(1)

        layout.addWidget(top_controls, 0)

        # ── chart card ────────────────────────────────────────────────────
        chart_card = QWidget(container)
        chart_card.setObjectName("ContentPanel")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        chart_layout.setSpacing(8)

        self._combined_chart = CategoryTrendsChart(chart_card)
        chart_layout.addWidget(self._combined_chart, 1)

        layout.addWidget(chart_card, 1)
        main_col.addWidget(container, 1)

        try:
            if self._combined_chart is not None:
                setter = getattr(self._combined_chart, "set_transition_enabled", None)
                if callable(setter):
                    setter(False)
        except Exception:
            pass
        try:
            self._refresh()
        except Exception:
            pass
        try:
            if self._combined_chart is not None:
                setter = getattr(self._combined_chart, "set_transition_enabled", None)
                if callable(setter):
                    setter(True)
        except Exception:
            pass

    # ------------------------------------------------------------------ range

    def _on_range_changed(self, months: int) -> None:
        self._current_months = months
        self._proj_income = None
        self._proj_expense = None
        if months == -1:
            self._compute_forecast()
        self._refresh()

    def _refresh(self) -> None:
        if self._combined_chart is None:
            return

        forecast = self._current_months == -1
        actual_months = 3 if forecast else self._current_months

        types: Set[MovementType] = set()
        if self._type_monthly:
            types.add(MovementType.MONTHLY)
        if self._type_one_time:
            types.add(MovementType.ONE_TIME)
        if self._type_yearly:
            types.add(MovementType.YEARLY)
        types_filter: Optional[Set[MovementType]] = types if types else set()

        income: Dict[str, List[float]] = {}
        income_labels: List[str] = []
        if self._show_income:
            income, income_labels = self._yearly_service.get_window_category_totals(
                actual_months, is_income=True, movement_types=types_filter
            )

        expense: Dict[str, List[float]] = {}
        expense_labels: List[str] = []
        if self._show_expense:
            expense, expense_labels = self._yearly_service.get_window_category_totals(
                actual_months, is_income=False, movement_types=types_filter
            )

        month_labels = income_labels or expense_labels

        if forecast and (self._proj_income or self._proj_expense):
            self._combined_chart.set_combined_series(
                income,
                expense,
                month_labels,
                expenses_negative=False,
                proj_income=self._proj_income,
                proj_expense=self._proj_expense,
                proj_labels=_future_month_labels(6),
            )
        else:
            self._combined_chart.set_combined_series(
                income, expense, month_labels, expenses_negative=False
            )

    # ------------------------------------------------------------------ forecast

    def _compute_forecast(self) -> None:
        types: Set[MovementType] = set()
        if self._type_monthly:
            types.add(MovementType.MONTHLY)
        if self._type_one_time:
            types.add(MovementType.ONE_TIME)
        if self._type_yearly:
            types.add(MovementType.YEARLY)
        types_filter: Optional[Set[MovementType]] = types if types else set()

        if self._show_income:
            inc_hist, _ = self._yearly_service.get_window_category_totals(
                12, is_income=True, movement_types=types_filter
            )
            self._proj_income = forecast_category_totals(inc_hist, horizon=6)
        if self._show_expense:
            exp_hist, _ = self._yearly_service.get_window_category_totals(
                12, is_income=False, movement_types=types_filter
            )
            self._proj_expense = forecast_category_totals(exp_hist, horizon=6)

    # ------------------------------------------------------------------ filters

    def _on_filters_changed(self, _checked: bool) -> None:
        try:
            if self._income_cb is not None:
                self._show_income = bool(self._income_cb.isChecked())
            if self._expense_cb is not None:
                self._show_expense = bool(self._expense_cb.isChecked())
            if self._monthly_cb is not None:
                self._type_monthly = bool(self._monthly_cb.isChecked())
            if self._one_time_cb is not None:
                self._type_one_time = bool(self._one_time_cb.isChecked())
            if self._yearly_cb is not None:
                self._type_yearly = bool(self._yearly_cb.isChecked())
        except Exception:
            pass
        self._refresh()

    # ------------------------------------------------------------------ lifecycle

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        try:
            if self._combined_chart is not None:
                setter = getattr(self._combined_chart, "set_transition_enabled", None)
                if callable(setter):
                    setter(False)
        except Exception:
            pass
        try:
            self._refresh()
        except Exception:
            pass
        try:
            if self._combined_chart is not None:
                setter = getattr(self._combined_chart, "set_transition_enabled", None)
                if callable(setter):
                    setter(True)
        except Exception:
            pass
