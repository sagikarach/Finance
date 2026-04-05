from __future__ import annotations

from typing import Callable, Dict, List, Optional
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
from ..models.accounts import MoneySnapshot, SavingsAccount
from ..models.charts import (
    build_base_values,
    latest_snapshots_by_month_with_axis,
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
        *,
        x_labels: Optional[List[str]] = None,
        on_series_clicked: Optional[Callable[[str], None]] = None,
        click_threshold_px: int = 26,
        baseline_value: Optional[float] = None,
    ) -> None:
        super().__init__(chart, parent)
        self._shadows: List[tuple[QLineSeries, QColor]] = shadows
        self._month_keys: List[tuple[int, int]] = month_keys
        self._tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = tooltip_specs
        self._format_amount = format_amount
        self._x_labels: Optional[List[str]] = x_labels
        self._on_series_clicked = on_series_clicked
        self._click_threshold2 = int(click_threshold_px) * int(click_threshold_px)
        self._baseline_value: Optional[float] = baseline_value
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
            max_y = first_pos.y()
            baseline_y = bottom_y
            baseline_val = self._baseline_value
            if baseline_val is not None:
                try:
                    baseline_y = chart.mapToPosition(
                        QPointF(float(pts[0].x()), float(baseline_val)), series
                    ).y()
                except Exception:
                    baseline_y = bottom_y

            for pt in pts[1:]:
                try:
                    pos = chart.mapToPosition(pt, series)
                except Exception:
                    continue
                path.lineTo(pos)
                last_pos = pos
                if pos.y() < min_y:
                    min_y = pos.y()
                if pos.y() > max_y:
                    max_y = pos.y()

            try:
                path.lineTo(QPointF(last_pos.x(), baseline_y))
                path.lineTo(QPointF(first_pos.x(), baseline_y))
            except Exception:
                pass
            try:
                path.closeSubpath()
            except Exception:
                pass

            gradient = None
            try:
                if baseline_val is None:
                    raise RuntimeError("no baseline")

                min_y_val = min(float(p.y()) for p in pts)
                max_y_val = max(float(p.y()) for p in pts)

                # Anchor the fill to the baseline line (not the chart bottom).
                # If the series crosses the baseline, fall back to a solid fill.
                crosses = bool(min_y_val < float(baseline_val) < max_y_val)
                if crosses:
                    gradient = None
                elif max_y_val <= float(baseline_val):
                    # Entire series at/below baseline: fade from baseline -> downwards.
                    y0 = float(baseline_y)
                    y1 = float(max(max_y, baseline_y))
                    gradient = QLinearGradient(QPointF(0.0, y0), QPointF(0.0, y1))
                    c0 = QColor(base_color)
                    c1 = QColor(base_color)
                    c0.setAlpha(180)
                    c1.setAlpha(0)
                    gradient.setColorAt(0.0, c0)
                    gradient.setColorAt(1.0, c1)
                else:
                    # Entire series at/above baseline: fade from baseline -> upwards.
                    y0 = float(min(min_y, baseline_y))
                    y1 = float(baseline_y)
                    gradient = QLinearGradient(QPointF(0.0, y0), QPointF(0.0, y1))
                    c0 = QColor(base_color)
                    c1 = QColor(base_color)
                    c0.setAlpha(0)
                    c1.setAlpha(180)
                    gradient.setColorAt(0.0, c0)
                    gradient.setColorAt(1.0, c1)
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
                no_pen = getattr(Qt, "NoPen", None)
                if no_pen is not None:
                    try:
                        painter.setPen(no_pen)
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

        month_label = None
        if self._x_labels is not None and idx < len(self._x_labels):
            month_label = str(self._x_labels[idx])
        if month_label is None:
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

    def mousePressEvent(self, event) -> None:
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

        if self._on_series_clicked is None:
            return
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

        best_name: Optional[str] = None
        best_dist2: Optional[float] = None

        for series, name, _values in self._tooltip_specs:
            pts = []
            try:
                pts = list(series.points())
            except Exception:
                try:
                    pts = list(series.pointsVector())
                except Exception:
                    pts = []
            if not pts:
                continue

            for pt in pts:
                try:
                    series_pos = chart.mapToPosition(pt, series)
                except Exception:
                    continue
                dx = float(series_pos.x() - pos.x())
                dy = float(series_pos.y() - pos.y())
                dist2 = dx * dx + dy * dy
                if best_dist2 is None or dist2 < best_dist2:
                    best_dist2 = dist2
                    best_name = name
                    if best_dist2 <= float(self._click_threshold2) * 0.25:
                        break

        if best_name is None or best_dist2 is None:
            return
        if float(best_dist2) > float(self._click_threshold2):
            return

        try:
            self._on_series_clicked(best_name)
        except Exception:
            pass


def create_savings_history_chart_card(
    parent: QWidget,
    account: SavingsAccount,
    format_amount: Callable[[float], str],
) -> QWidget:
    chart_card = QWidget(parent)
    chart_card.setObjectName("ContentPanel")
    try:
        chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    except Exception:
        pass
    chart_layout = QVBoxLayout(chart_card)
    chart_layout.setContentsMargins(8, 8, 8, 8)
    chart_layout.setSpacing(8)

    if charts_available and account.savings:
        chart = QChart()
        # Animations are pretty but expensive on large histories; disable for snappy navigation.
        try:
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        except Exception:
            try:
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            except Exception:
                pass
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        # One pass per saving: build latest-per-month and collect axis keys, without scanning history twice.
        axis_seen: set[tuple[int, int]] = set()
        axis_keys: List[tuple[int, int]] = []
        latest_by_saving: Dict[str, Dict[tuple[int, int], MoneySnapshot]] = {}
        for s in account.savings:
            try:
                axis_s, latest = latest_snapshots_by_month_with_axis(s.history)
                latest_by_saving[str(s.name)] = latest
                for k in axis_s.keys:
                    if k not in axis_seen:
                        axis_seen.add(k)
                        axis_keys.append(k)
            except Exception:
                latest_by_saving[str(getattr(s, "name", "") or "")] = {}
                continue
        axis_keys.sort(key=lambda k: (k[0], k[1]))
        if not axis_keys:
            axis_keys = [(0, 1)]
        axis = type(
            "MonthAxisTmp",
            (),
            {
                "keys": axis_keys,
                "month_to_index": {k: i for i, k in enumerate(axis_keys)},
            },
        )()
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

            latest_by_month = latest_by_saving.get(str(s.name), {}) or {}
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
