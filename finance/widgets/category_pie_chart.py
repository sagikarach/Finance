from __future__ import annotations

from typing import List, Optional

from ..models.monthly_report import CategoryMonthlyBreakdown
from ..utils.formatting import format_currency as format_currency_compact
from ..qt import (
    QLabel,
    QVBoxLayout,
    QWidget,
    Qt,
    QPainter,
    QColor,
    QMarginsF,
    QSizePolicy,
    QToolTip,
    QCursor,
    charts_available,
    QChart,
    QChartView,
    QLegend,
    QPieSeries,
    QPieSlice,
    QFrame,
)


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


class CategoryPieChart(QWidget):
    def __init__(
        self,
        breakdowns: Optional[List[CategoryMonthlyBreakdown]] = None,
        is_income: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._breakdowns: List[CategoryMonthlyBreakdown] = list(breakdowns or [])
        self._is_income = is_income
        self._was_hidden: bool = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        if charts_available:
            self._chart_view = QChartView(self)
            try:
                self._chart_view.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                self.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
            except Exception:
                pass
            try:
                self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            except AttributeError:
                self._chart_view.setRenderHint(QPainter.Antialiasing, True)
            try:
                self._chart_view.setStyleSheet("background: transparent;")
                try:
                    self._chart_view.setFrameShape(QFrame.Shape.NoFrame)
                except AttributeError:
                    self._chart_view.setFrameShape(QFrame.NoFrame)
                try:
                    self._chart_view.setAttribute(
                        Qt.WidgetAttribute.WA_TranslucentBackground, True
                    )
                except Exception:
                    pass
            except Exception:
                pass
            self._layout.addWidget(self._chart_view)
            self._render_chart()
        else:
            placeholder = QLabel(
                "גרפים אינם זמינים. נדרשת התקנת QtCharts."
            )
            placeholder.setObjectName("Subtitle")
            self._layout.addWidget(placeholder)

        self.setLayout(self._layout)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if charts_available and self._was_hidden:
            self._render_chart()
        self._was_hidden = False

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._was_hidden = True

    def set_breakdowns(
        self, breakdowns: List[CategoryMonthlyBreakdown], is_income: bool = True
    ) -> None:
        self._breakdowns = list(breakdowns)
        self._is_income = is_income
        if charts_available:
            self._render_chart()

    def _render_chart(self) -> None:
        if not charts_available:
            return

        filtered_breakdowns = [
            b for b in self._breakdowns if b.is_income == self._is_income
        ]

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

        total = sum(b.total_amount for b in filtered_breakdowns)
        if total <= 0:
            slice_ = series.append("אין נתונים", 1.0)
            try:
                slice_.setLabelVisible(True)
            except Exception:
                pass
        else:
            sorted_breakdowns = sorted(
                filtered_breakdowns, key=lambda b: b.total_amount, reverse=True
            )
            count = len(sorted_breakdowns)

            if self._is_income:
                start_color = QColor("#2563eb")
                end_color = QColor("#22c55e")
            else:
                start_color = QColor("#2563eb")
                end_color = QColor("#ef4444")

            for idx, breakdown in enumerate(sorted_breakdowns):
                s = series.append(breakdown.category, breakdown.total_amount)
                try:
                    s.setProperty("baseLabel", breakdown.category)
                except Exception:
                    pass
                try:
                    t = float(idx) / float(max(count - 1, 1))
                    color = _interpolate_qcolor(start_color, end_color, t)
                    s.setBrush(color)
                except Exception:
                    pass
                try:
                    s.hovered.connect(
                        lambda state, sl=s, br=breakdown: self._on_slice_hover(
                            series, sl, state, br
                        )
                    )
                except Exception:
                    pass

        chart = QChart()
        chart.addSeries(series)
        chart.legend().setVisible(False)
        try:
            chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        except Exception:
            try:
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            except Exception:
                pass
        try:
            alignment = Qt.AlignmentFlag.AlignBottom
        except AttributeError:
            alignment = Qt.AlignBottom
        chart.legend().setAlignment(alignment)
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
            chart.setTitleBrush(QColor("#0b1220"))
            chart.legend().setLabelColor(QColor("#0b1220"))
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            try:
                chart.setBackgroundPen(Qt.PenStyle.NoPen)
            except Exception:
                try:
                    chart.setBackgroundPen(Qt.NoPen)
                except Exception:
                    pass
            try:
                series.setLabelsColor(QColor("#111827"))
            except Exception:
                pass
        except Exception:
            pass

        self._chart_view.setChart(chart)

    def _on_slice_hover(
        self,
        series: QPieSeries,
        slice_obj: QPieSlice,
        hovering: bool,
        breakdown: CategoryMonthlyBreakdown,
    ) -> None:
        try:
            if hovering:
                percent = (slice_obj.value() / series.sum()) * 100.0
                amount = slice_obj.value()
                name = breakdown.category
                html = f"""
                <div style='font-size:13px;'>
                  <div style='font-weight:700; margin-bottom:4px;'>{name}</div>
                  <div>
                    <span style='display:inline-block;width:10px;height:10px;background:{_qcolor_to_hex(slice_obj.brush().color())};margin-left:6px;border-radius:2px;'></span>
                    {percent:.1f}% · {format_currency_compact(amount, use_compact=True)}
                  </div>
                </div>
                """
                try:
                    pos = QCursor.pos()
                    QToolTip.showText(pos, html, self._chart_view)
                except Exception:
                    return
            else:
                try:
                    QToolTip.hideText()
                except Exception:
                    pass
        except Exception:
            pass


def _qcolor_to_hex(c: QColor) -> str:
    try:
        return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
    except Exception:
        return "#000000"
