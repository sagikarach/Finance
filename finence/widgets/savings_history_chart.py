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
    QToolTip,
    QCursor,
    charts_available,
)
from ..models.accounts import SavingsAccount
from ..models.charts import (
    build_month_axis_from_histories,
    build_base_values,
    latest_snapshots_by_month,
    catmull_rom_spline_samples,
)


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

    def drawForeground(self, painter: QPainter, rect) -> None:
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
            try:
                pts = list(series.points())
            except Exception:
                try:
                    pts = list(series.pointsVector())
                except Exception:
                    pts = []
            if len(pts) < 2:
                continue

            path = QPainterPath()
            try:
                first_pos = chart.mapToPosition(pts[0], series)
            except Exception:
                continue
            path.moveTo(first_pos)
            last_pos = first_pos
            min_y = first_pos.y()

            for pt in pts[1:]:
                try:
                    pos = chart.mapToPosition(pt, series)
                except Exception:
                    continue
                path.lineTo(pos)
                last_pos = pos
                if pos.y() < min_y:
                    min_y = pos.y()

            try:
                path.lineTo(QPointF(last_pos.x(), bottom_y))
                path.lineTo(QPointF(first_pos.x(), bottom_y))
            except Exception:
                pass
            try:
                path.closeSubpath()
            except Exception:
                pass

            gradient = None
            try:
                gradient = QLinearGradient(QPointF(0.0, min_y), QPointF(0.0, bottom_y))
                top_col = QColor(base_color)
                top_col.setAlpha(180)
                bottom_col = QColor(base_color)
                bottom_col.setAlpha(0)
                gradient.setColorAt(0.0, top_col)
                gradient.setColorAt(1.0, bottom_col)
            except Exception:
                gradient = None

            fill = QColor(base_color)
            try:
                fill.setAlpha(80)
            except Exception:
                pass

            painter.save()
            try:
                painter.setPen(Qt.PenStyle.NoPen)
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

    def mouseMoveEvent(self, event) -> None:
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
            pos = event.position()
        except Exception:
            pos = event.pos()

        try:
            base_series = self._tooltip_specs[0][0]
            value_pt = chart.mapToValue(pos, base_series)
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
                    QPointF(float(idx), amount_val),
                    series,
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

        axis = build_month_axis_from_histories([s.history for s in account.savings])
        month_keys = axis.keys
        month_to_index = axis.month_to_index

        max_amount = 0.0

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

            latest_by_month = latest_snapshots_by_month(s.history)
            base_values, series_max = build_base_values(
                axis=axis,
                latest_by_month=latest_by_month,
                fallback_amount=s.amount,
            )
            if series_max > max_amount:
                max_amount = series_max

            samples = catmull_rom_spline_samples(base_values)
            for x_val, y_val in samples:
                series.append(x_val, y_val)

            try:
                hue = int((360.0 * idx) / float(total_savings))
                base_color = QColor.fromHsl(hue, 180, 140)
            except Exception:
                base_color = QColor("#f97316")

            try:
                pen = series.pen()
                pen.setColor(base_color)
                try:
                    pen.setWidthF(2.0)
                except Exception:
                    pass
                try:
                    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                except Exception:
                    pass
                series.setPen(pen)
            except Exception:
                pass

            shadow_specs.append((series, base_color))
            chart.addSeries(series)

            tooltip_specs.append((series, s.name, list(base_values)))

        axis_x = QCategoryAxis()
        for key in month_keys:
            year, month = key
            label = f"{month:02d}/{year % 100:02d}"
            axis_x.append(label, float(month_to_index[key]))
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        if max_amount > 0:
            top = float(math.ceil(max_amount / 1000.0) * 1000.0)
        else:
            top = 1000.0
        axis_y.setRange(0.0, top)
        try:
            axis_y.setTickInterval(1000.0)
        except Exception:
            pass
        try:
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except Exception:
            pass

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
                s_obj.attachAxis(axis_x)
                s_obj.attachAxis(axis_y)
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
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFrameShape(QFrame.Shape.NoFrame)
        chart_view.setStyleSheet("background: transparent;")
        chart_layout.addWidget(chart_view, 1)
    else:
        placeholder = QLabel("אין נתוני היסטוריה להצגה", chart_card)
        placeholder.setObjectName("Subtitle")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(placeholder, 1)

    return chart_card
