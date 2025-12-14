from __future__ import annotations

from typing import Callable, List
import math

from ..qt import (
    QApplication,
    QLabel,
    QWidget,
    QVBoxLayout,
    QFrame,
    Qt,
    QChart,
    QLineSeries,
    QValueAxis,
    QCategoryAxis,
    QColor,
    QPainter,
    charts_available,
)
from ..models.accounts import BankAccount
from ..models.charts import (
    build_month_axis_from_history,
    build_base_values,
    latest_snapshots_by_month,
    catmull_rom_spline_samples,
)
from .savings_history_chart import ShadowChartView


def create_bank_history_chart_card(
    parent: QWidget,
    account: BankAccount,
    format_amount: Callable[[float], str],
) -> QWidget:
    chart_card = QWidget(parent)
    chart_card.setObjectName("Sidebar")
    try:
        chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    except Exception:
        pass
    chart_layout = QVBoxLayout(chart_card)
    chart_layout.setContentsMargins(8, 8, 8, 8)
    chart_layout.setSpacing(8)

    if charts_available and account.history:
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        axis = build_month_axis_from_history(account.history)
        month_keys = axis.keys
        month_to_index = axis.month_to_index

        latest_by_month = latest_snapshots_by_month(account.history)
        base_values, max_amount = build_base_values(
            axis=axis,
            latest_by_month=latest_by_month,
            fallback_amount=account.total_amount,
        )

        series = QLineSeries()
        series.setName(account.name)
        try:
            series.setPointsVisible(False)
        except Exception:
            pass

        samples = catmull_rom_spline_samples(base_values)
        for x_val, y_val in samples:
            series.append(x_val, y_val)

        try:
            base_color = QColor("#3b82f6")
        except Exception:
            base_color = QColor("#3b82f6")

        try:
            pen = series.pen()
            pen.setColor(base_color)
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

        shadow_specs: List[tuple[QLineSeries, QColor]] = [(series, base_color)]
        chart.addSeries(series)

        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = [
            (series, account.name, list(base_values))
        ]

        axis_x = QCategoryAxis()
        for key in month_keys:
            year, month = key
            label = f"{month:02d}/{year % 100:02d}"
            axis_x.append(label, float(month_to_index[key]))
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        if max_amount > 0:
            top = float(math.ceil(max_amount / 1000.0) * 1000.0)
        else:
            top = 1000.0
        axis_y.setRange(0.0, top)
        try:
            axis_y.setTickInterval(1000.0)
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

        for s_obj in chart.series():
            try:
                s_obj.attachAxis(axis_x)
                s_obj.attachAxis(axis_y)
            except Exception:
                pass

        chart_view = ShadowChartView(
            chart,
            shadow_specs,
            month_keys,
            tooltip_specs,
            format_amount,
            chart_card,
        )
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFrameShape(QFrame.Shape.NoFrame)
        chart_view.setStyleSheet("background: transparent;")
        chart_layout.addWidget(chart_view, 1)
    else:
        placeholder = QLabel("אין נתוני היסטוריה להצגה", chart_card)
        placeholder.setObjectName("Subtitle")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(placeholder, 1)

    return chart_card
