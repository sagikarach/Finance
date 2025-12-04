from __future__ import annotations

from typing import Callable, List, Optional
import math

from ..qt import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QFrame,
    Qt,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QCategoryAxis,
    QColor,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPointF,
    charts_available,
)
from ..models.accounts import BankAccount, MoneySnapshot, parse_iso_date
from .savings_history_chart import ShadowChartView


def create_bank_history_chart_card(
    parent: QWidget,
    account: BankAccount,
    format_amount: Callable[[float], str],
) -> QWidget:
    """Create the bottom card with a smoothed line chart showing bank account history."""
    chart_card = QWidget(parent)
    chart_card.setObjectName("Sidebar")
    try:
        chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    except Exception:
        pass
    chart_layout = QVBoxLayout(chart_card)
    chart_layout.setContentsMargins(8, 8, 8, 8)
    chart_layout.setSpacing(8)

    if charts_available and account.history:
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        # Build ordered list of (year, month) keys from history
        month_keys: List[tuple[int, int]] = []
        seen_months: set[tuple[int, int]] = set()
        for snap in account.history:
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

        # Group history by month and take the latest snapshot amount within each month
        latest_by_month: dict[tuple[int, int], MoneySnapshot] = {}
        for snap in account.history:
            dt = parse_iso_date(str(snap.date))
            key = (dt.year, dt.month)
            existing = latest_by_month.get(key)
            if existing is None:
                latest_by_month[key] = snap
            else:
                if parse_iso_date(str(existing.date)) < dt:
                    latest_by_month[key] = snap

        # Build base values for every month, carrying forward the last known amount
        base_values: List[float] = []
        last_amount = 0.0
        max_amount = 0.0

        if not latest_by_month:
            # If no history, use current total amount
            last_amount = float(account.total_amount)
            for _key in month_keys:
                base_values.append(last_amount)
                if last_amount > max_amount:
                    max_amount = last_amount
        else:
            for key in month_keys:
                snap_opt = latest_by_month.get(key)
                if snap_opt is not None:
                    last_amount = float(snap_opt.amount)
                base_values.append(last_amount)
                if last_amount > max_amount:
                    max_amount = last_amount

        # Create a single line series for the bank account
        series = QLineSeries()
        series.setName(account.name)
        try:
            series.setPointsVisible(False)
        except Exception:
            pass

        n_months = len(month_keys)
        if n_months == 1:
            series.append(0.0, base_values[0])
        else:
            # Smooth the month-to-month knots using a small moving average
            smooth_knots: List[float] = list(base_values)
            if n_months >= 3:
                tmp = list(smooth_knots)
                for i_k in range(1, n_months - 1):
                    tmp[i_k] = (
                        0.25 * smooth_knots[i_k - 1]
                        + 0.5 * smooth_knots[i_k]
                        + 0.25 * smooth_knots[i_k + 1]
                    )
                smooth_knots = tmp

            # Clamp the smoothed curve to the real data range
            min_y_val = min(base_values)
            max_y_val = max(base_values) if base_values else 0.0

            def sample_catmull_rom(i_seg: int, t: float) -> float:
                """Sample a Catmull-Rom spline between month i_seg and i_seg+1."""
                i0 = max(0, min(n_months - 1, i_seg - 1))
                i1 = max(0, min(n_months - 1, i_seg))
                i2 = max(0, min(n_months - 1, i_seg + 1))
                i3 = max(0, min(n_months - 1, i_seg + 2))
                p0 = smooth_knots[i0]
                p1 = smooth_knots[i1]
                p2 = smooth_knots[i2]
                p3 = smooth_knots[i3]
                t2 = t * t
                t3 = t2 * t
                val = 0.5 * (
                    (2.0 * p1)
                    + (-p0 + p2) * t
                    + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                    + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
                )
                if val < min_y_val:
                    val = min_y_val
                if val > max_y_val:
                    val = max_y_val
                return val

            series.append(0.0, smooth_knots[0])
            steps_per_segment = 16
            for i_seg in range(n_months - 1):
                for j in range(1, steps_per_segment + 1):
                    t = float(j) / float(steps_per_segment)
                    x_val = float(i_seg) + t
                    y_val = sample_catmull_rom(i_seg, t)
                    series.append(x_val, y_val)

        # Choose a color for the line (using a blue tone for bank accounts)
        try:
            base_color = QColor("#3b82f6")  # Blue color for bank accounts
        except Exception:
            base_color = QColor("#3b82f6")

        # Style the visible line
        try:
            pen = series.pen()
            pen.setColor(base_color)
            try:
                pen.setWidthF(2.0)
            except Exception:
                pass
            try:
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)  # type: ignore[attr-defined]
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # type: ignore[attr-defined]
            except Exception:
                pass
            series.setPen(pen)
        except Exception:
            pass

        shadow_specs: List[tuple[QLineSeries, QColor]] = [(series, base_color)]
        chart.addSeries(series)

        # Tooltip specs for the custom chart view
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = [
            (series, account.name, list(base_values))
        ]

        # X axis with month/year labels
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

        # Y axis with amount values
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
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

        # Theme-aware axis label colors
        label_color = QColor("#0f172a")
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

        for s_obj in chart.series():
            try:
                s_obj.attachAxis(axis_x)  # type: ignore[arg-type]
                s_obj.attachAxis(axis_y)  # type: ignore[arg-type]
            except Exception:
                pass

        chart_view = ShadowChartView(
            chart,
            shadow_specs,
            month_keys,
            tooltip_specs,
            format_amount,
            chart_card,
        )
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)  # type: ignore[attr-defined]
        chart_view.setFrameShape(QFrame.Shape.NoFrame)  # type: ignore[name-defined]
        chart_view.setStyleSheet("background: transparent;")
        chart_layout.addWidget(chart_view, 1)
    else:
        placeholder = QLabel("אין נתוני היסטוריה להצגה", chart_card)
        placeholder.setObjectName("Subtitle")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(placeholder, 1)

    return chart_card

