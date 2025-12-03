from __future__ import annotations

from typing import Callable, Dict, List, Optional
import math

from ..qt import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QToolButton,
    QPushButton,
    QFrame,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QCategoryAxis,
    QColor,
    QPainter,
    QToolTip,
    QCursor,
    charts_available,
)
from ..data.provider import AccountsProvider
from ..models.accounts import SavingsAccount, MoneySnapshot, parse_iso_date
from .base_page import BasePage
from .savings_page import format_currency


class SavingsAccountPage(BasePage):
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
            page_title="פרטי חסכון",
            # Use a distinct route name so the sidebar can enable the per-account
            # selection arrow, while still treating it as part of the savings
            # section visually (handled in Sidebar.update_route).
            current_route="savings_account",
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        while main_col.count():
            item = main_col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_name = ""
        try:
            selected_name = str(self._app_context.get("selected_savings_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[SavingsAccount] = None
        for acc in self._accounts:
            if isinstance(acc, SavingsAccount) and acc.name == selected_name:
                target = acc
                break

        if target is None:
            # Fallback UI if nothing was selected or account was removed.
            placeholder = QLabel("לא נבחר חשבון חסכון", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        # --- Top third: summary rectangle with total amount and action buttons ---
        top_card = QWidget(self)
        top_card.setObjectName("Sidebar")
        try:
            top_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(16)

        summary_col = QVBoxLayout()
        summary_col.setSpacing(4)

        name_label = QLabel(target.name, top_card)
        name_label.setObjectName("HeaderTitle")
        total_label = QLabel(format_currency(target.total_amount), top_card)
        total_label.setObjectName("StatValueLarge")
        liquid_text = "נזיל" if target.is_liquid else "לא נזיל"
        liquid_label = QLabel(liquid_text, top_card)
        liquid_label.setObjectName("StatTitle")

        summary_col.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignLeft)
        summary_col.addWidget(liquid_label, 0, Qt.AlignmentFlag.AlignLeft)

        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(8)

        add_point_btn = QPushButton("הוסף נתון היסטוריה", top_card)
        edit_account_btn = QPushButton("ערוך חשבון", top_card)
        refresh_btn = QPushButton("רענן", top_card)
        for b in (add_point_btn, edit_account_btn, refresh_btn):
            try:
                b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            buttons_col.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)

        top_layout.addLayout(summary_col, 1)
        top_layout.addStretch(1)
        top_layout.addLayout(buttons_col, 0)

        # --- Bottom 2/3: rectangle with line chart of savings history ---
        chart_card = QWidget(self)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)

        if charts_available and target.savings:
            chart = QChart()
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            # Remove legend and background so the chart blends with the card.
            chart.legend().setVisible(False)
            chart.setBackgroundRoundness(0)
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
            chart.setPlotAreaBackgroundVisible(False)

            # Build a global ordered list of (year, month) keys across all
            # savings histories so all lines share the same month positions.
            month_keys: List[tuple[int, int]] = []
            seen_months: set[tuple[int, int]] = set()
            for s in target.savings:
                for snap in s.history:
                    dt = parse_iso_date(str(snap.date))
                    key = (dt.year, dt.month)
                    if key not in seen_months:
                        seen_months.add(key)
                        month_keys.append(key)

            if not month_keys:
                # Fallback: single synthetic month if there is no history.
                month_keys = [(0, 1)]

            month_keys.sort(key=lambda k: (k[0], k[1]))
            month_to_index = {key: idx for idx, key in enumerate(month_keys)}

            max_amount = 0.0

            for s in target.savings:
                series = QLineSeries()
                series.setName(s.name)
                # Hide square markers on the line; we only want smooth lines.
                try:
                    series.setPointsVisible(False)
                except Exception:
                    pass

                # Group this savings' history by month and take the latest
                # snapshot amount within each month.
                latest_by_month: dict[tuple[int, int], MoneySnapshot] = {}
                for snap in s.history:
                    dt = parse_iso_date(str(snap.date))
                    key = (dt.year, dt.month)
                    existing = latest_by_month.get(key)
                    # Help type-checker: guard against None explicitly before
                    # assigning to the dictionary of concrete MoneySnapshot.
                    if existing is None:
                        latest_by_month[key] = snap
                    else:
                        if parse_iso_date(str(existing.date)) < dt:
                            latest_by_month[key] = snap

                # Build a value for every month in month_keys so each savings
                # line is continuous across the whole range. For months with
                # no data, we carry forward the last known amount (or 0 before
                # the first data point).
                last_amount = 0.0
                if not latest_by_month:
                    # No history at all: use the current total amount flat
                    # across all months.
                    last_amount = float(s.amount)
                    for key in month_keys:
                        x_val = float(month_to_index[key])
                        series.append(x_val, last_amount)
                        if last_amount > max_amount:
                            max_amount = last_amount
                else:
                    for key in month_keys:
                        snap_opt = latest_by_month.get(key)
                        if snap_opt is not None:
                            last_amount = float(snap_opt.amount)
                        x_val = float(month_to_index[key])
                        series.append(x_val, last_amount)
                        if last_amount > max_amount:
                            max_amount = last_amount

                chart.addSeries(series)

                # Connect hover handler to show tooltip with month, savings
                # name and amount for each point.
                def make_hover_handler(savings_name: str, values: List[float]):
                    def on_hover(point, state):  # type: ignore[no-redef]
                        if not state:
                            return
                        # point.x() is the month index; clamp to values range.
                        idx = int(round(point.x()))
                        if idx < 0 or idx >= len(values):
                            return
                        amount_val = values[idx]
                        label_idx = 0
                        if 0 <= idx < len(month_keys):
                            year, month = month_keys[idx]
                            month_label = f"{month:02d}/{year % 100:02d}"
                        else:
                            month_label = str(idx)
                        text = f"{savings_name}\n{month_label}: {format_currency(amount_val)}"
                        try:
                            QToolTip.showText(QCursor.pos(), text)
                        except Exception:
                            pass

                    return on_hover

                # Capture the sequence of y-values for this series in month
                # order so the hover handler can look them up by index.
                series_values: List[float] = []
                if not latest_by_month:
                    last_amount_tmp = float(s.amount)
                    series_values = [last_amount_tmp for _ in month_keys]
                else:
                    last_amount_tmp = 0.0
                    for key in month_keys:
                        snap_opt = latest_by_month.get(key)
                        if snap_opt is not None:
                            last_amount_tmp = float(snap_opt.amount)
                        series_values.append(last_amount_tmp)

                try:
                    series.hovered.connect(make_hover_handler(s.name, series_values))  # type: ignore[arg-type]
                except Exception:
                    pass

            # X axis with month/year labels (no axis title, no grid).
            axis_x = QCategoryAxis()
            for key in month_keys:
                year, month = key
                label = f"{month:02d}/{year % 100:02d}"
                axis_x.append(label, float(month_to_index[key]))
            try:
                axis_x.setGridLineVisible(False)
                axis_x.setMinorGridLineVisible(False)  # type: ignore[attr-defined]
            except Exception:
                pass

            # Y axis with amount values (no axis title, no grid).
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%.0f")
            # Round the top of the range up to the next 1000 so ticks are
            # aligned on multiples of 1000, and use a 1000 interval when
            # supported.
            if max_amount > 0:
                top = float(math.ceil(max_amount / 1000.0) * 1000.0)
            else:
                top = 1000.0
            axis_y.setRange(0.0, top)
            try:
                axis_y.setTickInterval(1000.0)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                axis_y.setGridLineVisible(False)
                axis_y.setMinorGridLineVisible(False)  # type: ignore[attr-defined]
            except Exception:
                pass

            # Theme-aware axis label colors: pure white in dark mode, dark
            # navy in light mode.
            label_color = QColor("#0f172a")  # light mode default
            app = QApplication.instance()
            if app is not None:
                try:
                    theme = str(app.property("theme") or "light")
                    if theme == "dark":
                        label_color = QColor("#ffffff")
                except Exception:
                    pass
            try:
                axis_x.setLabelsBrush(label_color)
                axis_y.setLabelsBrush(label_color)
            except Exception:
                pass

            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

            for series in chart.series():
                try:
                    series.attachAxis(axis_x)  # type: ignore[arg-type]
                    series.attachAxis(axis_y)  # type: ignore[arg-type]
                except Exception:
                    pass

            chart_view = QChartView(chart, chart_card)
            chart_view.setRenderHint(QPainter.Antialiasing)  # type: ignore[name-defined]
            chart_view.setFrameShape(QFrame.Shape.NoFrame)  # type: ignore[name-defined]
            chart_view.setStyleSheet("background: transparent;")
            chart_layout.addWidget(chart_view, 1)
        else:
            placeholder = QLabel("אין נתוני היסטוריה להצגה", chart_card)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(placeholder, 1)

        # Layout: top card 1/3 height, bottom card 2/3 height.
        main_col.addWidget(top_card, 1)
        main_col.addWidget(chart_card, 2)

    def on_route_activated(self) -> None:
        """Called by Router.navigate whenever this route becomes active."""
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        """Ensure chart colors update when switching between light/dark mode."""
        # Call base implementation to keep header/sidebar/theme button in sync.
        super()._on_theme_changed(is_dark)
        # Rebuild content so axis label colors and chart styling reflect
        # the current theme.
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
