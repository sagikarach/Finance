from __future__ import annotations

from typing import Callable, List, Optional
import math

from ..qt import (
    QApplication,
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
    QToolTip,
    QCursor,
    charts_available,
)
from ..models.accounts import SavingsAccount, MoneySnapshot, parse_iso_date


class ShadowChartView(QChartView):
    def __init__(
        self,
        chart: QChart,
        shadows: List[tuple[QLineSeries, QColor]],
        month_keys: List[tuple[int, int]],
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]],
        format_amount: Callable[[float], str],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(chart, parent)
        self._shadows: List[tuple[QLineSeries, QColor]] = shadows
        self._month_keys: List[tuple[int, int]] = month_keys
        self._tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = tooltip_specs
        self._format_amount = format_amount
        try:
            self.setMouseTracking(True)
        except Exception:
            pass

    def drawForeground(self, painter: QPainter, rect) -> None:  # type: ignore[override]
        # Keep any default foreground (e.g. tooltips) first.
        try:
            super().drawForeground(painter, rect)
        except Exception:
            pass

        try:
            chart = self.chart()
        except Exception:
            chart = None
        if chart is None or not self._shadows:
            return

        try:
            plot_rect = chart.plotArea()
        except Exception:
            plot_rect = rect
        bottom_y = plot_rect.bottom()

        for series, base_color in self._shadows:
            # Collect data points from the series.
            try:
                pts = list(series.points())  # type: ignore[attr-defined]
            except Exception:
                try:
                    pts = list(series.pointsVector())  # type: ignore[attr-defined]
                except Exception:
                    pts = []
            if len(pts) < 2:
                continue

            path = QPainterPath()
            try:
                first_pos = chart.mapToPosition(pts[0], series)  # type: ignore[arg-type]
            except Exception:
                continue
            path.moveTo(first_pos)
            last_pos = first_pos
            min_y = first_pos.y()

            for pt in pts[1:]:
                try:
                    pos = chart.mapToPosition(pt, series)  # type: ignore[arg-type]
                except Exception:
                    continue
                path.lineTo(pos)
                last_pos = pos
                if pos.y() < min_y:
                    min_y = pos.y()

            # Close the path down to the bottom of the plot area so the fill
            # appears only under the line.
            try:
                path.lineTo(QPointF(last_pos.x(), bottom_y))
                path.lineTo(QPointF(first_pos.x(), bottom_y))
            except Exception:
                pass
            try:
                path.closeSubpath()
            except Exception:
                pass

            # Create a vertical gradient that is strongest near the line
            # (around min_y) and fades out towards the bottom of the plot.
            gradient = None
            try:
                gradient = QLinearGradient(
                    QPointF(0.0, min_y), QPointF(0.0, bottom_y)
                )
                top_col = QColor(base_color)
                top_col.setAlpha(180)
                bottom_col = QColor(base_color)
                bottom_col.setAlpha(0)
                gradient.setColorAt(0.0, top_col)
                gradient.setColorAt(1.0, bottom_col)
            except Exception:
                gradient = None

            # Fallback flat fill if gradient creation fails for any reason.
            fill = QColor(base_color)
            try:
                fill.setAlpha(80)
            except Exception:
                pass

            painter.save()
            try:
                painter.setPen(Qt.PenStyle.NoPen)  # type: ignore[attr-defined]
            except Exception:
                try:
                    painter.setPen(Qt.NoPen)  # type: ignore[attr-defined]
                except Exception:
                    pass
            if gradient is not None:
                painter.setBrush(gradient)
            else:
                painter.setBrush(fill)
            try:
                painter.drawPath(path)
            except Exception:
                pass
            painter.restore()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        try:
            super().mouseMoveEvent(event)
        except Exception:
            pass

        if not self._month_keys or not self._tooltip_specs:
            return

        chart = None
        try:
            chart = self.chart()
        except Exception:
            chart = None
        if chart is None:
            return

        try:
            pos = event.position()  # type: ignore[attr-defined]
        except Exception:
            pos = event.pos()

        try:
            base_series = self._tooltip_specs[0][0]
            value_pt = chart.mapToValue(pos, base_series)  # type: ignore[arg-type]
            x_val = value_pt.x()
        except Exception:
            return

        if not self._month_keys:
            return
        idx = int(round(x_val))
        if idx < 0 or idx >= len(self._month_keys):
            return

        best_name: Optional[str] = None
        best_amount: Optional[float] = None
        best_dist2: Optional[float] = None

        for series, name, values in self._tooltip_specs:
            if idx < 0 or idx >= len(values):
                continue
            amount_val = float(values[idx])
            try:
                series_pos = chart.mapToPosition(
                    QPointF(float(idx), amount_val), series  # type: ignore[arg-type]
                )
            except Exception:
                continue
            dx = float(series_pos.x() - pos.x())
            dy = float(series_pos.y() - pos.y())
            dist2 = dx * dx + dy * dy
            if best_dist2 is None or dist2 < best_dist2:
                best_dist2 = dist2
                best_name = name
                best_amount = amount_val

        if best_name is None or best_amount is None:
            return

        year, month = self._month_keys[idx]
        if year > 0:
            month_label = f"{month:02d}/{year % 100:02d}"
        else:
            month_label = str(idx)

        text = f"{best_name}\n{month_label}: {self._format_amount(best_amount)}"
        try:
            QToolTip.showText(QCursor.pos(), text, self)
        except Exception:
            pass


def create_savings_history_chart_card(
    parent: QWidget,
    account: SavingsAccount,
    format_amount: Callable[[float], str],
) -> QWidget:
    """Create the bottom card with a smoothed line chart and shadow under each saving."""
    chart_card = QWidget(parent)
    chart_card.setObjectName("Sidebar")
    try:
        chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    except Exception:
        pass
    chart_layout = QVBoxLayout(chart_card)
    chart_layout.setContentsMargins(8, 8, 8, 8)
    chart_layout.setSpacing(8)

    if charts_available and account.savings:
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        # Build a global ordered list of (year, month) keys across all savings
        # histories so all lines share the same month positions.
        month_keys: List[tuple[int, int]] = []
        seen_months: set[tuple[int, int]] = set()
        for s in account.savings:
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

        # Track (series, color) so the custom view can paint shadows.
        shadow_specs: List[tuple[QLineSeries, QColor]] = []
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = []

        total_savings = max(1, len(account.savings))

        for idx, s in enumerate(account.savings):
            series = QLineSeries()
            series.setName(s.name)
            try:
                series.setPointsVisible(False)
            except Exception:
                pass

            # Group this savings' history by month and take the latest snapshot
            # amount within each month.
            latest_by_month: dict[tuple[int, int], MoneySnapshot] = {}
            for snap in s.history:
                dt = parse_iso_date(str(snap.date))
                key = (dt.year, dt.month)
                existing = latest_by_month.get(key)
                if existing is None:
                    latest_by_month[key] = snap
                else:
                    if parse_iso_date(str(existing.date)) < dt:
                        latest_by_month[key] = snap

            # Build a base value for every month in month_keys so each savings
            # line is continuous across the whole range. For months with no
            # data, we carry forward the last known amount (or 0 before the
            # first data point). Then we densify this sequence with an
            # interpolated smooth curve between the month samples so the drawn
            # line looks rounded rather than like a series of sharp corners.
            base_values: List[float] = []
            last_amount = 0.0
            if not latest_by_month:
                last_amount = float(s.amount)
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

            n_months = len(month_keys)
            if n_months == 1:
                series.append(0.0, base_values[0])
            else:
                # Slightly smooth the month-to-month knots using a small moving
                # average so the curve looks even more rounded, while still
                # staying very close to the real data.
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

                # Clamp the smoothed curve to the real data range of this
                # series so we don't overshoot wildly above or below.
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

            # Choose a distinct color per savings line.
            try:
                hue = int((360.0 * idx) / float(total_savings))
                base_color = QColor.fromHsl(hue, 180, 140)
            except Exception:
                base_color = QColor("#f97316")  # warm fallback

            # Style the visible line.
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

            shadow_specs.append((series, base_color))
            chart.addSeries(series)

            # Base month-by-month values for this savings so the custom chart
            # view can compute tooltips on mouse move.
            tooltip_specs.append((series, s.name, list(base_values)))

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

        # Theme-aware axis label colors: pure white in dark mode, dark navy in light.
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


