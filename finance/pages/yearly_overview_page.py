from __future__ import annotations

import threading
import weakref
from datetime import date
from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.yearly_report_service import YearlyReportService
from ..models.gemini_classifier import get_gemini_classifier, has_gemini_api_key
from ..qt import (
    QLabel,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..utils.formatting import format_currency
from ..widgets.yearly_balance_chart import YearlyBalanceChart
from ..widgets.time_range_bar import TimeRangeBar
from .base_page import BasePage


def _future_month_labels(horizon: int) -> List[str]:
    """Return short Hebrew month labels for the next *horizon* months."""
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

    def set_value(self, text: str) -> None:
        self._value.setText(text)
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

        self._range_bar: Optional[TimeRangeBar] = None
        self._income_value: Optional[QLabel] = None
        self._expense_value: Optional[QLabel] = None
        self._net_value: Optional[QLabel] = None
        self._balance_chart: Optional[YearlyBalanceChart] = None
        self._proj_status_label: Optional[QLabel] = None

        self._proj_loading: bool = False
        self._proj_error: Optional[str] = None
        self._proj_nets: Optional[List[float]] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="סיכום שנתי",
            current_route="yearly_overview",
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
        try:
            container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        # ── stat cards row (no year picker) ──────────────────────────────
        top_row = QWidget(container)
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(16)

        income_card = AutoStatCard("הכנסות", container)
        expense_card = AutoStatCard("הוצאות", container)
        net_card = AutoStatCard("יתרה", container)
        income_card.setObjectName("StatCardGreen")
        expense_card.setObjectName("StatCardRed")
        net_card.setObjectName("StatCardPurple")
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
        chart_layout.setContentsMargins(16, 16, 16, 16)
        chart_layout.setSpacing(8)

        self._range_bar = TimeRangeBar(chart_card, default_months=self._current_months)
        self._range_bar.range_changed.connect(self._on_range_changed)
        chart_layout.addWidget(self._range_bar)

        self._proj_status_label = QLabel("", chart_card)
        self._proj_status_label.setObjectName("Subtitle")
        try:
            self._proj_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        self._proj_status_label.hide()
        chart_layout.addWidget(self._proj_status_label)

        self._balance_chart = YearlyBalanceChart(chart_card)
        chart_layout.addWidget(self._balance_chart, 1)

        layout.addWidget(top_row, 0)
        layout.addWidget(chart_card, 1)
        main_col.addWidget(container, 1)

        self._refresh()

    # ------------------------------------------------------------------ range

    def _on_range_changed(self, months: int) -> None:
        self._current_months = months
        self._proj_nets = None
        self._proj_error = None
        self._refresh()
        if months == -1 and has_gemini_api_key():
            self._start_forecast_thread()

    def _refresh(self) -> None:
        forecast = self._current_months == -1
        actual_months = 3 if forecast else self._current_months

        # Stat cards
        income, expense, net = self._yearly_service.get_window_totals(actual_months)
        if self._income_value is not None:
            self._income_value.setText(format_currency(income))
        if self._expense_value is not None:
            self._expense_value.setText(format_currency(expense))
        if self._net_value is not None:
            self._net_value.setText(format_currency(net))

        # Chart
        window_data = self._yearly_service.get_window_nets(actual_months)
        labels = [lbl for lbl, _ in window_data]
        nets = [n for _, n in window_data]

        if self._balance_chart is not None:
            if forecast and self._proj_nets:
                self._balance_chart.set_monthly_net(
                    nets, labels,
                    proj_values=self._proj_nets,
                    proj_labels=_future_month_labels(len(self._proj_nets)),
                )
            else:
                self._balance_chart.set_monthly_net(nets, labels)

        # Status label
        if self._proj_status_label is not None:
            if forecast:
                if self._proj_loading:
                    self._proj_status_label.setText("⏳ מחשב תחזית AI...")
                    self._proj_status_label.show()
                elif self._proj_error:
                    self._proj_status_label.setText(f"❌ {self._proj_error}")
                    self._proj_status_label.show()
                else:
                    self._proj_status_label.hide()
            else:
                self._proj_status_label.hide()

    # ------------------------------------------------------------------ forecast

    def _start_forecast_thread(self) -> None:
        svc = self._yearly_service
        page_ref = weakref.ref(self)

        def _set_loading(val: bool) -> None:
            page = page_ref()
            if page is not None:
                page._proj_loading = val
                page._refresh()

        def _set_data(result: List[float]) -> None:
            page = page_ref()
            if page is not None:
                page._proj_loading = False
                page._proj_nets = result
                page._refresh()

        def _set_failed(msg: str) -> None:
            page = page_ref()
            if page is not None:
                page._proj_loading = False
                page._proj_error = msg
                page._refresh()

        QTimer.singleShot(0, lambda: _set_loading(True))

        def _run() -> None:
            try:
                history = svc.get_window_nets(12)
                result = get_gemini_classifier().predict_monthly_net(history, horizon=6)
                if result:
                    QTimer.singleShot(0, lambda: _set_data(result))
                else:
                    QTimer.singleShot(
                        0, lambda: _set_failed("לא התקבלה תחזית מה-AI — נסה שוב מאוחר יותר")
                    )
            except Exception:
                QTimer.singleShot(0, lambda: _set_failed("תחזית נכשלה — בדוק חיבור לאינטרנט"))

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------ lifecycle

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
