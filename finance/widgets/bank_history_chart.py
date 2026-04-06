from __future__ import annotations

import math
from datetime import datetime
from typing import Callable, List, Optional

from ..models.accounts import BankAccount, BudgetAccount, parse_iso_date
from ..models.bank_movement import BankMovement
from ..models.charts import (
    build_base_values,
    catmull_rom_spline_samples,
    latest_snapshots_by_month_with_axis,
)
from ..qt import (
    QApplication,
    QCategoryAxis,
    QChart,
    QColor,
    QFrame,
    QLabel,
    QLineSeries,
    QPainter,
    Qt,
    QValueAxis,
    QVBoxLayout,
    QWidget,
    charts_available,
)
from .savings_history_chart import (
    ShadowChartView,
    _apply_line_pen,
    _build_y_axis,
    _label_color,
    _label_step_for,
)
from .time_range_bar import TimeRangeBar


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month >= 12 else (year, month + 1)


def _month_key_fast(date_str: str) -> Optional[tuple[int, int]]:
    s = str(date_str or "").strip()
    if len(s) >= 7 and s[4] == "-" and s[7:8] in ("", "-"):
        try:
            y, m = int(s[0:4]), int(s[5:7])
            if 1 <= m <= 12:
                return (y, m)
        except Exception:
            pass
    return None


def _build_x_axis_labeled(
    labels: List[str],
    label_step: int,
) -> QCategoryAxis:
    """Build a category axis from explicit labels, thinned by *label_step*."""
    axis = QCategoryAxis()
    n = len(labels)
    for i, lbl in enumerate(labels):
        if i % label_step == 0 or i == n - 1:
            axis.append(lbl, float(i))
    try:
        axis.setGridLineVisible(False)
        axis.setMinorGridLineVisible(False)
    except Exception:
        pass
    return axis


# ─────────────────────────────────────── BankHistoryChartCard ──────────

class BankHistoryChartCard(QWidget):
    """
    Chart card for a BankAccount or BudgetAccount.

    Includes a TimeRangeBar (3M / 6M / 1Y / 2Y / הכל).
    Each range change rebuilds the series and axes for the visible slice,
    with smart label density, no fill glitches, and no label truncation.
    """

    def __init__(
        self,
        parent: QWidget,
        account: BankAccount | BudgetAccount,
        format_amount: Callable[[float], str],
        *,
        movements: Optional[List[BankMovement]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._chart: Optional[QChart] = None
        self._chart_view: Optional[ShadowChartView] = None
        self._format_amount = format_amount

        # data set by each _prepare_* method
        self._chart_type: str = "none"
        # budget / history: parallel month_keys + base_values
        self._month_keys: List[tuple[int, int]] = []
        self._base_values: List[float] = []
        self._series_color = QColor("#3b82f6")
        self._series_name: str = ""
        # bank movements: month_keys + full balance series (incl. start/today)
        self._bv_bank: List[float] = []         # [start, m1..mN, today]
        self._mk_bank: List[tuple[int, int]] = []  # N month keys

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        ready = self._prepare(account, format_amount, movements)
        if not ready:
            placeholder = QLabel("אין נתוני היסטוריה להצגה", self)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder, 1)
            return

        # ── chart + view (initially empty) ───────────────────────────────
        chart = QChart()
        try:
            chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        except Exception:
            pass
        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(0)
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setPlotAreaBackgroundVisible(False)
        self._chart = chart

        chart_view = ShadowChartView(chart, [], [], [], format_amount, self,
                                     baseline_value=0.0)
        chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        chart_view.setFrameShape(QFrame.Shape.NoFrame)
        chart_view.setStyleSheet("background: transparent;")
        self._chart_view = chart_view

        # ── range bar ─────────────────────────────────────────────────────
        n = self._total_month_count()
        default_months = 12 if n > 12 else 0
        range_bar = TimeRangeBar(self, default_months=default_months)
        range_bar.range_changed.connect(self._apply_range)
        layout.addWidget(range_bar)
        layout.addWidget(chart_view, 1)

        self._apply_range(default_months)

    # ───────────────────────────────────── data preparation ────────────

    def _prepare(
        self,
        account: BankAccount | BudgetAccount,
        format_amount: Callable[[float], str],
        movements: Optional[List[BankMovement]],
    ) -> bool:
        if isinstance(account, BudgetAccount):
            return self._prepare_budget(account, movements)
        if isinstance(account, BankAccount) and movements is not None and charts_available:
            return self._prepare_bank_movements(account, movements)
        if charts_available and getattr(account, "history", None):
            return self._prepare_history(account)
        return False

    def _prepare_budget(
        self, account: BudgetAccount, movements: Optional[List[BankMovement]]
    ) -> bool:
        all_mov = list(movements or [])
        spent = [
            m for m in all_mov
            if m.account_name == account.name
            and float(getattr(m, "amount", 0.0) or 0.0) < 0.0
            and not bool(getattr(m, "is_transfer", False))
        ]
        if not (charts_available and spent):
            return False

        reset_day = max(1, min(28, int(getattr(account, "reset_day", 1) or 1)))
        spent_by_period: dict[tuple[int, int], float] = {}
        for m in spent:
            try:
                dt = parse_iso_date(str(getattr(m, "date", "") or ""))
                if dt == datetime.min:
                    continue
                end_key = (dt.year, dt.month) if dt.day <= reset_day else _next_month(dt.year, dt.month)
                spent_by_period[end_key] = spent_by_period.get(end_key, 0.0) + abs(float(getattr(m, "amount", 0.0) or 0.0))
            except Exception:
                continue

        keys = sorted(spent_by_period)
        if not keys:
            return False

        month_keys: List[tuple[int, int]] = []
        cur = keys[0]
        while True:
            month_keys.append(cur)
            if cur == keys[-1]:
                break
            cur = _next_month(cur[0], cur[1])

        self._chart_type = "budget"
        self._month_keys = month_keys
        self._base_values = [float(spent_by_period.get(k, 0.0)) for k in month_keys]
        self._series_name = "הוצאות לפי חודש"
        return True

    def _prepare_bank_movements(
        self, account: BankAccount, movements: List[BankMovement]
    ) -> bool:
        acc_name = str(getattr(account, "name", "") or "").strip()
        baseline = float(getattr(account, "baseline_amount", 0.0) or 0.0)

        sums: dict[tuple[int, int], float] = {}
        for m in movements:
            try:
                if str(getattr(m, "account_name", "") or "").strip() != acc_name:
                    continue
                ks = str(getattr(m, "date", "") or "")
                key = _month_key_fast(ks)
                if key is None:
                    dt = parse_iso_date(ks)
                    if dt == datetime.min:
                        continue
                    key = (dt.year, dt.month)
                sums[key] = sums.get(key, 0.0) + float(getattr(m, "amount", 0.0) or 0.0)
            except Exception:
                continue

        try:
            if float(baseline) == 0.0:
                inferred = float(getattr(account, "total_amount", 0.0) or 0.0) - sum(sums.values())
                if abs(inferred) > 0.0001:
                    baseline = inferred
        except Exception:
            pass

        mk: List[tuple[int, int]] = []
        if sums:
            ks = sorted(sums)
            cur = ks[0]
            while True:
                mk.append(cur)
                if cur == ks[-1]:
                    break
                cur = _next_month(cur[0], cur[1])

        running = float(baseline)
        bv = [running]
        for k in mk:
            running += sums.get(k, 0.0)
            bv.append(running)
        bv.append(running)  # "today"

        self._chart_type = "bank"
        self._mk_bank = mk
        self._bv_bank = bv
        self._series_name = str(getattr(account, "name", "") or "")
        return True

    def _prepare_history(self, account: BankAccount | BudgetAccount) -> bool:
        axis_obj, latest = latest_snapshots_by_month_with_axis(account.history)
        base_values, _ = build_base_values(
            axis=axis_obj, latest_by_month=latest,
            fallback_amount=getattr(account, "total_amount", 0.0),
        )
        self._chart_type = "history"
        self._month_keys = list(axis_obj.keys)
        self._base_values = list(base_values)
        self._series_name = str(getattr(account, "name", "") or "")
        return True

    # ─────────────────────────────────────── helpers ────────────────────

    def _total_month_count(self) -> int:
        if self._chart_type == "bank":
            return len(self._mk_bank)
        return len(self._month_keys)

    # ─────────────────────────────────────── range ──────────────────────

    def _apply_range(self, months: int) -> None:
        if self._chart is None or self._chart_view is None:
            return

        if self._chart_type == "bank":
            self._apply_range_bank(months)
        else:
            self._apply_range_simple(months)

    def _apply_range_simple(self, months: int) -> None:
        """Used for budget spend and history snapshot charts."""
        n = len(self._month_keys)
        if n == 0:
            return
        first = max(0, n - months) if 0 < months < n else 0
        visible_keys = self._month_keys[first:]
        visible_vals = self._base_values[first:]
        n_vis = len(visible_keys)
        if n_vis == 0:
            return

        self._clear_chart()

        label_step = _label_step_for(n_vis)
        labels = [f"{m:02d}/{y % 100:02d}" for y, m in visible_keys]
        axis_x = _build_x_axis_labeled(labels, label_step)
        max_v = max(visible_vals) if visible_vals else 0.0
        axis_y = _build_y_axis(max_v if max_v > 0 else 1000.0)

        series = QLineSeries()
        series.setName(self._series_name)
        try:
            series.setPointsVisible(False)
        except Exception:
            pass
        _apply_line_pen(series, self._series_color)
        for x_val, y_val in catmull_rom_spline_samples(visible_vals):
            series.append(x_val, y_val)
        self._chart.addSeries(series)

        lc = _label_color()
        try:
            axis_x.setLabelsBrush(lc)
            axis_y.setLabelsBrush(lc)
        except Exception:
            pass
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for s in self._chart.series():
            try:
                s.attachAxis(axis_x)
                s.attachAxis(axis_y)
            except Exception:
                pass

        self._chart_view._shadows = [(series, self._series_color)]
        self._chart_view._tooltip_specs = [(series, self._series_name, list(visible_vals))]
        self._chart_view._month_keys = list(visible_keys)
        self._chart_view._x_labels = labels

    def _apply_range_bank(self, months: int) -> None:
        """Used for bank-account balance from movements."""
        N = len(self._mk_bank)            # number of real months
        n_bv = len(self._bv_bank)        # N + 2 (start + N months + today)
        if n_bv == 0:
            return

        if months == 0 or months >= N:
            # Show everything: start + all months + today
            first_bv = 0
            visible_mk = self._mk_bank
            include_start = True
        else:
            # Show last M months + today (no "start" baseline)
            first_bv = max(1, N - months + 1)
            visible_mk = self._mk_bank[first_bv - 1:]
            include_start = False

        visible_bv = self._bv_bank[first_bv:]
        n_vis = len(visible_bv)
        if n_vis == 0:
            return

        self._clear_chart()

        # Build x-labels for visible slice
        if include_start:
            x_labels = (
                ["התחלה"]
                + [f"{m:02d}/{y % 100:02d}" for y, m in self._mk_bank]
                + ["היום"]
            )
        else:
            x_labels = (
                [f"{m:02d}/{y % 100:02d}" for y, m in visible_mk]
                + ["היום"]
            )

        # Smart step: count only the month labels (not start/today)
        n_month_labels = len(x_labels) - (1 if include_start else 0) - 1
        label_step = max(1, _label_step_for(max(1, n_month_labels)))
        # Always show first and last label
        axis_x = _build_x_axis_labeled(x_labels, label_step)

        min_v = float(min(min(visible_bv), 0.0))
        max_v = float(max(max(visible_bv), 0.0))
        axis_y = _build_y_axis(max_v if max_v != 0.0 else 1000.0, min_v)

        series = QLineSeries()
        series.setName(self._series_name)
        try:
            series.setPointsVisible(False)
        except Exception:
            pass
        _apply_line_pen(series, self._series_color)
        for x_val, y_val in catmull_rom_spline_samples(visible_bv):
            series.append(x_val, y_val)
        self._chart.addSeries(series)

        lc = _label_color()
        try:
            axis_x.setLabelsBrush(lc)
            axis_y.setLabelsBrush(lc)
        except Exception:
            pass
        self._chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        for s in self._chart.series():
            try:
                s.attachAxis(axis_x)
                s.attachAxis(axis_y)
            except Exception:
                pass

        # month_keys for tooltip (pad with dummy for start/today)
        padded_keys = (
            ([(0, 0)] if include_start else [])
            + list(visible_mk)
            + [(0, 0)]
        )
        self._chart_view._shadows = [(series, self._series_color)]
        self._chart_view._tooltip_specs = [(series, self._series_name, list(visible_bv))]
        self._chart_view._month_keys = padded_keys
        self._chart_view._x_labels = x_labels

    def _clear_chart(self) -> None:
        if self._chart is None:
            return
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


def create_bank_history_chart_card(
    parent: QWidget,
    account: BankAccount | BudgetAccount,
    format_amount: Callable[[float], str],
    *,
    movements: Optional[List[BankMovement]] = None,
) -> QWidget:
    """Backward-compatible factory — returns a BankHistoryChartCard."""
    return BankHistoryChartCard(parent, account, format_amount, movements=movements)
