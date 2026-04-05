from __future__ import annotations

from typing import List, Optional, Sequence

from ..models.accounts import MoneyAccount
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
    charts_available,
    QChart,
    QChartView,
    QLegend,
    QPieSeries,
    QPieSlice,
    QFrame,
    QToolTip,
    QCursor,
)


class AccountsPieChart(QWidget):
    def __init__(
        self,
        accounts: Optional[Sequence[MoneyAccount]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._accounts: List[MoneyAccount] = list(accounts or [])
        self._slice_to_marker: dict = {}
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

    def set_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = list(accounts)
        if charts_available:
            self._render_chart()

    def _render_chart(self) -> None:
        series = QPieSeries()
        try:
            series.setLabelsVisible(False)
        except Exception:
            pass
        try:
            series.setHoleSize(0.38)
            series.setPieSize(0.92)
        except Exception:
            pass

        total = sum(max(a.total_amount, 0.0) for a in self._accounts)
        if total <= 0:
            slice_ = series.append("אין נתונים", 1.0)
            try:
                slice_.setLabelVisible(True)
            except Exception:
                pass
        else:
            valid_accounts = [
                (acc, max(acc.total_amount, 0.0))
                for acc in self._accounts
                if max(acc.total_amount, 0.0) > 0.0
            ]
            valid_accounts.sort(key=lambda item: item[1], reverse=True)
            count = len(valid_accounts)
            for idx, (account, value) in enumerate(valid_accounts):
                s = series.append(account.name, value)
                try:
                    s.setProperty("baseLabel", account.name)
                except Exception:
                    pass
                try:
                    t = float(idx) / float(max(count - 1, 1))
                    color = _interpolate_qcolor(QColor("#2563eb"), QColor("#22c55e"), t)
                    s.setBrush(color)
                except Exception:
                    pass
                try:
                    s.hovered.connect(
                        lambda state, sl=s, ser=series: self._on_slice_hover(
                            ser, sl, state
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

        try:
            self._slice_to_marker = {}
            markers = chart.legend().markers(series)
            for sl, mk in zip(series.slices(), markers):
                self._slice_to_marker[sl] = mk
                try:
                    base = sl.property("baseLabel") or sl.label()
                    mk.setLabel(str(base))
                except Exception:
                    pass
        except Exception:
            pass

        self._chart_view.setChart(chart)

    def _on_slice_hover(
        self, series: QPieSeries, slice_obj: QPieSlice, hovering: bool
    ) -> None:
        try:
            if hovering:
                total = (
                    series.sum()
                    if hasattr(series, "sum")
                    else sum([sl.value() for sl in series.slices()])
                )
                percent = 0.0 if not total else (slice_obj.value() / total) * 100.0
                try:
                    slice_obj.setExploded(True)
                    if hasattr(slice_obj, "setExplodeDistanceFactor"):
                        slice_obj.setExplodeDistanceFactor(0.08)
                except Exception:
                    pass
                try:
                    name = slice_obj.property("baseLabel") or ""
                    amount = slice_obj.value()
                    html = f"""
                    <div style='font-size:13px;'>
                      <div style='font-weight:700; margin-bottom:4px;'>{name}</div>
                      <div>
                        <span style='display:inline-block;width:10px;height:10px;background:{_qcolor_to_hex(slice_obj.brush().color())};margin-left:6px;border-radius:2px;'></span>
                        {percent:.1f}% · {format_currency_compact(amount, use_compact=True)}
                      </div>
                    </div>
                    """
                    QToolTip.showText(QCursor.pos(), html, self._chart_view)
                except Exception:
                    pass
            else:
                try:
                    slice_obj.setLabelVisible(False)
                except Exception:
                    pass
                try:
                    slice_obj.setExploded(False)
                except Exception:
                    pass
                try:
                    QToolTip.hideText()
                except Exception:
                    pass
            try:
                marker = self._slice_to_marker.get(slice_obj)
                if marker:
                    base = slice_obj.property("baseLabel") or slice_obj.label()
                    marker.setLabel(str(base))
            except Exception:
                pass
        except Exception:
            pass


def _qcolor_to_hex(c: QColor) -> str:
    try:
        return "#{:02x}{:02x}{:02x}".format(c.red(), c.green(), c.blue())
    except Exception:
        return "#000000"


def _interpolate_qcolor(c1: QColor, c2: QColor, t: float) -> QColor:
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    return QColor(r, g, b)
