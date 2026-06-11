from __future__ import annotations

import math
from typing import List, Optional, Tuple

from ..qt import (
    QApplication,
    QColor,
    QFrame,
    QLabel,
    QPainter,
    Qt,
    QVBoxLayout,
    QWidget,
    charts_available,
)
from ..models.mortgage import Mortgage
from ..models.mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    months_between,
    outstanding_projection,
)

if charts_available:
    from ..qt import (
        QChart,
        QChartView,
        QLineSeries,
        QValueAxis,
        QCategoryAxis,
    )


_LINE_COLOR = "#6366f1"  # אינדיגו — עקומת היתרה
_TODAY_COLOR = "#f59e0b"  # ענבר — קו "היום"


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


def _month_keys_from(start_date: str, count: int) -> List[Tuple[int, int]]:
    """רשימת (שנה, חודש) החל מ-``start_date`` באורך ``count``."""
    from ..models.accounts import parse_iso_date

    dt = parse_iso_date(str(start_date or "").strip())
    y, m = int(dt.year), int(dt.month)
    keys: List[Tuple[int, int]] = []
    for _ in range(max(0, count)):
        keys.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return keys


def _label_step_for(n: int) -> int:
    return max(1, (n + 6) // 7)


class MortgageBalanceChart(QWidget):
    """גרף ירידת יתרת הקרן לאורך חיי המשכנתא (תחזית דטרמיניסטית)."""

    def __init__(
        self,
        mortgage: Optional[Mortgage] = None,
        *,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._assumptions = assumptions
        self._chart = None
        self._chart_view = None
        self._placeholder: Optional[QLabel] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        self._layout = layout

        if not charts_available:
            self._placeholder = QLabel("גרפים אינם זמינים בסביבה זו", self)
            try:
                self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                pass
            layout.addWidget(self._placeholder)
            return

        chart = QChart()
        try:
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        except Exception:
            pass
        try:
            chart.legend().setVisible(False)
            chart.setBackgroundRoundness(0)
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
            chart.setPlotAreaBackgroundVisible(False)
        except Exception:
            pass
        self._chart = chart

        chart_view = QChartView(chart, self)
        try:
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setFrameShape(QFrame.Shape.NoFrame)
            chart_view.setStyleSheet("background: transparent;")
        except Exception:
            pass
        self._chart_view = chart_view
        layout.addWidget(chart_view, 1)

        self.set_mortgage(mortgage)

    def set_mortgage(self, mortgage: Optional[Mortgage]) -> None:
        if not charts_available or self._chart is None:
            return

        # נקה סדרות וצירים קיימים.
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

        if mortgage is None or not mortgage.tracks:
            return

        total_months = max((int(t.term_months) for t in mortgage.tracks), default=0)
        if total_months <= 0:
            return

        points = outstanding_projection(
            mortgage, months=total_months, step=1, assumptions=self._assumptions
        )
        if not points:
            return

        values = [p.outstanding for p in points]
        n = len(values)
        max_val = max(values) if values else 0.0

        series = QLineSeries()
        try:
            pen = series.pen()
            pen.setColor(QColor(_LINE_COLOR))
            pen.setWidthF(2.5)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            series.setPen(pen)
        except Exception:
            pass
        for i, v in enumerate(values):
            series.append(float(i), float(v))
        self._chart.addSeries(series)

        # ציר X — תוויות חודש/שנה בכל ~7 נקודות.
        month_keys = _month_keys_from(mortgage.start_date, n)
        axis_x = QCategoryAxis()
        step = _label_step_for(n)
        for i, (year, month) in enumerate(month_keys):
            if i % step == 0 or i == n - 1:
                try:
                    axis_x.append(f"{month:02d}/{year % 100:02d}", float(i))
                except Exception:
                    pass
        try:
            axis_x.setRange(0.0, float(max(1, n - 1)))
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        try:
            axis_y.setLabelFormat("%.0f")
            top = float(math.ceil(abs(max_val) / 1000.0) * 1000.0) or 1000.0
            axis_y.setRange(0.0, top)
            axis_y.setTickInterval(max(1000.0, top / 5.0))
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except Exception:
            pass

        lc = _label_color()
        try:
            axis_x.setLabelsColor(lc)
            axis_y.setLabelsColor(lc)
        except Exception:
            pass

        try:
            self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        except Exception:
            pass

        # קו אנכי מקווקו במיקום "היום" (אם בתוך טווח הזמן).
        elapsed = months_between(mortgage.start_date, None)
        if 0 < elapsed < n:
            today_series = QLineSeries()
            try:
                pen = today_series.pen()
                pen.setColor(QColor(_TODAY_COLOR))
                pen.setWidthF(1.5)
                pen.setStyle(Qt.PenStyle.DashLine)
                today_series.setPen(pen)
            except Exception:
                pass
            today_series.append(float(elapsed), 0.0)
            today_series.append(float(elapsed), float(max_val))
            self._chart.addSeries(today_series)
            try:
                today_series.attachAxis(axis_x)
                today_series.attachAxis(axis_y)
            except Exception:
                pass

    def refresh_theme(self) -> None:
        """החל מחדש את צבעי התוויות לאחר החלפת ערכת נושא."""
        if not charts_available or self._chart is None:
            return
        lc = _label_color()
        for ax in list(self._chart.axes()):
            try:
                ax.setLabelsColor(lc)
            except Exception:
                pass
