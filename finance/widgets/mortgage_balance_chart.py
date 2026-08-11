from __future__ import annotations

from .chart_utils import label_color as _label_color, month_keys_from as _month_keys_from, label_step_for as _label_step_for

import math
from typing import List, Optional, Tuple

from ..qt import (
    QApplication,
    QColor,
    QFont,
    QFrame,
    QLabel,
    QPainter,
    QPen,
    QPointF,
    Qt,
    QVBoxLayout,
    QWidget,
    charts_available,
)
from ..models.mortgage import Mortgage
from ..models.mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    months_after,
    months_between,
    outstanding_projection,
    track_end_milestones,
)
from ..utils.safe import QT_ERRORS

if charts_available:
    from ..qt import (
        QChart,
        QChartView,
        QLineSeries,
        QValueAxis,
        QCategoryAxis,
    )


class _MilestoneChartView(QChartView if charts_available else object):  # type: ignore
    """QChartView שמצייר בעצמו את אבני-הדרך: קו אנכי מקווקו בכל סיום מסלול,
    ותווית מעוגנת בדיוק לאותו קו (QtCharts לא מספק אנוטציות, לכן מציירים ב-
    ``drawForeground`` באמצעות ``mapToPosition`` — כמו ב-savings_history_chart)."""

    def __init__(self, chart: "QChart", parent: Optional[QWidget] = None) -> None:
        super().__init__(chart, parent)
        self._milestones: List[Tuple[int, str]] = []  # (period, label)
        self._series = None  # סדרת היתרה — לעיגון מיקום דרך mapToPosition

    def set_milestones(self, milestones: List[Tuple[int, str]], series) -> None:
        self._milestones = list(milestones)
        self._series = series
        try:
            self.update()
        except QT_ERRORS:
            pass

    def drawForeground(self, painter: "QPainter", rect) -> None:  # noqa: N802
        try:
            super().drawForeground(painter, rect)
        except QT_ERRORS:
            pass
        chart = self.chart()
        if chart is None or self._series is None or not self._milestones:
            return
        try:
            plot = chart.plotArea()
        except QT_ERRORS:
            return

        is_dark = False
        app = QApplication.instance()
        if app is not None:
            try:
                is_dark = str(app.property("theme") or "light") == "dark"
            except QT_ERRORS:
                is_dark = False
        text_color = QColor("#e2e8f0" if is_dark else "#334155")
        chip = QColor(17, 24, 39, 205) if is_dark else QColor(255, 255, 255, 215)
        line_color = QColor(_MILESTONE_COLOR)

        painter.save()
        font = QFont(painter.font())
        font.setPointSizeF(8.5)
        painter.setFont(font)
        fm = painter.fontMetrics()
        line_h = fm.height()

        ordered = sorted(self._milestones, key=lambda mp: mp[0])
        for i, (period, text) in enumerate(ordered):
            try:
                x = chart.mapToPosition(
                    QPointF(float(period), 0.0), self._series
                ).x()
            except QT_ERRORS:
                continue
            if x < plot.left() - 1 or x > plot.right() + 1:
                continue
            # קו אנכי מקווקו לכל גובה אזור הגרף.
            pen = QPen(line_color)
            pen.setStyle(Qt.PenStyle.DotLine)
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.drawLine(
                int(x), int(plot.top()), int(x), int(plot.bottom())
            )
            # תווית מעוגנת לקו, בשכבות מתחלפות כדי שלא תתנגש עם שכנתה.
            tw = fm.horizontalAdvance(text)
            ty = plot.top() + 3 + (i % 2) * (line_h + 3)
            tx = x - 5 - tw  # RTL: הטקסט משמאל לקו
            if tx < plot.left() + 2:
                tx = x + 5  # אם גולש שמאלה — הפוך לימין הקו
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(chip)
            painter.drawRoundedRect(
                int(tx) - 3, int(ty) - 1, tw + 6, line_h + 2, 3, 3
            )
            painter.setPen(text_color)
            painter.drawText(int(tx), int(ty) + fm.ascent(), text)
        painter.restore()


_LINE_COLOR = "#6366f1"  # אינדיגו — עקומת היתרה
_TODAY_COLOR = "#f59e0b"  # ענבר — קו "היום"
_MILESTONE_COLOR = "#94a3b8"  # אפור — סיום מסלול (התשלום יורד)


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
        self._mortgage: Optional[Mortgage] = mortgage
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
            except QT_ERRORS:
                pass
            layout.addWidget(self._placeholder)
            return

        chart = QChart()
        try:
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        except QT_ERRORS:
            pass
        try:
            chart.legend().setVisible(False)
            chart.setBackgroundRoundness(0)
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
            chart.setPlotAreaBackgroundVisible(False)
        except QT_ERRORS:
            pass
        self._chart = chart

        chart_view = _MilestoneChartView(chart, self)
        try:
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setFrameShape(QFrame.Shape.NoFrame)
            chart_view.setStyleSheet("background: transparent;")
        except QT_ERRORS:
            pass
        self._chart_view = chart_view
        layout.addWidget(chart_view, 1)

        self.set_mortgage(mortgage)

    def set_assumptions(self, assumptions: MortgageAssumptions) -> None:
        """עדכן את ההנחות ורענן את הגרף (משמש בעת שינוי פריים/מדד)."""
        self._assumptions = assumptions
        self.set_mortgage(self._mortgage)

    def set_mortgage(self, mortgage: Optional[Mortgage]) -> None:
        self._mortgage = mortgage
        if not charts_available or self._chart is None:
            return

        # נקה סדרות וצירים קיימים.
        try:
            self._chart.removeAllSeries()
        except QT_ERRORS:
            for s in list(self._chart.series()):
                try:
                    self._chart.removeSeries(s)
                except QT_ERRORS:
                    pass
        for ax in list(self._chart.axes()):
            try:
                self._chart.removeAxis(ax)
            except QT_ERRORS:
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
        except QT_ERRORS:
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
                except QT_ERRORS:
                    pass
        try:
            axis_x.setRange(0.0, float(max(1, n - 1)))
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except QT_ERRORS:
            pass

        axis_y = QValueAxis()
        try:
            axis_y.setLabelFormat("%.0f")
            top = float(math.ceil(abs(max_val) / 1000.0) * 1000.0) or 1000.0
            axis_y.setRange(0.0, top)
            axis_y.setTickInterval(max(1000.0, top / 5.0))
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except QT_ERRORS:
            pass

        lc = _label_color()
        try:
            axis_x.setLabelsColor(lc)
            axis_y.setLabelsColor(lc)
        except QT_ERRORS:
            pass

        try:
            self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        except QT_ERRORS:
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
            except QT_ERRORS:
                pass
            today_series.append(float(elapsed), 0.0)
            today_series.append(float(elapsed), float(max_val))
            self._chart.addSeries(today_series)
            try:
                today_series.attachAxis(axis_x)
                today_series.attachAxis(axis_y)
            except QT_ERRORS:
                pass

        # אבני-דרך: מסלולים שנגמרים מאוחדים לפי חודש; מציירים ידנית ב-
        # drawForeground (קו + תווית מעוגנת) כי QtCharts לא מספק אנוטציות.
        by_period: dict = {}
        for ms in track_end_milestones(mortgage, self._assumptions):
            if not (0 < ms.period <= n):
                continue
            by_period.setdefault(ms.period, []).append(ms.track_name)

        milestones: List[Tuple[int, str]] = []
        for period, names in by_period.items():
            ym = months_after(mortgage.start_date, period)
            when = f"{ym[1]:02d}/{ym[0] % 100:02d}" if ym else f"#{period}"
            milestones.append((int(period), f"{when} · סיום {' + '.join(names)}"))
        if isinstance(self._chart_view, _MilestoneChartView):
            self._chart_view.set_milestones(milestones, series)

    def refresh_theme(self) -> None:
        """החל מחדש את צבעי התוויות לאחר החלפת ערכת נושא."""
        if not charts_available or self._chart is None:
            return
        lc = _label_color()
        for ax in list(self._chart.axes()):
            try:
                ax.setLabelsColor(lc)
            except QT_ERRORS:
                pass
