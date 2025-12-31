from __future__ import annotations

from typing import Callable, List, Optional
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
from ..models.accounts import BankAccount, BudgetAccount
from ..models.bank_movement import BankMovement
from ..models.accounts import parse_iso_date
from ..models.charts import (
    build_base_values,
    latest_snapshots_by_month_with_axis,
    catmull_rom_spline_samples,
)
from .savings_history_chart import ShadowChartView


def create_bank_history_chart_card(
    parent: QWidget,
    account: BankAccount | BudgetAccount,
    format_amount: Callable[[float], str],
    *,
    movements: Optional[List[BankMovement]] = None,
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

    if isinstance(account, BudgetAccount):
        all_movements = list(movements or [])
        spent_movements = [
            m
            for m in all_movements
            if m.account_name == account.name
            and float(getattr(m, "amount", 0.0) or 0.0) < 0.0
            and not bool(getattr(m, "is_transfer", False))
        ]
        try:
            spent_movements.sort(key=lambda m: parse_iso_date(str(m.date)))
        except Exception:
            pass

        if charts_available and spent_movements:
            # "Budget month" spent: period is (reset_day+1 .. next reset_day) and
            # the label is the month of the reset_day at the END of the period.
            reset_day = int(getattr(account, "reset_day", 1) or 1)
            if reset_day < 1:
                reset_day = 1
            if reset_day > 28:
                reset_day = 28

            def _next_month(year: int, month: int) -> tuple[int, int]:
                if month >= 12:
                    return (year + 1, 1)
                return (year, month + 1)

            spent_by_period_end: dict[tuple[int, int], float] = {}
            for m in spent_movements:
                try:
                    dt = parse_iso_date(str(getattr(m, "date", "") or ""))
                except Exception:
                    continue
                amt = float(getattr(m, "amount", 0.0) or 0.0)
                if dt.day <= reset_day:
                    end_key = (dt.year, dt.month)
                else:
                    end_key = _next_month(dt.year, dt.month)
                spent_by_period_end[end_key] = float(
                    spent_by_period_end.get(end_key, 0.0)
                ) + abs(float(amt))

            keys_sorted = sorted(spent_by_period_end.keys(), key=lambda k: (k[0], k[1]))
            if not keys_sorted:
                placeholder = QLabel("אין הוצאות להצגה", chart_card)
                placeholder.setObjectName("Subtitle")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                chart_layout.addWidget(placeholder, 1)
                return chart_card

            # Fill gaps with 0 so the line is continuous across months.
            start_key = keys_sorted[0]
            end_key = keys_sorted[-1]
            month_keys: List[tuple[int, int]] = []
            cur = start_key
            while True:
                month_keys.append(cur)
                if cur == end_key:
                    break
                cur = _next_month(cur[0], cur[1])

            base_values = [float(spent_by_period_end.get(k, 0.0)) for k in month_keys]
            max_amount = max(base_values) if base_values else 0.0
            x_labels = [f"{m:02d}/{y % 100:02d}" for (y, m) in month_keys]

            chart = QChart()
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            chart.legend().setVisible(False)
            chart.setBackgroundRoundness(0)
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
            chart.setPlotAreaBackgroundVisible(False)

            series = QLineSeries()
            series.setName("הוצאות לפי חודש")
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

            shadow_specs_budget: List[tuple[QLineSeries, QColor]] = [
                (series, base_color)
            ]
            chart.addSeries(series)

            # Use period-end (year, month) keys.
            x_keys: List[tuple[int, int]] = list(month_keys)
            tooltip_specs_budget: List[tuple[QLineSeries, str, List[float]]] = [
                (series, "הוצאות לפי חודש", list(base_values))
            ]

            axis_x = QCategoryAxis()
            for idx, label in enumerate(x_labels):
                axis_x.append(label, float(idx))
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
                axis_y.setTickInterval(max(100.0, top / 4.0))
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
                shadow_specs_budget,
                x_keys,
                tooltip_specs_budget,
                format_amount,
                chart_card,
                x_labels=x_labels,
                baseline_value=0.0,
            )
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
            chart_view.setFrameShape(QFrame.Shape.NoFrame)
            chart_view.setStyleSheet("background: transparent;")
            chart_layout.addWidget(chart_view, 1)
        else:
            placeholder = QLabel("אין הוצאות להצגה", chart_card)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(placeholder, 1)
        return chart_card

    if isinstance(account, BankAccount) and charts_available and movements is not None:
        # Build the series from movements + baseline_amount so changing the init amount
        # immediately affects the chart (old history snapshots may not include it).
        acc_name = str(getattr(account, "name", "") or "").strip()
        baseline = float(getattr(account, "baseline_amount", 0.0) or 0.0)

        sums_by_month: dict[tuple[int, int], float] = {}
        for m in list(movements or []):
            try:
                if str(getattr(m, "account_name", "") or "").strip() != acc_name:
                    continue
                if bool(getattr(m, "is_transfer", False)):
                    # Transfers should affect balances in general, but your app treats them specially.
                    # Still include them in balance (they are real money movement). Keep them included.
                    pass
                dt = parse_iso_date(str(getattr(m, "date", "") or ""))
                key = (dt.year, dt.month)
                sums_by_month[key] = float(sums_by_month.get(key, 0.0)) + float(
                    getattr(m, "amount", 0.0) or 0.0
                )
            except Exception:
                continue

        def _next_month(year: int, month: int) -> tuple[int, int]:
            if month >= 12:
                return (year + 1, 1)
            return (year, month + 1)

        if sums_by_month:
            keys_sorted = sorted(sums_by_month.keys(), key=lambda k: (k[0], k[1]))
            start_key = keys_sorted[0]
            end_key = keys_sorted[-1]
            month_keys_bank: List[tuple[int, int]] = []
            cur = start_key
            while True:
                month_keys_bank.append(cur)
                if cur == end_key:
                    break
                cur = _next_month(cur[0], cur[1])
        else:
            placeholder = QLabel("אין תנועות להצגה", chart_card)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(placeholder, 1)
            return chart_card

        # Build actual balance values: baseline + cumulative monthly net movements.
        # First point is baseline + first month's net (as requested).
        running = float(baseline)
        base_values_bank: List[float] = []
        for k in month_keys_bank:
            running += float(sums_by_month.get(k, 0.0))
            base_values_bank.append(float(running))

        min_amount = min(base_values_bank) if base_values_bank else 0.0
        max_amount = max(base_values_bank) if base_values_bank else 0.0
        # Ensure 0 is always visible (user wants the 0-line to be at 0).
        min_amount = float(min(min_amount, 0.0))
        max_amount = float(max(max_amount, 0.0))

        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        series = QLineSeries()
        series.setName(account.name)
        try:
            series.setPointsVisible(False)
        except Exception:
            pass

        samples = catmull_rom_spline_samples(base_values_bank)
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

        shadow_specs_bank: List[tuple[QLineSeries, QColor]] = [(series, base_color)]
        chart.addSeries(series)

        tooltip_specs_bank: List[tuple[QLineSeries, str, List[float]]] = [
            (series, account.name, list(base_values_bank))
        ]

        axis_x = QCategoryAxis()
        x_labels = [f"{m:02d}/{y % 100:02d}" for (y, m) in month_keys_bank]
        for idx, label in enumerate(x_labels):
            axis_x.append(label, float(idx))
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        top = 1000.0
        if max_amount != 0.0:
            top = float(math.ceil(abs(max_amount) / 1000.0) * 1000.0) or 1000.0
        bottom = 0.0
        if min_amount < 0.0:
            bottom = float(-math.ceil(abs(min_amount) / 1000.0) * 1000.0)
        axis_y.setRange(bottom, top)
        try:
            axis_y.setTickInterval(max(1000.0, (top - bottom) / 4.0))
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
            shadow_specs_bank,
            month_keys_bank,
            tooltip_specs_bank,
            format_amount,
            chart_card,
            x_labels=x_labels,
            baseline_value=0.0,
        )
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFrameShape(QFrame.Shape.NoFrame)
        chart_view.setStyleSheet("background: transparent;")
        chart_layout.addWidget(chart_view, 1)
        return chart_card

    if charts_available and account.history:
        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)

        axis, latest_by_month = latest_snapshots_by_month_with_axis(account.history)
        month_keys = axis.keys
        month_to_index = axis.month_to_index
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
