from __future__ import annotations

from typing import Dict, Optional, List, Callable

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QToolButton,
)
from ..data.provider import AccountsProvider
from ..models.accounts_service import AccountsService
from ..models.overview import AccountsOverview
from ..models.yearly_report_service import YearlyReportService
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..widgets.monthly_cashflow_chart import MonthlyCashflowChart
from ..widgets.action_history_table import ActionHistoryTable
from ..utils.formatting import format_currency
from .base_page import BasePage


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

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons = []
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

    def _stat_card(
        self, parent: QWidget, object_name: str, title: str, value: str,
    ) -> QWidget:
        card = QWidget(parent)
        card.setObjectName(object_name)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
            card.setMinimumHeight(118)
            card.setMaximumHeight(150)
        except Exception:
            pass
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)
        t = QLabel(title, card)
        t.setObjectName("StatTitle")
        v = QLabel(value, card)
        v.setObjectName("StatValueLarge")
        lay.addStretch(1)
        lay.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        return card

    def _chart_panel(
        self, parent: QWidget, subtitle: str, title: str, chart: QWidget,
    ) -> QWidget:
        panel = QWidget(parent)
        panel.setObjectName("ContentPanel")
        try:
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(6)
        sub = QLabel(subtitle, panel)
        sub.setObjectName("PanelSubtitle")
        ttl = QLabel(title, panel)
        ttl.setObjectName("PanelTitle")
        lay.addWidget(sub)
        lay.addWidget(ttl)
        lay.addWidget(chart, 1)
        return panel

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
        except Exception:
            window = []
        labels = [lbl for lbl, _ in window]
        nets = [n for _, n in window]
        avg_net = (sum(nets) / len(nets)) if nets else 0.0

        # ── top row: three stat cards ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(
            self._stat_card(
                parent_widget, "DashHeroYellow", "סה״כ כסף",
                format_currency(overview.total_all),
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
        except Exception:
            pass
        bars_panel = self._chart_panel(
            parent_widget, "6 חודשים אחרונים", "תזרים חודשי", bars
        )

        donut = AccountsPieChart(accounts=overview.accounts, parent=parent_widget)
        donut_panel = self._chart_panel(
            parent_widget, "היכן הכסף", "פילוח חשבונות", donut
        )

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
        except Exception:
            pass
        activity_layout = QVBoxLayout(activity_panel)
        activity_layout.setContentsMargins(6, 6, 6, 8)
        activity_layout.setSpacing(0)

        try:
            history = self._history_provider.list_history()
        except Exception:
            history = []
        categories = []
        try:
            categories = self._bank_movement_service.list_categories(is_income=False)
        except Exception:
            categories = []

        def on_saved() -> None:
            try:
                history = self._history_provider.list_history()
                history_table.set_history(history)
                if self._accounts_service is not None:
                    try:
                        self._accounts = self._accounts_service.load_accounts()
                    except Exception:
                        pass
            except Exception:
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
