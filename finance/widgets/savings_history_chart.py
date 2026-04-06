from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional

from ..qt import (
    QApplication,
    QColor,
    QCursor,
    QFrame,
    QLabel,
    QLinearGradient,
    QLineSeries,
    QPainter,
    QPainterPath,
    QPointF,
    Qt,
    QChart,
    QChartView,
    QCategoryAxis,
    QValueAxis,
    QToolTip,
    QVBoxLayout,
    QWidget,
    charts_available,
)
from ..models.accounts import MoneySnapshot, SavingsAccount
from ..models.charts import (
    build_base_values,
    catmull_rom_spline_samples,
    latest_snapshots_by_month_with_axis,
)
from .time_range_bar import TimeRangeBar


# ─────────────────────────────────────────────────────────────── helpers ──

def _label_color() -> QColor:
    color = QColor("#0f172a")
    app = QApplication.instance()
    if app is not None:
        try:
            if str(app.property("theme") or "light") == "dark":
                color = QColor("#ffffff")
        except Exception:
            pass
    return color


def _apply_line_pen(series: QLineSeries, color: QColor) -> None:
    try:
        pen = series.pen()
        pen.setColor(color)
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


def _build_x_axis(
    month_keys: List[tuple[int, int]],
    label_step: int,
) -> QCategoryAxis:
    """Build a QCategoryAxis with one label every *label_step* months."""
    axis = QCategoryAxis()
    n = len(month_keys)
    for i, (year, month) in enumerate(month_keys):
        if i % label_step == 0 or i == n - 1:
            axis.append(f"{month:02d}/{year % 100:02d}", float(i))
    try:
        axis.setGridLineVisible(False)
        axis.setMinorGridLineVisible(False)
    except Exception:
        pass
    return axis


def _build_y_axis(max_val: float, min_val: float = 0.0) -> QValueAxis:
    axis = QValueAxis()
    axis.setLabelFormat("%.0f")
    top = float(math.ceil(abs(max_val) / 1000.0) * 1000.0) or 1000.0
    bottom = float(-math.ceil(abs(min_val) / 1000.0) * 1000.0) if min_val < 0.0 else 0.0
    axis.setRange(bottom, top)
    try:
        axis.setTickInterval(max(1000.0, (top - bottom) / 5.0))
    except Exception:
        pass
    try:
        axis.setGridLineVisible(False)
        axis.setMinorGridLineVisible(False)
    except Exception:
        pass
    return axis


def _label_step_for(n_visible: int) -> int:
    """Return a label step that gives at most ~7 labels."""
    return max(1, (n_visible + 6) // 7)


# ──────────────────────────────────────────────────── ShadowChartView ──

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
        self._shadows = shadows
        self._month_keys = month_keys
        self._tooltip_specs = tooltip_specs
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
                path.closeSubpath()
            except Exception:
                pass

            gradient = None
            try:
                if baseline_val is None:
                    raise RuntimeError("no baseline")
                min_y_val = min(float(p.y()) for p in pts)
                max_y_val = max(float(p.y()) for p in pts)
                crosses = bool(min_y_val < float(baseline_val) < max_y_val)
                if crosses:
                    gradient = None
                elif max_y_val <= float(baseline_val):
                    # Series at/below baseline: fade from baseline downward
                    y0 = float(baseline_y)
                    y1 = float(max(max_y, baseline_y))
                    gradient = QLinearGradient(QPointF(0.0, y0), QPointF(0.0, y1))
                    c0, c1 = QColor(base_color), QColor(base_color)
                    c0.setAlpha(180); c1.setAlpha(0)
                    gradient.setColorAt(0.0, c0); gradient.setColorAt(1.0, c1)
                else:
                    # Series at/above baseline: fade from baseline upward
                    y0 = float(min(min_y, baseline_y))
                    y1 = float(baseline_y)
                    gradient = QLinearGradient(QPointF(0.0, y0), QPointF(0.0, y1))
                    c0, c1 = QColor(base_color), QColor(base_color)
                    c0.setAlpha(0); c1.setAlpha(180)
                    gradient.setColorAt(0.0, c0); gradient.setColorAt(1.0, c1)
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
            painter.setBrush(gradient if gradient is not None else fill)
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

        idx = int(round(x_val))
        if idx < 0 or idx >= len(self._month_keys):
            return

        best_name: Optional[str] = None
        best_amount: Optional[float] = None
        best_dist2: Optional[float] = None

        for series, name, values in self._tooltip_specs:
            if idx >= len(values):
                continue
            amount_val = float(values[idx])
            try:
                series_pos = chart.mapToPosition(QPointF(float(idx), amount_val), series)
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
            month_label = f"{month:02d}/{year % 100:02d}" if year > 0 else str(idx)

        try:
            QToolTip.showText(QCursor.pos(), f"{best_name}\n{month_label}: {self._format_amount(best_amount)}", self)
        except Exception:
            pass

    def mousePressEvent(self, event) -> None:
        try:
            super().mousePressEvent(event)
        except Exception:
            pass

        if self._on_series_clicked is None or not self._month_keys or not self._tooltip_specs:
            return

        chart = None
        try:
            chart = self.chart()
        except Exception:
            return
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
            for pt in pts:
                try:
                    sp = chart.mapToPosition(pt, series)
                except Exception:
                    continue
                dx = float(sp.x() - pos.x())
                dy = float(sp.y() - pos.y())
                dist2 = dx * dx + dy * dy
                if best_dist2 is None or dist2 < best_dist2:
                    best_dist2 = dist2
                    best_name = name

        if best_name is None or best_dist2 is None:
            return
        if float(best_dist2) > float(self._click_threshold2):
            return
        try:
            self._on_series_clicked(best_name)
        except Exception:
            pass


# ──────────────────────────────────────────── SavingsHistoryChartCard ──

class SavingsHistoryChartCard(QWidget):
    """
    Chart card for a SavingsAccount's sub-account history lines.

    Includes a TimeRangeBar (3M / 6M / 1Y / 2Y / הכל).
    On each range change the series and axes are rebuilt for the visible slice
    with a smart label density, preventing truncation and fill glitches.
    """

    def __init__(
        self,
        parent: QWidget,
        account: SavingsAccount,
        format_amount: Callable[[float], str],
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._chart: Optional[QChart] = None
        self._chart_view: Optional[ShadowChartView] = None
        self._all_month_keys: List[tuple[int, int]] = []
        # list of (name, full_base_values, color)
        self._all_series_data: List[tuple[str, List[float], QColor]] = []
        self._format_amount = format_amount

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        if not (charts_available and account.savings):
            placeholder = QLabel("אין נתוני היסטוריה להצגה", self)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder, 1)
            return

        # ── pre-compute all data ──────────────────────────────────────────
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

        axis_keys.sort()
        if not axis_keys:
            axis_keys = [(0, 1)]

        axis_obj = type(
            "_Ax", (),
            {"keys": axis_keys, "month_to_index": {k: i for i, k in enumerate(axis_keys)}},
        )()
        self._all_month_keys = list(axis_keys)

        total_savings = max(1, len(account.savings))
        for idx, s in enumerate(account.savings):
            latest = latest_by_saving.get(str(s.name), {}) or {}
            base_values, _ = build_base_values(
                axis=axis_obj, latest_by_month=latest, fallback_amount=s.amount
            )
            try:
                hue = int((360.0 * idx) / float(total_savings))
                color = QColor.fromHsl(hue, 180, 140)
            except Exception:
                color = QColor("#f97316")
            self._all_series_data.append((str(s.name), list(base_values), color))

        # ── create chart + view (initially empty) ────────────────────────
        chart = QChart()
        try:
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        except Exception:
            pass
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)
        self._chart = chart

        chart_view = ShadowChartView(chart, [], [], [], format_amount, self)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFrameShape(QFrame.Shape.NoFrame)
        chart_view.setStyleSheet("background: transparent;")
        self._chart_view = chart_view

        # ── range bar ─────────────────────────────────────────────────────
        n = len(self._all_month_keys)
        default_months = 12 if n > 12 else 0
        range_bar = TimeRangeBar(self, default_months=default_months)
        range_bar.range_changed.connect(self._apply_range)
        layout.addWidget(range_bar)
        layout.addWidget(chart_view, 1)

        # populate with the initial range
        self._apply_range(default_months)

    # ------------------------------------------------------------------ range

    def _apply_range(self, months: int) -> None:
        if self._chart is None or self._chart_view is None:
            return
        n = len(self._all_month_keys)
        if n == 0:
            return

        first_idx = max(0, n - months) if 0 < months < n else 0
        visible_keys = self._all_month_keys[first_idx:]
        n_vis = len(visible_keys)
        if n_vis == 0:
            return

        # ── clear old content ────────────────────────────────────────────
        try:
            self._chart.removeAllSeries()
        except Exception:
            for s in list(self._chart.series()):
                try:
                    self._chart.removeSeries(s)
                except Exception:
                    pass
        for ax in list(self._chart.axes()):
            try:
                self._chart.removeAxis(ax)
            except Exception:
                pass

        # ── rebuild series ───────────────────────────────────────────────
        label_step = _label_step_for(n_vis)
        shadow_specs: List[tuple[QLineSeries, QColor]] = []
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = []
        max_v = 0.0

        for name, all_vals, color in self._all_series_data:
            vals = list(all_vals[first_idx:])
            if not vals:
                continue
            seg_max = max(vals)
            if seg_max > max_v:
                max_v = seg_max

            series = QLineSeries()
            series.setName(name)
            try:
                series.setPointsVisible(False)
            except Exception:
                pass
            _apply_line_pen(series, color)
            for x_val, y_val in catmull_rom_spline_samples(vals):
                series.append(x_val, y_val)

            self._chart.addSeries(series)
            shadow_specs.append((series, color))
            tooltip_specs.append((series, name, vals))

        # ── rebuild axes ─────────────────────────────────────────────────
        axis_x = _build_x_axis(visible_keys, label_step)
        axis_y = _build_y_axis(max_v if max_v > 0 else 1000.0)
        lc = _label_color()
        try:
            axis_x.setLabelsBrush(lc)
            axis_y.setLabelsBrush(lc)
        except Exception:
            pass

        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for s_obj in self._chart.series():
            try:
                s_obj.attachAxis(axis_x)
                s_obj.attachAxis(axis_y)
            except Exception:
                pass

        # ── update chart_view internals ──────────────────────────────────
        self._chart_view._shadows = shadow_specs
        self._chart_view._tooltip_specs = tooltip_specs
        self._chart_view._month_keys = list(visible_keys)
        self._chart_view._x_labels = [f"{m:02d}/{y % 100:02d}" for y, m in visible_keys]


def create_savings_history_chart_card(
    parent: QWidget,
    account: SavingsAccount,
    format_amount: Callable[[float], str],
) -> QWidget:
    """Backward-compatible factory — returns a SavingsHistoryChartCard."""
    return SavingsHistoryChartCard(parent, account, format_amount)
