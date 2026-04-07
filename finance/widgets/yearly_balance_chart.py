from __future__ import annotations

from typing import List, Optional
import math

from ..qt import (
    QApplication,
    QColor,
    QChart,
    QCategoryAxis,
    QFont,
    QFrame,
    QLineSeries,
    QPainter,
    QValueAxis,
    QVBoxLayout,
    QWidget,
    Qt,
    charts_available,
)
from ..models.charts import catmull_rom_spline_samples
from ..utils.formatting import format_currency
from .savings_history_chart import ShadowChartView


class YearlyBalanceChart(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._view: Optional[ShadowChartView] = None

    def set_monthly_net(
        self,
        values: List[float],
        month_labels: List[str],
        *,
        proj_values: Optional[List[float]] = None,
        proj_labels: Optional[List[str]] = None,
    ) -> None:
        if not charts_available:
            return

        n = max(1, len(values))
        base_values = [float(v) for v in values[:n]]
        labels = list(month_labels[:n])
        if len(labels) < n:
            labels = labels + [""] * (n - len(labels))

        samples = [
            (float(x), float(y)) for x, y in catmull_rom_spline_samples(base_values)
        ]
        if not samples:
            samples = [(0.0, 0.0), (11.0, 0.0)]

        def sign(y: float) -> int:
            return 1 if y >= 0.0 else -1

        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        positive_color = QColor("#22c55e")
        negative_color = QColor("#ef4444")

        segments_pos: List[List[tuple[float, float]]] = []
        segments_neg: List[List[tuple[float, float]]] = []
        cur = [samples[0]]
        cur_sign = sign(samples[0][1])
        for x2, y2 in samples[1:]:
            x1, y1 = cur[-1]
            s2 = sign(y2)
            if s2 == cur_sign:
                cur.append((x2, y2))
                continue

            if y2 == y1:
                x_cross = x2
            else:
                t = (0.0 - y1) / (y2 - y1)
                x_cross = x1 + t * (x2 - x1)
            cur.append((float(x_cross), 0.0))
            if len(cur) >= 2:
                (segments_pos if cur_sign > 0 else segments_neg).append(cur)
            cur = [(float(x_cross), 0.0), (x2, y2)]
            cur_sign = s2
        if len(cur) >= 2:
            (segments_pos if cur_sign > 0 else segments_neg).append(cur)

        shadow_specs: List[tuple[QLineSeries, QColor]] = []

        def add_segment_series(
            points: List[tuple[float, float]], color: QColor
        ) -> None:
            if len(points) < 2:
                return
            s = QLineSeries()
            try:
                s.setPointsVisible(False)
            except Exception:
                pass
            for x_val, y_val in points:
                s.append(float(x_val), float(y_val))
            try:
                pen = s.pen()
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
                s.setPen(pen)
            except Exception:
                pass
            chart.addSeries(s)
            shadow_specs.append((s, QColor(color)))

        for seg in segments_pos:
            add_segment_series(seg, positive_color)
        for seg in segments_neg:
            add_segment_series(seg, negative_color)

        hit_series = QLineSeries()
        try:
            hit_series.setName("")
        except Exception:
            pass
        try:
            hit_series.setPointsVisible(False)
        except Exception:
            pass
        for i, y in enumerate(base_values):
            hit_series.append(float(i), float(y))
        try:
            pen = hit_series.pen()
            pen.setColor(QColor(0, 0, 0, 0))
            try:
                pen.setWidthF(0.1)
            except Exception:
                pass
            hit_series.setPen(pen)
        except Exception:
            pass
        chart.addSeries(hit_series)

        # ── projection dashed series ─────────────────────────────────────
        p_vals: List[float] = []
        p_labels: List[str] = []
        if proj_values:
            p = len(proj_values)
            p_vals = list(proj_values[:p])
            p_labels = list((proj_labels or [])[:p])
            if len(p_labels) < p:
                p_labels = p_labels + [""] * (p - len(p_labels))
            # proj series: starts at last actual value for smooth join
            all_proj = [base_values[-1]] + p_vals if base_values else p_vals
            from ..models.charts import catmull_rom_spline_samples as _crs

            proj_series = QLineSeries()
            try:
                proj_series.setPointsVisible(False)
            except Exception:
                pass
            try:
                pen = proj_series.pen()
                pen.setColor(QColor("#f59e0b"))
                try:
                    pen.setWidthF(2.0)
                    pen.setStyle(Qt.PenStyle.DashLine)
                except Exception:
                    pass
                proj_series.setPen(pen)
            except Exception:
                pass
            x_offset = float(n - 1)
            for x_val, y_val in _crs(all_proj):
                proj_series.append(x_val + x_offset, y_val)
            chart.addSeries(proj_series)

        # ── x-axis (actual + optional projection labels) ─────────────────
        all_labels = labels + p_labels
        total_n = n + len(p_labels)

        axis_x = QCategoryAxis()
        for i, label in enumerate(all_labels):
            axis_x.append(label, float(i))
        try:
            axis_x.setRange(0.0, float(total_n - 1))
        except Exception:
            pass
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        try:
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except Exception:
            pass

        y_min = min(base_values) if base_values else 0.0
        y_max = max(base_values) if base_values else 0.0
        y0_min, y0_max, tick = self._nice_y_axis_range(y_min, y_max)
        y0_min = min(y0_min, 0.0)
        y0_max = max(y0_max, 0.0)
        axis_y.setRange(y0_min, y0_max)
        try:
            axis_y.setTickType(QValueAxis.TickType.TicksDynamic)
            try:
                axis_y.setTickAnchor(0.0)
            except Exception:
                pass
            axis_y.setTickInterval(tick)
        except Exception:
            try:
                axis_y.setTickCount(max(2, int((y0_max - y0_min) / max(1.0, tick)) + 1))
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
        try:
            f = QFont()
            f.setPixelSize(11)
            axis_x.setLabelsFont(f)
            axis_y.setLabelsFont(f)
        except Exception:
            pass

        zero_line = QLineSeries()
        try:
            zero_line.setName("")
        except Exception:
            pass
        try:
            zero_line.setPointsVisible(False)
        except Exception:
            pass
        zero_line.append(0.0, 0.0)
        zero_line.append(float(total_n - 1), 0.0)
        try:
            app = QApplication.instance()
            is_dark = False
            if app is not None:
                is_dark = str(app.property("theme") or "light") == "dark"
            zero_col = QColor("#475569" if is_dark else "#d4eafc")
            if not is_dark:
                try:
                    zero_col.setAlpha(140)
                except Exception:
                    pass
            pen0 = zero_line.pen()
            pen0.setColor(zero_col)
            try:
                pen0.setWidthF(1.2)
            except Exception:
                pass
            try:
                pen0.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                pen0.setCapStyle(Qt.PenCapStyle.RoundCap)
            except Exception:
                pass
            zero_line.setPen(pen0)
        except Exception:
            pass
        chart.addSeries(zero_line)

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for s_obj in chart.series():
            try:
                if hasattr(chart, "setAxisX"):
                    chart.setAxisX(axis_x, s_obj)
                else:
                    s_obj.attachAxis(axis_x)
            except Exception:
                try:
                    s_obj.attachAxis(axis_x)
                except Exception:
                    pass
            try:
                if hasattr(chart, "setAxisY"):
                    chart.setAxisY(axis_y, s_obj)
                else:
                    s_obj.attachAxis(axis_y)
            except Exception:
                try:
                    s_obj.attachAxis(axis_y)
                except Exception:
                    pass

        month_keys: List[tuple[int, int]] = [(0, i + 1) for i in range(total_n)]
        tooltip_specs = [(hit_series, "יתרה", base_values)]
        view = ShadowChartView(
            chart,
            shadow_specs,
            month_keys,
            tooltip_specs,
            lambda v: format_currency(v, use_compact=True),
            self,
            x_labels=all_labels,
            baseline_value=0.0,
        )
        try:
            hint = None
            try:
                hint = QPainter.RenderHint.Antialiasing
            except Exception:
                hint = getattr(QPainter, "Antialiasing", None)
            if hint is not None:
                view.setRenderHint(hint, True)
        except Exception:
            pass
        try:
            frame_no = None
            try:
                frame_no = QFrame.Shape.NoFrame
            except Exception:
                frame_no = getattr(QFrame, "NoFrame", None)
            if frame_no is not None:
                view.setFrameShape(frame_no)
        except Exception:
            pass
        try:
            view.setStyleSheet("background: transparent;")
        except Exception:
            pass

        if self._view is not None:
            try:
                self._layout.removeWidget(self._view)
                self._view.setParent(None)
                self._view.deleteLater()
            except Exception:
                pass
        self._view = view
        self._layout.addWidget(view, 1)

    def _nice_y_axis_range(
        self, y_min: float, y_max: float
    ) -> tuple[float, float, float]:
        if not math.isfinite(y_min) or not math.isfinite(y_max):
            return (0.0, 1.0, 1.0)
        if y_min == y_max:
            if y_min == 0.0:
                return (-1000.0, 1000.0, 1000.0)
            pad = abs(y_min) * 0.25
            return (y_min - pad, y_max + pad, max(1.0, pad))

        span = y_max - y_min
        pad = span * 0.08
        lo = y_min - pad
        hi = y_max + pad
        approx_ticks = 5.0
        raw_step = abs(hi - lo) / max(1.0, approx_ticks)
        if raw_step <= 0.0 or not math.isfinite(raw_step):
            raw_step = 1.0
        pow10 = 10.0 ** math.floor(math.log10(raw_step))
        for mult in (1.0, 2.0, 5.0, 10.0):
            step = pow10 * mult
            if step >= raw_step:
                break
        else:
            step = pow10 * 10.0
        lo_n = math.floor(lo / step) * step
        hi_n = math.ceil(hi / step) * step
        if lo_n == hi_n:
            hi_n = lo_n + step
        return (float(lo_n), float(hi_n), float(step))
