from __future__ import annotations

from .donut_utils import PASTEL_HEX

from typing import Dict, Optional

from ..qt import (
    QChart,
    QChartView,
    QColor,
    QCursor,
    QFrame,
    QLegend,
    QMarginsF,
    QPainter,
    QPieSeries,
    QToolTip,
    Qt,
    QWidget,
    QVBoxLayout,
    charts_available,
)
from ..utils.formatting import format_currency
from ..utils.safe import QT_ERRORS


class OneTimeEventPieChart(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._view: Optional[QChartView] = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        if not charts_available:
            return

        self._view = QChartView(self)
        try:
            self._view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        except QT_ERRORS:
            try:
                hint = getattr(QPainter, "Antialiasing", None)
                if hint is not None:
                    self._view.setRenderHint(hint, True)
            except QT_ERRORS:
                pass
        try:
            self._view.setStyleSheet("background: transparent;")
        except QT_ERRORS:
            pass
        try:
            self._view.setFrameShape(QFrame.Shape.NoFrame)
        except QT_ERRORS:
            pass
        try:
            self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        except QT_ERRORS:
            pass

        lay.addWidget(self._view, 1)

    def clear(self) -> None:
        if self._view is None:
            return
        chart = QChart()
        try:
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            chart.setTitle("")
            chart.setMargins(QMarginsF(0, 0, 0, 0))
        except QT_ERRORS:
            pass
        self._view.setChart(chart)

    def set_breakdown(self, by_category_expense: Dict[str, float]) -> None:
        if not charts_available or self._view is None:
            return

        series = QPieSeries()
        try:
            series.setLabelsVisible(False)
        except QT_ERRORS:
            pass
        try:
            series.setHoleSize(0.34)
            series.setPieSize(0.98)
        except QT_ERRORS:
            pass

        if not by_category_expense:
            slice_ = series.append("אין נתונים", 1.0)
            try:
                slice_.setLabelVisible(True)
            except QT_ERRORS:
                pass
        else:
            items = list(by_category_expense.items())
            # Pastel categorical palette — matches the monthly/accounts donuts.
            palette = list(PASTEL_HEX)
            for idx, (cat, amount) in enumerate(items):
                s = series.append(cat, float(amount))
                try:
                    s.setBrush(QColor(palette[idx % len(palette)]))
                except QT_ERRORS:
                    pass
                try:
                    s.hovered.connect(
                        lambda state,
                        sl=s,
                        label=cat,
                        val=float(amount): self._on_slice_hover(
                            series, sl, state, label, val
                        )
                    )
                except QT_ERRORS:
                    pass

        chart = QChart()
        chart.addSeries(series)
        try:
            chart.legend().setVisible(False)
        except QT_ERRORS:
            pass
        try:
            chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        except QT_ERRORS:
            try:
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            except QT_ERRORS:
                pass
        try:
            alignment = Qt.AlignmentFlag.AlignBottom
        except QT_ERRORS:
            alignment = getattr(Qt, "AlignBottom", None)
        try:
            if alignment is not None:
                chart.legend().setAlignment(alignment)
        except QT_ERRORS:
            pass
        try:
            chart.legend().setContentsMargins(0, 0, 0, 0)
        except QT_ERRORS:
            pass
        try:
            chart.setMargins(QMarginsF(0, 0, 0, 0))
        except QT_ERRORS:
            pass
        try:
            legend = chart.legend()
            try:
                legend.setBackgroundVisible(False)
                legend.setBorderColor(Qt.GlobalColor.transparent)
            except QT_ERRORS:
                pass
            try:
                legend.setMarkerShape(QLegend.MarkerShape.MarkerShapeRectangle)
            except QT_ERRORS:
                pass
        except QT_ERRORS:
            pass
        try:
            chart.setTitle("")
        except QT_ERRORS:
            pass
        try:
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            try:
                chart.setBackgroundPen(Qt.PenStyle.NoPen)
            except QT_ERRORS:
                pass
            try:
                if hasattr(series, "setLabelsColor"):
                    series.setLabelsColor(QColor("#111827"))
            except QT_ERRORS:
                pass
        except QT_ERRORS:
            pass

        self._view.setChart(chart)

    def _on_slice_hover(
        self,
        series: QPieSeries,
        slice_obj,
        hovering: bool,
        label: str,
        value: float,
    ) -> None:
        if self._view is None:
            return
        try:
            if hovering:
                percent = (float(slice_obj.value()) / float(series.sum())) * 100.0
                html = f"""
                <div style='font-size:13px;'>
                  <div style='font-weight:700; margin-bottom:4px;'>{label}</div>
                  <div>{percent:.1f}% · {format_currency(-abs(value))}</div>
                </div>
                """
                QToolTip.showText(QCursor.pos(), html, self._view)
            else:
                QToolTip.hideText()
        except QT_ERRORS:
            pass
