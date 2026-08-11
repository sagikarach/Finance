from __future__ import annotations

from typing import Dict, Optional, Callable

from ..qt import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
)
from ..data.provider import AccountsProvider
from ..models.accounts_service import AccountsService
from ..models.overview import AccountsOverview
from ..models.mortgage_service import MortgageService
from ..models.yearly_report_service import YearlyReportService
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..widgets.monthly_cashflow_chart import MonthlyCashflowChart
from ..widgets.action_history_table import ActionHistoryTable
from ..utils.formatting import format_currency
from .base_page import BasePage
from ..utils.safe import QT_ERRORS


class HomePage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="לוח בקרה",
            current_route="home",
        )
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _stat_card(
        self, parent: QWidget, object_name: str, title: str, value: str,
        subtitle: str = "",
    ) -> QWidget:
        return self._make_stat_card(
            object_name, title, value,
            subtitle=subtitle, min_height=118, spacing=4, parent=parent,
        )

    def _chart_panel(self, parent: QWidget, title: str, chart: QWidget) -> QWidget:
        return self._content_panel(title, chart, parent)

    def _build_content(self, main_col: QVBoxLayout) -> None:
        overview = AccountsOverview.for_home(self._accounts)

        parent_widget = main_col.parentWidget()
        if parent_widget is None:
            parent_widget = self

        # ── monthly cash-flow (last 6 months, one-time excluded) ──
        window = []
        try:
            yr = YearlyReportService(self._bank_movement_provider)
            window = yr.get_window_nets(6, include_one_time=False)
        except QT_ERRORS:
            window = []
        labels = [lbl for lbl, _ in window]
        nets = [n for _, n in window]
        avg_net = (sum(nets) / len(nets)) if nets else 0.0

        # ── net worth of assets (non-liquid), folded into the headline total ──
        try:
            assets_net = MortgageService().total_assets_net()
        except QT_ERRORS:
            assets_net = 0.0

        # ── top row: three stat cards ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(
            self._stat_card(
                parent_widget, "DashHeroYellow", "סה״כ שווי",
                format_currency(overview.total_all + assets_net),
            ),
            3,
        )
        cards_row.addWidget(
            self._stat_card(
                parent_widget, "DashCard", "סכום נזיל",
                format_currency(overview.total_liquid),
            ),
            2,
        )
        cards_row.addWidget(
            self._stat_card(
                parent_widget, "DashCardGreen", "תזרים חודשי ממוצע",
                format_currency(avg_net),
            ),
            2,
        )
        main_col.addLayout(cards_row, 0)

        # ── middle row: cash-flow bars + accounts donut ──
        bars = MonthlyCashflowChart(parent_widget)
        try:
            bars.set_data(nets, labels)
        except QT_ERRORS:
            pass
        bars_panel = self._chart_panel(parent_widget, "תזרים חודשי", bars)

        asset_slices = [("נכסים", assets_net)] if assets_net > 0.5 else []
        donut = AccountsPieChart(
            accounts=overview.accounts,
            parent=parent_widget,
            extra_slices=asset_slices,
        )
        donut_panel = self._chart_panel(parent_widget, "פילוח חשבונות", donut)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(16)
        charts_row.addWidget(bars_panel, 3)
        charts_row.addWidget(donut_panel, 2)
        main_col.addLayout(charts_row, 3)

        # ── bottom row: recent activity (full width) ──
        activity_panel = QWidget(parent_widget)
        activity_panel.setObjectName("ContentPanel")
        try:
            activity_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(6, 6, 6, 8)
        activity_layout.setSpacing(0)

        try:
            history = self._history_provider.list_history()
        except QT_ERRORS:
            history = []
        categories = []
        try:
            categories = self._bank_movement_service.list_categories(is_income=False)
        except QT_ERRORS:
            categories = []

        def on_saved() -> None:
            try:
                history = self._history_provider.list_history()
                history_table.set_history(history)
                if self._accounts_service is not None:
                    try:
                        self._accounts = self._accounts_service.load_accounts()
                    except QT_ERRORS:
                        pass
            except QT_ERRORS:
                pass

        history_table = ActionHistoryTable(
            history=history,
            max_rows=6,
            parent=activity_panel,
            categories=categories,
            movement_service=self._bank_movement_service,
            on_saved=on_saved,
            history_provider=self._history_provider,
        )
        activity_layout.addWidget(history_table, 1)
        main_col.addWidget(activity_panel, 2)

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
