from __future__ import annotations

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
        except Exception:
            try:
                hint = getattr(QPainter, "Antialiasing", None)
                if hint is not None:
                    self._view.setRenderHint(hint, True)
            except Exception:
                pass
        try:
            self._view.setStyleSheet("background: transparent;")
        except Exception:
            pass
        try:
            self._view.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            pass
        try:
            self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        except Exception:
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
        except Exception:
            pass
        self._view.setChart(chart)

    def set_breakdown(self, by_category_expense: Dict[str, float]) -> None:
        if not charts_available or self._view is None:
            return

        series = QPieSeries()
        try:
            series.setLabelsVisible(False)
        except Exception:
            pass
        try:
            series.setHoleSize(0.34)
            series.setPieSize(0.98)
        except Exception:
            pass

        if not by_category_expense:
            slice_ = series.append("אין נתונים", 1.0)
            try:
                slice_.setLabelVisible(True)
            except Exception:
                pass
        else:
            items = list(by_category_expense.items())
            count = len(items)
            start_color = QColor("#2563eb")
            end_color = QColor("#ef4444")
            for idx, (cat, amount) in enumerate(items):
                s = series.append(cat, float(amount))
                try:
                    t = float(idx) / float(max(count - 1, 1))
                    s.setBrush(self._interpolate_qcolor(start_color, end_color, t))
                except Exception:
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
                except Exception:
                    pass

        chart = QChart()
        chart.addSeries(series)
        try:
            chart.legend().setVisible(False)
        except Exception:
            pass
        try:
            chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        except Exception:
            try:
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            except Exception:
                pass
        try:
            alignment = Qt.AlignmentFlag.AlignBottom
        except Exception:
            alignment = getattr(Qt, "AlignBottom", None)
        try:
            if alignment is not None:
                chart.legend().setAlignment(alignment)
        except Exception:
            pass
        try:
            chart.legend().setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            chart.setMargins(QMarginsF(0, 0, 0, 0))
        except Exception:
            pass
        try:
            legend = chart.legend()
            try:
                legend.setBackgroundVisible(False)
                legend.setBorderColor(Qt.GlobalColor.transparent)
            except Exception:
                pass
            try:
                legend.setMarkerShape(QLegend.MarkerShape.MarkerShapeRectangle)
            except Exception:
                pass
        except Exception:
            pass
        try:
            chart.setTitle("")
        except Exception:
            pass
        try:
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            try:
                chart.setBackgroundPen(Qt.PenStyle.NoPen)
            except Exception:
                pass
            try:
                if hasattr(series, "setLabelsColor"):
                    series.setLabelsColor(QColor("#111827"))
            except Exception:
                pass
        except Exception:
            pass

        self._view.setChart(chart)

    @staticmethod
    def _interpolate_qcolor(start: QColor, end: QColor, t: float) -> QColor:
        try:
            r1, g1, b1 = start.red(), start.green(), start.blue()
            r2, g2, b2 = end.red(), end.green(), end.blue()
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            return QColor(r, g, b)
        except Exception:
            return start

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
        except Exception:
            pass
