from __future__ import annotations

from typing import Any, Dict, List, Optional, cast
import math
import zlib
import importlib

from ..qt import (
    QApplication,
    QColor,
    QChart,
    QCategoryAxis,
    QFrame,
    QLabel,
    QLineSeries,
    QPainter,
    QValueAxis,
    QVBoxLayout,
    QWidget,
    Qt,
    charts_available,
)
from ..utils.formatting import format_currency
from ..models.charts import catmull_rom_spline_samples
from .savings_history_chart import ShadowChartView


class CategoryTrendsChart(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ChartCard")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)

        self._chart_view: Optional[ShadowChartView] = None
        self._view_host = QWidget(self)
        self._view_stack: Any = None
        self._focused_kind: Optional[str] = None
        self._focused_category: Optional[str] = None
        self._last_mode: Optional[str] = None
        self._last_month_labels: List[str] = []
        self._last_single: Dict[str, List[float]] = {}
        self._last_income: Dict[str, List[float]] = {}
        self._last_expense: Dict[str, List[float]] = {}
        self._last_combined_expenses_negative: bool = True
        self._last_income_prefix: str = "הכנסות: "
        self._last_expense_prefix: str = "הוצאות: "
        self._transition_enabled: bool = True

        if charts_available:
            self._layout.addWidget(self._view_host, 1)
            self.set_empty_state("אין נתונים להצגה")
        else:
            placeholder = QLabel(
                "Charts are unavailable on this backend. Install QtCharts.", self
            )
            placeholder.setObjectName("Subtitle")
            self._layout.addWidget(placeholder, 1)

        self._setup_view_stack()

    def _setup_view_stack(self) -> None:
        QStackedLayoutCls: Any = None
        try:
            from PySide6.QtWidgets import QStackedLayout as QStackedLayoutCls
        except Exception:
            try:
                QtWidgets = importlib.import_module("PyQt6.QtWidgets")
                QStackedLayoutCls = getattr(QtWidgets, "QStackedLayout", None)
            except Exception:
                QStackedLayoutCls = None

        if QStackedLayoutCls is None:
            return
        if self._view_stack is not None:
            return
        stack = QStackedLayoutCls(self._view_host)
        stack.setContentsMargins(0, 0, 0, 0)
        try:
            stack.setStackingMode(QStackedLayoutCls.StackingMode.StackAll)
        except Exception:
            stack_all = getattr(QStackedLayoutCls, "StackAll", None)
            if stack_all is not None:
                try:
                    stack.setStackingMode(stack_all)
                except Exception:
                    pass
        self._view_stack = stack

    def _animate_swap(
        self, *, old_view: ShadowChartView, new_view: ShadowChartView
    ) -> None:
        if not self._transition_enabled:
            try:
                if self._view_stack is not None:
                    self._view_stack.removeWidget(old_view)
                else:
                    self._layout.removeWidget(old_view)
            except Exception:
                pass
            try:
                old_view.deleteLater()
            except Exception:
                pass
            try:
                cast(Any, new_view).setGraphicsEffect(None)
            except Exception:
                pass
            return

        QPropertyAnimationCls: Any = None
        QEasingCurveCls: Any = None
        QGraphicsOpacityEffectCls: Any = None
        try:
            from PySide6.QtCore import QPropertyAnimation as QPropertyAnimationCls
            from PySide6.QtCore import QEasingCurve as QEasingCurveCls
            from PySide6.QtWidgets import (
                QGraphicsOpacityEffect as QGraphicsOpacityEffectCls,
            )
        except Exception:
            try:
                QtCore = importlib.import_module("PyQt6.QtCore")
                QtWidgets = importlib.import_module("PyQt6.QtWidgets")
                QPropertyAnimationCls = getattr(QtCore, "QPropertyAnimation", None)
                QEasingCurveCls = getattr(QtCore, "QEasingCurve", None)
                QGraphicsOpacityEffectCls = getattr(
                    QtWidgets, "QGraphicsOpacityEffect", None
                )
            except Exception:
                return
        if (
            QPropertyAnimationCls is None
            or QEasingCurveCls is None
            or QGraphicsOpacityEffectCls is None
        ):
            return

        old_eff = QGraphicsOpacityEffectCls(old_view)
        new_eff = QGraphicsOpacityEffectCls(new_view)
        try:
            old_view.setGraphicsEffect(old_eff)
            new_view.setGraphicsEffect(new_eff)
        except Exception:
            return

        try:
            old_eff.setOpacity(1.0)
            new_eff.setOpacity(0.0)
        except Exception:
            pass

        fade_out = QPropertyAnimationCls(old_eff, b"opacity", old_view)
        fade_in = QPropertyAnimationCls(new_eff, b"opacity", new_view)
        for anim, start, end in ((fade_out, 1.0, 0.0), (fade_in, 0.0, 1.0)):
            try:
                anim.setDuration(220)
            except Exception:
                pass
            try:
                anim.setStartValue(start)
                anim.setEndValue(end)
            except Exception:
                pass
            try:
                curve = None
                try:
                    curve = QEasingCurveCls.Type.InOutCubic
                except Exception:
                    curve = getattr(QEasingCurveCls, "InOutCubic", None)
                if curve is not None:
                    anim.setEasingCurve(curve)
            except Exception:
                try:
                    curve = getattr(QEasingCurveCls, "InOutCubic", None)
                    if curve is not None:
                        anim.setEasingCurve(curve)
                except Exception:
                    pass

        def _cleanup() -> None:
            try:
                if self._view_stack is not None:
                    self._view_stack.removeWidget(old_view)
                else:
                    self._layout.removeWidget(old_view)
            except Exception:
                pass
            try:
                old_view.deleteLater()
            except Exception:
                pass
            try:
                new_eff.setOpacity(1.0)
            except Exception:
                pass
            try:
                cast(Any, new_view).setGraphicsEffect(None)
            except Exception:
                pass

        try:
            fade_out.finished.connect(_cleanup)
        except Exception:
            pass

        try:
            fade_in.start()
            fade_out.start()
        except Exception:
            _cleanup()

    def set_transition_enabled(self, enabled: bool) -> None:
        self._transition_enabled = bool(enabled)

    def _replace_chart_view(self, view: ShadowChartView) -> None:
        old_view = self._chart_view
        if old_view is None:
            self._chart_view = view
            if self._view_stack is not None:
                self._view_stack.addWidget(view)
                try:
                    self._view_stack.setCurrentWidget(view)
                except Exception:
                    pass
            else:
                self._layout.addWidget(view, 1)
            return

        if self._view_stack is not None:
            try:
                self._view_stack.addWidget(view)
            except Exception:
                pass
            try:
                self._view_stack.setCurrentWidget(view)
            except Exception:
                pass
        else:
            try:
                idx = self._layout.indexOf(old_view)
            except Exception:
                idx = -1

            try:
                if idx >= 0:
                    self._layout.insertWidget(idx, view, 1)
                else:
                    self._layout.addWidget(view, 1)
            except Exception:
                self._layout.addWidget(view, 1)

        self._chart_view = view
        try:
            view.raise_()
        except Exception:
            pass
        self._animate_swap(old_view=old_view, new_view=view)

    def _nice_y_axis(self, max_val: float) -> tuple[float, float]:
        step = 250.0
        v = float(max(0.0, max_val))
        if v <= 0.0:
            return step, step
        top = math.ceil(v / step) * step
        if top <= 0.0:
            top = step
        return float(top), step

    def _color_for_series_name(self, name: str) -> QColor:
        try:
            key = str(name)
            try:
                inc = str(self._last_income_prefix or "")
                exp = str(self._last_expense_prefix or "")
                if inc and key.startswith(inc):
                    key = key[len(inc) :]
                elif exp and key.startswith(exp):
                    key = key[len(exp) :]
            except Exception:
                pass
            h = zlib.crc32(str(key).encode("utf-8")) & 0xFFFFFFFF
            hue = int(h % 360)
            return QColor.fromHsl(hue, 180, 140)
        except Exception:
            return QColor("#2563eb")

    def set_empty_state(self, text: str) -> None:
        if not charts_available:
            return
        self._last_mode = None
        self._focused_kind = None
        self._focused_category = None
        chart = QChart()
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        try:
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        except Exception:
            pass
        try:
            chart.setPlotAreaBackgroundVisible(False)
        except Exception:
            pass
        view = ShadowChartView(
            chart,
            [],
            [(0, 1)],
            [],
            lambda v: format_currency(v, use_compact=True),
            self,
            x_labels=[text],
        )
        try:
            hint = None
            try:
                hint = QPainter.RenderHint.Antialiasing
            except Exception:
                hint = getattr(QPainter, "Antialiasing", None)
            if hint is not None:
                view.setRenderHint(hint, True)
        except Exception:
            pass
        try:
            frame_no = None
            try:
                frame_no = QFrame.Shape.NoFrame
            except Exception:
                frame_no = getattr(QFrame, "NoFrame", None)
            if frame_no is not None:
                view.setFrameShape(frame_no)
        except Exception:
            pass
        try:
            view.setStyleSheet("background: transparent;")
        except Exception:
            pass
        self._replace_chart_view(view)

    def _parse_clicked_series(self, series_name: str) -> tuple[str, str]:
        name = str(series_name)
        inc = self._last_income_prefix
        exp = self._last_expense_prefix
        if inc and name.startswith(inc):
            return "income", name[len(inc) :]
        if exp and name.startswith(exp):
            return "expense", name[len(exp) :]
        return ("combined" if self._last_mode == "combined" else "single"), name

    def _on_series_clicked(self, series_name: str) -> None:
        kind, cat = self._parse_clicked_series(series_name)
        if self._focused_kind == kind and self._focused_category == cat:
            self._focused_kind = None
            self._focused_category = None
        else:
            self._focused_kind = kind
            self._focused_category = cat
        self._rerender_last()

    def _rerender_last(self) -> None:
        if self._last_mode == "single":
            self._render_single(self._last_single, self._last_month_labels)
        elif self._last_mode == "combined":
            self._render_combined(
                self._last_income,
                self._last_expense,
                self._last_month_labels,
                expenses_negative=self._last_combined_expenses_negative,
                income_prefix=self._last_income_prefix,
                expense_prefix=self._last_expense_prefix,
            )

    def _filter_single_by_focus(
        self, data_by_category: Dict[str, List[float]]
    ) -> Dict[str, List[float]]:
        if self._focused_kind is None or self._focused_category is None:
            return dict(data_by_category)
        if self._focused_kind != "single":
            return dict(data_by_category)
        cat = self._focused_category
        if cat in data_by_category:
            return {cat: data_by_category[cat]}
        self._focused_kind = None
        self._focused_category = None
        return dict(data_by_category)

    def _render_single(
        self,
        data_by_category: Dict[str, List[float]],
        month_labels: List[str],
    ) -> None:
        if not charts_available:
            return
        if not data_by_category:
            self.set_empty_state("אין נתונים להצגה")
            return

        data_by_category = self._filter_single_by_focus(data_by_category)

        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        try:
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        except Exception:
            pass
        try:
            chart.setPlotAreaBackgroundVisible(False)
        except Exception:
            pass

        max_val = 0.0
        categories_sorted = sorted(data_by_category.items(), key=lambda kv: -sum(kv[1]))
        shadow_specs: List[tuple[QLineSeries, QColor]] = []
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = []
        month_keys: List[tuple[int, int]] = [
            (0, i + 1) for i in range(min(12, len(month_labels)))
        ]

        for _idx, (category, values) in enumerate(categories_sorted):
            series = QLineSeries()
            series.setName(category)
            try:
                series.setPointsVisible(False)
            except Exception:
                pass

            base_values = [float(v) for v in values[:12]]
            if len(base_values) < 12:
                base_values = base_values + [0.0] * (12 - len(base_values))
            for y in base_values:
                if y > max_val:
                    max_val = y
            for x_val, y_val in catmull_rom_spline_samples(base_values):
                series.append(float(x_val), float(y_val))

            base_color = self._color_for_series_name(category)

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

            shadow_specs.append((series, base_color))
            tooltip_specs.append((series, category, base_values))
            chart.addSeries(series)

        axis_x = QCategoryAxis()
        for i, label in enumerate(month_labels[:12]):
            axis_x.append(label, float(i))
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        try:
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except Exception:
            pass
        top, tick = self._nice_y_axis(max_val)
        axis_y.setRange(0.0, top)
        try:
            tick_dynamic = None
            try:
                tick_dynamic = QValueAxis.TickType.TicksDynamic
            except Exception:
                tick_dynamic = getattr(QValueAxis, "TicksDynamic", None)
            if tick_dynamic is not None and hasattr(axis_y, "setTickType"):
                axis_y.setTickType(tick_dynamic)
            if hasattr(axis_y, "setTickAnchor"):
                axis_y.setTickAnchor(0.0)
            axis_y.setTickInterval(tick)
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

        view = ShadowChartView(
            chart,
            shadow_specs,
            month_keys,
            tooltip_specs,
            lambda v: format_currency(v, use_compact=True),
            self,
            x_labels=month_labels[:12],
            on_series_clicked=self._on_series_clicked,
        )
        try:
            hint = None
            try:
                hint = QPainter.RenderHint.Antialiasing
            except Exception:
                hint = getattr(QPainter, "Antialiasing", None)
            if hint is not None:
                view.setRenderHint(hint, True)
        except Exception:
            pass
        try:
            frame_no = None
            try:
                frame_no = QFrame.Shape.NoFrame
            except Exception:
                frame_no = getattr(QFrame, "NoFrame", None)
            if frame_no is not None:
                view.setFrameShape(frame_no)
        except Exception:
            pass
        try:
            view.setStyleSheet("background: transparent;")
        except Exception:
            pass
        self._replace_chart_view(view)

    def set_series(
        self,
        data_by_category: Dict[str, List[float]],
        month_labels: List[str],
    ) -> None:
        self._last_mode = "single"
        self._last_month_labels = list(month_labels)
        self._last_single = dict(data_by_category)
        self._render_single(data_by_category, month_labels)

    def set_combined_series(
        self,
        income_by_category: Dict[str, List[float]],
        expense_by_category: Dict[str, List[float]],
        month_labels: List[str],
        *,
        expenses_negative: bool = True,
        income_prefix: str = "הכנסות: ",
        expense_prefix: str = "הוצאות: ",
    ) -> None:
        self._last_mode = "combined"
        self._last_month_labels = list(month_labels)
        self._last_income = dict(income_by_category)
        self._last_expense = dict(expense_by_category)
        self._last_combined_expenses_negative = bool(expenses_negative)
        self._last_income_prefix = str(income_prefix)
        self._last_expense_prefix = str(expense_prefix)
        self._render_combined(
            income_by_category,
            expense_by_category,
            month_labels,
            expenses_negative=expenses_negative,
            income_prefix=income_prefix,
            expense_prefix=expense_prefix,
        )

    def _render_combined(
        self,
        income_by_category: Dict[str, List[float]],
        expense_by_category: Dict[str, List[float]],
        month_labels: List[str],
        *,
        expenses_negative: bool = True,
        income_prefix: str = "הכנסות: ",
        expense_prefix: str = "הוצאות: ",
    ) -> None:
        if not charts_available:
            return

        if not income_by_category and not expense_by_category:
            self.set_empty_state("אין נתונים להצגה")
            return

        if self._focused_kind is not None and self._focused_category is not None:
            cat = self._focused_category
            if self._focused_kind == "income":
                if cat in income_by_category:
                    income_by_category = {cat: income_by_category[cat]}
                    expense_by_category = {}
                else:
                    self._focused_kind = None
                    self._focused_category = None
            elif self._focused_kind == "expense":
                if cat in expense_by_category:
                    income_by_category = {}
                    expense_by_category = {cat: expense_by_category[cat]}
                else:
                    self._focused_kind = None
                    self._focused_category = None
            elif self._focused_kind == "combined":
                if cat in income_by_category:
                    income_by_category = {cat: income_by_category[cat]}
                    expense_by_category = {}
                elif cat in expense_by_category:
                    income_by_category = {}
                    expense_by_category = {cat: expense_by_category[cat]}
                else:
                    self._focused_kind = None
                    self._focused_category = None

        chart = QChart()
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        try:
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        except Exception:
            pass
        try:
            chart.setPlotAreaBackgroundVisible(False)
        except Exception:
            pass

        max_val = 0.0
        min_val = 0.0

        income_sorted = sorted(income_by_category.items(), key=lambda kv: -sum(kv[1]))
        expense_sorted = sorted(expense_by_category.items(), key=lambda kv: -sum(kv[1]))
        shadow_specs: List[tuple[QLineSeries, QColor]] = []
        tooltip_specs: List[tuple[QLineSeries, str, List[float]]] = []
        month_keys: List[tuple[int, int]] = [
            (0, i + 1) for i in range(min(12, len(month_labels)))
        ]

        def add_series(
            *,
            categories_sorted: List[tuple[str, List[float]]],
            name_prefix: str,
            is_expense: bool,
            start_idx: int,
        ) -> int:
            nonlocal max_val, min_val
            idx_local = start_idx
            for category, values in categories_sorted:
                series = QLineSeries()
                series_name = f"{name_prefix}{category}"
                series.setName(series_name)
                try:
                    series.setPointsVisible(False)
                except Exception:
                    pass

                base_values: List[float] = []
                for v in values[:12]:
                    y_raw = float(v)
                    y = (
                        -abs(y_raw)
                        if (is_expense and expenses_negative)
                        else abs(y_raw)
                    )
                    base_values.append(float(y))
                if len(base_values) < 12:
                    base_values = base_values + [0.0] * (12 - len(base_values))
                for y in base_values:
                    if y > max_val:
                        max_val = y
                    if y < min_val:
                        min_val = y
                for x_val, y_val in catmull_rom_spline_samples(base_values):
                    series.append(float(x_val), float(y_val))

                base_color = self._color_for_series_name(series_name)

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

                shadow_specs.append((series, base_color))
                tooltip_specs.append((series, f"{name_prefix}{category}", base_values))
                chart.addSeries(series)
                idx_local += 1
            return idx_local

        next_idx = add_series(
            categories_sorted=income_sorted,
            name_prefix=income_prefix,
            is_expense=False,
            start_idx=0,
        )
        add_series(
            categories_sorted=expense_sorted,
            name_prefix=expense_prefix,
            is_expense=True,
            start_idx=next_idx,
        )

        axis_x = QCategoryAxis()
        for i, label in enumerate(month_labels[:12]):
            axis_x.append(label, float(i))
        try:
            axis_x.setGridLineVisible(False)
            axis_x.setMinorGridLineVisible(False)
        except Exception:
            pass

        axis_y = QValueAxis()
        axis_y.setLabelFormat("%.0f")
        try:
            axis_y.setGridLineVisible(False)
            axis_y.setMinorGridLineVisible(False)
        except Exception:
            pass

        top, tick = self._nice_y_axis(max_val)
        bottom = 0.0 if not expenses_negative else min(0.0, min_val)
        axis_y.setRange(float(bottom), float(top))
        try:
            tick_dynamic = None
            try:
                tick_dynamic = QValueAxis.TickType.TicksDynamic
            except Exception:
                tick_dynamic = getattr(QValueAxis, "TicksDynamic", None)
            if tick_dynamic is not None and hasattr(axis_y, "setTickType"):
                axis_y.setTickType(tick_dynamic)
            if hasattr(axis_y, "setTickAnchor"):
                axis_y.setTickAnchor(0.0)
            axis_y.setTickInterval(tick)
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

        view = ShadowChartView(
            chart,
            shadow_specs,
            month_keys,
            tooltip_specs,
            lambda v: format_currency(v, use_compact=True),
            self,
            x_labels=month_labels[:12],
            on_series_clicked=self._on_series_clicked,
        )
        try:
            hint = None
            try:
                hint = QPainter.RenderHint.Antialiasing
            except Exception:
                hint = getattr(QPainter, "Antialiasing", None)
            if hint is not None:
                view.setRenderHint(hint, True)
        except Exception:
            pass
        try:
            frame_no = None
            try:
                frame_no = QFrame.Shape.NoFrame
            except Exception:
                frame_no = getattr(QFrame, "NoFrame", None)
            if frame_no is not None:
                view.setFrameShape(frame_no)
        except Exception:
            pass
        try:
            view.setStyleSheet("background: transparent;")
        except Exception:
            pass
        self._replace_chart_view(view)
