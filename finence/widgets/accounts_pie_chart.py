from __future__ import annotations

from typing import List, Optional

from ..models.accounts import MoneyAccount
from ..qt import (
    QLabel,
    QVBoxLayout,
    QWidget,
    Qt,
    QPainter,
    QColor,
    QMarginsF,
    charts_available,
    QChart,
    QChartView,
    QLegend,
    QPieSeries,
    QPieSlice,
    QFrame,
    QFont,
    QToolTip,
    QCursor,
)


class AccountsPieChart(QWidget):
    def __init__(
        self,
        accounts: Optional[List[MoneyAccount]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._accounts: List[MoneyAccount] = list(accounts or [])
        self._slice_to_marker = {}
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        if charts_available:
            self._chart_view = QChartView(self)
            self._chart_view.setMinimumHeight(320)
            try:
                self._chart_view.setRenderHint(
                    QPainter.RenderHint.Antialiasing, True
                )  # Qt6 enum
            except AttributeError:
                self._chart_view.setRenderHint(QPainter.Antialiasing, True)  # fallback
            # Make the view fully transparent and remove its frame
            try:
                self._chart_view.setStyleSheet("background: transparent;")
                self._chart_view.setFrameShape(QFrame.NoFrame)
                try:
                    self._chart_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                except Exception:
                    pass
            except Exception:
                pass
            self._layout.addWidget(self._chart_view)
            self._render_chart()
        else:
            placeholder = QLabel(
                "Charts are unavailable on this backend. Install QtCharts."
            )
            placeholder.setObjectName("Subtitle")
            self._layout.addWidget(placeholder)

        self.setLayout(self._layout)

    def set_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = list(accounts)
        if charts_available:
            self._render_chart()

    # Internal
    def _render_chart(self) -> None:
        series = QPieSeries()
        try:
            series.setLabelsVisible(False)
        except Exception:
            pass
        try:
            series.setHoleSize(0.38)
        except Exception:
            pass

        total = sum(max(a.amount, 0.0) for a in self._accounts)
        if total <= 0:
            # empty chart with a single zero slice
            slice_ = series.append("No Data", 1.0)
            try:
                slice_.setLabelVisible(True)
            except Exception:
                pass
        else:
            valid_accounts = [
                (acc, max(acc.amount, 0.0))
                for acc in self._accounts
                if max(acc.amount, 0.0) > 0.0
            ]
            valid_accounts.sort(key=lambda item: item[1], reverse=True)
            count = len(valid_accounts)
            for idx, (account, value) in enumerate(valid_accounts):
                s = series.append(account.name, value)
                try:
                    s.setProperty("baseLabel", account.name)
                except Exception:
                    pass
                # Labels hidden by default; legend will show names
                # Color gradient from blue (largest) to green (smallest), spaced by count
                try:
                    t = float(idx) / float(max(count - 1, 1))
                    color = _interpolate_qcolor(QColor("#2563eb"), QColor("#22c55e"), t)
                    s.setBrush(color)
                except Exception:
                    pass
                # No outside labels to avoid leader lines
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
        chart.legend().setVisible(True)
        try:
            chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
        except Exception:
            try:
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            except Exception:
                pass
        try:
            alignment = Qt.AlignmentFlag.AlignTop  # place legend above
        except AttributeError:  # pragma: no cover - PySide/PyQt variant
            alignment = Qt.AlignTop  # fallback for older enums
        chart.legend().setAlignment(alignment)
        # Pull legend closer to the plot by tightening margins/padding
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
                legend.setBorderColor(Qt.GlobalColor.transparent)  # type: ignore[arg-type]
            except Exception:
                pass
            try:
                legend.setMarkerShape(QLegend.MarkerShape.MarkerShapeRectangle)
            except Exception:
                pass
        except Exception:
            pass
        try:
            chart.setTitle("התפלגות פיננסית")
            title_font = QFont()
            title_font.setPointSize(50)
            title_font.setBold(True)
            chart.setTitleFont(title_font)
        except Exception:
            pass
        # Visuals
        try:
            chart.setTitleBrush(QColor("#0b1220"))
            chart.legend().setLabelColor(QColor("#0b1220"))
            # Make    and plot area backgrounds transparent (no colored background)
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(False)
            try:
                # Ensure no border around the chart background
                chart.setBackgroundPen(Qt.PenStyle.NoPen)  # Qt6
            except Exception:
                try:
                    chart.setBackgroundPen(Qt.NoPen)  # fallback alias
                except Exception:
                    pass
            series.setLabelsColor(QColor("#111827"))
        except Exception:
            pass

        # Build mapping from slice to legend marker so legend labels stay constant
        try:
            self._slice_to_marker = {}
            markers = chart.legend().markers(series)
            for sl, mk in zip(series.slices(), markers):
                self._slice_to_marker[sl] = mk
                # ensure legend shows base name regardless of slice label changes
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
                # Show tooltip with name, amount and percent
                try:
                    name = slice_obj.property("baseLabel") or ""
                    amount = slice_obj.value()
                    html = f"""
                    <div style='font-size:13px;'>
                      <div style='font-weight:700; margin-bottom:4px;'>{name}</div>
                      <div>
                        <span style='display:inline-block;width:10px;height:10px;background:{_qcolor_to_hex(slice_obj.brush().color())};margin-left:6px;border-radius:2px;'></span>
                        {percent:.1f}% · {format_currency(amount)}
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
            # Keep legend label constant (name) regardless of hover label
            try:
                marker = self._slice_to_marker.get(slice_obj)
                if marker:
                    base = slice_obj.property("baseLabel") or slice_obj.label()
                    marker.setLabel(str(base))
            except Exception:
                pass
        except Exception:
            pass

def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.0f}" if abs(value) >= 1000 else f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"

def _qcolor_to_hex(c: QColor) -> str:
    try:
        return "#{:02x}{:02x}{:02x}".format(c.red(), c.green(), c.blue())
    except Exception:
        return "#000000"

def _interpolate_qcolor(c1: QColor, c2: QColor, t: float) -> QColor:
    """
    Linearly interpolate between two colors c1 (t=0) and c2 (t=1).
    """
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    return QColor(r, g, b)
