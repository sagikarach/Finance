from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional

from ..models.accounts import parse_iso_date
from ..qt import (
    QApplication,
    QCategoryAxis,
    QChart,
    QColor,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineSeries,
    QMarginsF,
    QPainter,
    QPen,
    QValueAxis,
    QVBoxLayout,
    Qt,
    QWidget,
    charts_available,
)
from ..utils.formatting import format_currency
from .savings_history_chart import ShadowChartView
from .time_range_bar import TimeRangeBar


@dataclass(frozen=True)
class ExpensePoint:
    date_iso: str
    amount: float


class OneTimeEventExpensesOverTimeChart(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._view: Optional[ShadowChartView] = None
        self._axis_x: Optional[QCategoryAxis] = None
        self._axis_y: Optional[QValueAxis] = None
        self._all_values: List[float] = []      # cumulative values for all days
        self._all_labels: List[str] = []        # date labels for all days
        self._range_bar: Optional[TimeRangeBar] = None

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(4)

    def clear(self) -> None:
        self._clear_layout()

    def set_expenses(self, expenses: List[ExpensePoint]) -> None:
        self._clear_layout()

        if not charts_available:
            self._root.addWidget(
                self._placeholder(
                    "גרפים אינם זמינים. נדרשת התקנת QtCharts."
                ),
                1,
            )
            return

        if not expenses:
            self._root.addWidget(self._placeholder("אין הוצאות להצגה"), 1)
            return

        try:
            expenses = sorted(expenses, key=lambda p: parse_iso_date(p.date_iso))
        except Exception:
            pass

        try:
            start_dt = parse_iso_date(expenses[0].date_iso).date()
            end_dt = parse_iso_date(expenses[-1].date_iso).date()
        except Exception:
            self._root.addWidget(self._placeholder("אין הוצאות להצגה"), 1)
            return

        day_sum: Dict[str, float] = {}
        for p in expenses:
            try:
                d = parse_iso_date(p.date_iso).date().isoformat()
            except Exception:
                continue
            day_sum[d] = float(day_sum.get(d, 0.0) + float(p.amount))

        labels: List[str] = []
        values: List[float] = []
        series = QLineSeries()
        try:
            series.setName("הוצאות")
        except Exception:
            pass

        cum = 0.0
        idx = 0
        dcur = start_dt
        while dcur <= end_dt:
            key = dcur.isoformat()
            cum += float(day_sum.get(key, 0.0))
            labels.append(dcur.strftime("%d/%m/%y"))
            values.append(float(cum))
            try:
                series.append(float(idx), float(cum))
            except Exception:
                pass
            idx += 1
            dcur = dcur + timedelta(days=1)

        if not values:
            self._root.addWidget(self._placeholder("אין הוצאות להצגה"), 1)
            return

        # Store full data for range filtering
        self._all_values = list(values)
        self._all_labels = list(labels)

        line_color = QColor("#ef4444")
        try:
            pen = QPen(line_color)
            pen.setWidthF(3.0)
            series.setPen(pen)
        except Exception:
            pass

        chart = QChart()
        chart.addSeries(series)
        try:
            chart.legend().setVisible(False)
        except Exception:
            pass
        try:
            chart.setMargins(QMarginsF(0, 0, 0, 0))
        except Exception:
            pass
        try:
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            chart.setTitle("")
        except Exception:
            pass

        axis_x = QCategoryAxis()
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass
        try:
            axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        except Exception:
            pass

        n = len(values)
        tick_count = min(6, n)
        indices: List[int] = []
        if tick_count <= 2:
            indices = [0, n - 1] if n > 1 else [0]
        else:
            for i in range(tick_count):
                indices.append(int(round(i * (n - 1) / float(tick_count - 1))))
            indices = sorted(set(indices))
        for i in indices:
            if 0 <= i < len(labels):
                try:
                    axis_x.append(str(labels[i]), float(i))
                except Exception:
                    pass
        try:
            axis_x.setRange(0.0, float(max(0, n - 1)))
        except Exception:
            pass

        axis_y = QValueAxis()
        try:
            axis_y.setLabelFormat("%.0f")
        except Exception:
            pass
        max_val = max(values) if values else 0.0
        top, tick = self._nice_y_axis(max_val)
        axis_y.setRange(0.0, float(top))
        try:
            axis_y.setTickInterval(float(tick))
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
        try:
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        except Exception:
            pass

        self._axis_x = axis_x
        self._axis_y = axis_y

        month_keys = [(0, i) for i in range(len(values))]
        tooltip_specs = [(series, "הוצאות מצטברות", values)]
        view = ShadowChartView(
            chart,
            [(series, line_color)],
            month_keys,
            tooltip_specs,
            lambda v: format_currency(float(v), use_compact=True),
            self,
            x_labels=labels,
            baseline_value=0.0,
        )
        try:
            view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        except Exception:
            try:
                hint = getattr(QPainter, "Antialiasing", None)
                if hint is not None:
                    view.setRenderHint(hint, True)
            except Exception:
                pass
        try:
            view.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass
        try:
            view.setStyleSheet("background: transparent;")
        except Exception:
            pass

        self._view = view

        # TimeRangeBar — shown only when there are enough days to be useful
        # Here presets represent months (converted to days for filtering)
        if n > 30:
            default_months = 12 if n > 365 else 0
            range_bar = TimeRangeBar(self, default_months=default_months)
            range_bar.range_changed.connect(self._apply_range)
            self._range_bar = range_bar
            self._root.addWidget(range_bar)
            self._root.addWidget(view, 1)
            self._apply_range(default_months)
        else:
            self._root.addWidget(view, 1)

    def _apply_range(self, months: int) -> None:
        """Zoom x-axis to the last *months* months worth of days (0 = all)."""
        if self._axis_x is None or self._axis_y is None:
            return
        n = len(self._all_values)
        if n == 0:
            return

        # Convert months → days for the daily series
        days = months * 30 if months > 0 else 0
        if days == 0 or days >= n:
            first_idx = 0
        else:
            first_idx = max(0, n - days)

        try:
            self._axis_x.setRange(float(first_idx), float(n - 1))
        except Exception:
            pass

        visible = self._all_values[first_idx:]
        max_val = max(visible) if visible else 0.0
        top, tick = self._nice_y_axis(max_val)
        # Y starts at the value at first_idx (cumulative, never decreases)
        y_min = float(self._all_values[first_idx]) if self._all_values else 0.0
        y_min = max(0.0, y_min - (top - y_min) * 0.05)  # small padding below
        try:
            self._axis_y.setRange(y_min, float(top))
            self._axis_y.setTickInterval(float(tick))
        except Exception:
            pass

    @staticmethod
    def _placeholder(text: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(text, w)
        lbl.setObjectName("Subtitle")
        try:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
        lay.addWidget(lbl, 1)
        return w

    def _clear_layout(self) -> None:
        try:
            while self._root.count():
                item = self._root.takeAt(0)
                w = item.widget() if item is not None else None
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
        except Exception:
            pass
        self._view = None
        self._axis_x = None
        self._axis_y = None
        self._all_values = []
        self._all_labels = []
        self._range_bar = None

    @staticmethod
    def _nice_y_axis(max_val: float) -> tuple[float, float]:
        try:
            v = float(max_val)
        except Exception:
            return 100.0, 25.0
        if v <= 0:
            return 100.0, 25.0
        import math

        exp = 10 ** int(math.floor(math.log10(v)))
        for mult in (1, 2, 5, 10):
            top = float(mult * exp)
            if top >= v:
                tick = float(top / 4.0)
                if tick <= 0:
                    tick = float(top)
                return float(top), float(tick)
        top = float(10 * exp)
        return top, float(top / 4.0)
