from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from ..data.bank_movement_provider import BankMovementProvider
from .accounts import parse_iso_date
from .bank_movement import BankMovement, MovementType
from .yearly_report import (
    CategoryYearlyBreakdown,
    MonthTypeSummary,
    MonthlyInYearSummary,
    MonthKey,
    movement_type_to_bucket,
    YearlyMovementSummary,
    YearlyReport,
)


class YearlyReportService:
    def __init__(self, movement_provider: BankMovementProvider) -> None:
        self.movement_provider = movement_provider

    def get_yearly_report(
        self,
        year: int,
        account_names: Optional[List[str]] = None,
        movement_types: Optional[Set[MovementType]] = None,
    ) -> Optional[YearlyReport]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return None

        account_set: Optional[Set[str]] = set(account_names) if account_names else None
        type_set: Optional[Set[MovementType]] = (
            set(movement_types) if movement_types is not None else None
        )

        movements: List[BankMovement] = []
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if type_set is not None and m.type not in type_set:
                    continue
                if self._is_transfer(m):
                    continue
                dt = parse_iso_date(m.date)
                if dt.year != year:
                    continue
                movements.append(m)
            except Exception:
                continue

        if not movements:
            summary = YearlyMovementSummary(
                year=year,
                total_income=0.0,
                total_outcome=0.0,
                net_amount=0.0,
                movement_count=0,
                income_count=0,
                outcome_count=0,
            )
            return YearlyReport(
                year=year,
                summary=summary,
                category_breakdowns=[],
                movements=[],
                account_breakdowns={},
                month_breakdowns={},
            )

        movements_sorted = sorted(
            movements, key=lambda x: parse_iso_date(x.date), reverse=True
        )
        summary = self._calculate_summary(movements_sorted, year)
        category_breakdowns = self._calculate_category_breakdowns(
            movements_sorted, year
        )
        account_breakdowns = self._calculate_account_breakdowns(movements_sorted, year)
        month_breakdowns = self._calculate_month_breakdowns(movements_sorted, year)

        return YearlyReport(
            year=year,
            summary=summary,
            category_breakdowns=category_breakdowns,
            movements=movements_sorted,
            account_breakdowns=account_breakdowns,
            month_breakdowns=month_breakdowns,
        )

    def get_available_years(
        self, account_names: Optional[List[str]] = None
    ) -> List[int]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return []

        account_set: Optional[Set[str]] = set(account_names) if account_names else None
        years: Set[int] = set()
        from datetime import datetime as _dt
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                dt = parse_iso_date(m.date)
                if dt == _dt.min:
                    continue
                years.add(dt.year)
            except Exception:
                continue

        return sorted(years, reverse=True)

    def get_month_type_summaries(
        self,
        year: int,
        account_names: Optional[List[str]] = None,
    ) -> List[MonthTypeSummary]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return []

        account_set: Optional[Set[str]] = set(account_names) if account_names else None
        by_month: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )

        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if self._is_transfer(m):
                    continue
                dt = parse_iso_date(m.date)
                if dt.year != year:
                    continue
                bucket = movement_type_to_bucket(m.type)
                amount = float(m.amount)
                if amount >= 0:
                    by_month[dt.month]["income"][bucket] += amount
                else:
                    by_month[dt.month]["expense"][bucket] += abs(amount)
            except Exception:
                continue

        out: List[MonthTypeSummary] = []
        for month in sorted(by_month.keys()):
            income = by_month[month]["income"]
            expense = by_month[month]["expense"]
            out.append(
                MonthTypeSummary(
                    year=year,
                    month=month,
                    income_monthly=float(income.get("monthly", 0.0)),
                    income_yearly=float(income.get("yearly", 0.0)),
                    income_one_time=float(income.get("one_time", 0.0)),
                    expense_monthly=float(expense.get("monthly", 0.0)),
                    expense_yearly=float(expense.get("yearly", 0.0)),
                    expense_one_time=float(expense.get("one_time", 0.0)),
                )
            )

        return out

    def get_category_month_totals(
        self,
        year: int,
        *,
        is_income: bool,
        movement_types: Optional[Set[MovementType]] = None,
        account_names: Optional[List[str]] = None,
    ) -> Dict[str, List[float]]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return {}

        account_set: Optional[Set[str]] = set(account_names) if account_names else None
        type_set: Optional[Set[MovementType]] = (
            set(movement_types) if movement_types is not None else None
        )

        out: Dict[str, List[float]] = defaultdict(lambda: [0.0] * 12)
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if type_set is not None and m.type not in type_set:
                    continue
                if self._is_transfer(m):
                    continue
                dt = parse_iso_date(m.date)
                if dt.year != year:
                    continue
                amount = float(m.amount)
                if is_income and amount <= 0:
                    continue
                if (not is_income) and amount >= 0:
                    continue
                category = m.category or "שונות"
                idx = max(0, min(11, dt.month - 1))
                out[category][idx] += abs(amount)
            except Exception:
                continue

        return dict(out)

    # ──────────────────────────────────────── sliding-window helpers ──

    _HEB_MONTHS = [
        "ינו", "פבר", "מרץ", "אפר", "מאי", "יוני",
        "יול", "אוג", "ספט", "אוק", "נוב", "דצמ",
    ]

    def _build_window_keys(self, months: int) -> List[Tuple[int, int]]:
        """Return (year, month) keys for the last *months* calendar months.

        If months == 0 all months that appear in stored movements are returned.
        """
        from datetime import date as _date, datetime as _dt

        if months <= 0:
            try:
                all_mvs = self.movement_provider.list_movements()
            except Exception:
                return []
            keys_seen: Set[Tuple[int, int]] = set()
            for mv in all_mvs:
                try:
                    dt = parse_iso_date(mv.date)
                    if dt != _dt.min:
                        keys_seen.add((dt.year, dt.month))
                except Exception:
                    continue
            return sorted(keys_seen)

        today = _date.today()
        keys: List[Tuple[int, int]] = []
        y, m = today.year, today.month
        for _ in range(months):
            keys.append((y, m))
            m -= 1
            if m < 1:
                m = 12
                y -= 1
        keys.reverse()
        return keys

    def get_window_nets(
        self, months: int
    ) -> List[Tuple[str, float]]:
        """Return [(label, net_amount)] for each month in the window."""
        from datetime import datetime as _dt

        window = self._build_window_keys(months)
        if not window:
            return []
        try:
            all_mvs = list(self.movement_provider.list_movements())
        except Exception:
            return []

        nets: Dict[Tuple[int, int], float] = defaultdict(float)
        for mv in all_mvs:
            try:
                if self._is_transfer(mv):
                    continue
                dt = parse_iso_date(mv.date)
                if dt == _dt.min:
                    continue
                nets[(dt.year, dt.month)] += float(mv.amount)
            except Exception:
                continue

        result: List[Tuple[str, float]] = []
        for yr, mo in window:
            label = f"{self._HEB_MONTHS[mo - 1]} {yr % 100:02d}"
            result.append((label, nets.get((yr, mo), 0.0)))
        return result

    def get_window_totals(
        self, months: int
    ) -> Tuple[float, float, float]:
        """Return (total_income, total_expense, net) for the window."""
        from datetime import datetime as _dt

        window_set = set(self._build_window_keys(months))
        if not window_set:
            return 0.0, 0.0, 0.0
        try:
            all_mvs = list(self.movement_provider.list_movements())
        except Exception:
            return 0.0, 0.0, 0.0

        income = 0.0
        expense = 0.0
        for mv in all_mvs:
            try:
                if self._is_transfer(mv):
                    continue
                dt = parse_iso_date(mv.date)
                if dt == _dt.min:
                    continue
                if (dt.year, dt.month) not in window_set:
                    continue
                amount = float(mv.amount)
                if amount > 0:
                    income += amount
                elif amount < 0:
                    expense += abs(amount)
            except Exception:
                continue
        return income, expense, income - expense

    def get_window_category_totals(
        self,
        months: int,
        *,
        is_income: bool,
        movement_types: Optional[Set[MovementType]] = None,
        account_names: Optional[List[str]] = None,
    ) -> Tuple[Dict[str, List[float]], List[str]]:
        """Like get_category_month_totals but for a sliding window.

        Returns (category_dict, month_labels).
        """
        from datetime import datetime as _dt

        window = self._build_window_keys(months)
        if not window:
            return {}, []
        n = len(window)
        key_to_idx: Dict[Tuple[int, int], int] = {k: i for i, k in enumerate(window)}

        try:
            all_mvs = list(self.movement_provider.list_movements())
        except Exception:
            return {}, []

        account_set: Optional[Set[str]] = set(account_names) if account_names else None
        type_set: Optional[Set[MovementType]] = (
            set(movement_types) if movement_types is not None else None
        )

        out: Dict[str, List[float]] = defaultdict(lambda: [0.0] * n)
        for mv in all_mvs:
            try:
                if account_set is not None and mv.account_name not in account_set:
                    continue
                if type_set is not None and mv.type not in type_set:
                    continue
                if self._is_transfer(mv):
                    continue
                dt = parse_iso_date(mv.date)
                key = (dt.year, dt.month)
                if key not in key_to_idx:
                    continue
                amount = float(mv.amount)
                if is_income and amount <= 0:
                    continue
                if (not is_income) and amount >= 0:
                    continue
                category = mv.category or "שונות"
                out[category][key_to_idx[key]] += abs(amount)
            except Exception:
                continue

        labels = [
            f"{self._HEB_MONTHS[mo - 1]} {yr % 100:02d}" for yr, mo in window
        ]
        return dict(out), labels

    def _calculate_summary(
        self, movements: List[BankMovement], year: int
    ) -> YearlyMovementSummary:
        total_income = 0.0
        total_outcome = 0.0
        income_count = 0
        outcome_count = 0

        for m in movements:
            try:
                if self._is_transfer(m):
                    continue
                amount = float(m.amount)
                if amount > 0:
                    total_income += amount
                    income_count += 1
                elif amount < 0:
                    total_outcome += abs(amount)
                    outcome_count += 1
            except Exception:
                continue

        return YearlyMovementSummary(
            year=year,
            total_income=total_income,
            total_outcome=total_outcome,
            net_amount=total_income - total_outcome,
            movement_count=len(movements),
            income_count=income_count,
            outcome_count=outcome_count,
        )

    def _calculate_category_breakdowns(
        self, movements: List[BankMovement], year: int
    ) -> List[CategoryYearlyBreakdown]:
        category_data: Dict[Tuple[str, bool], List[float]] = defaultdict(list)
        for m in movements:
            try:
                if self._is_transfer(m):
                    continue
                amount = float(m.amount)
                is_income = amount > 0
                category = m.category or "שונות"
                category_data[(category, is_income)].append(abs(amount))
            except Exception:
                continue

        out: List[CategoryYearlyBreakdown] = []
        for (category, is_income), amounts in category_data.items():
            out.append(
                CategoryYearlyBreakdown(
                    category=category,
                    year=year,
                    total_amount=sum(amounts),
                    movement_count=len(amounts),
                    is_income=is_income,
                )
            )

        out.sort(key=lambda x: (not x.is_income, -x.total_amount))
        return out

    def _is_transfer(self, movement: BankMovement) -> bool:
        try:
            if bool(getattr(movement, "is_transfer", False)):
                return True
        except Exception:
            pass
        try:
            if str(getattr(movement, "category", "") or "").strip() == "העברה":
                return True
        except Exception:
            pass
        return False

    def _calculate_account_breakdowns(
        self, movements: List[BankMovement], year: int
    ) -> Dict[str, YearlyMovementSummary]:
        by_account: Dict[str, List[BankMovement]] = defaultdict(list)
        for m in movements:
            by_account[m.account_name].append(m)

        out: Dict[str, YearlyMovementSummary] = {}
        for account_name, items in by_account.items():
            out[account_name] = self._calculate_summary(items, year)
        return out

    def _calculate_month_breakdowns(
        self, movements: List[BankMovement], year: int
    ) -> Dict[MonthKey, MonthlyInYearSummary]:
        by_month: Dict[MonthKey, List[BankMovement]] = defaultdict(list)
        for m in movements:
            try:
                dt = parse_iso_date(m.date)
                by_month[(dt.year, dt.month)].append(m)
            except Exception:
                continue

        out: Dict[MonthKey, MonthlyInYearSummary] = {}
        for (y, month), items in by_month.items():
            total_income = 0.0
            total_outcome = 0.0
            income_count = 0
            outcome_count = 0
            for m in items:
                try:
                    amount = float(m.amount)
                    if amount > 0:
                        total_income += amount
                        income_count += 1
                    elif amount < 0:
                        total_outcome += abs(amount)
                        outcome_count += 1
                except Exception:
                    continue

            out[(y, month)] = MonthlyInYearSummary(
                year=y,
                month=month,
                total_income=total_income,
                total_outcome=total_outcome,
                net_amount=total_income - total_outcome,
                movement_count=len(items),
                income_count=income_count,
                outcome_count=outcome_count,
            )

        return out


# ---------------------------------------------------------------------------
# Naive mathematical forecast helpers (no external dependencies)
# ---------------------------------------------------------------------------

def _linear_trend(values: List[float]) -> float:
    """Return per-step slope from simple linear regression over *values*."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def forecast_net(history: List[Tuple[str, float]], horizon: int = 6) -> List[float]:
    """Forecast net cash-flow using recent average + capped linear trend."""
    if not history:
        return [0.0] * horizon
    values = [v for _, v in history]
    recent = values[-12:]
    avg = sum(recent) / len(recent)
    slope = _linear_trend(recent)
    if avg != 0:
        cap = abs(avg) * 0.10
        slope = max(-cap, min(cap, slope))
    last = recent[-1]
    return [last + slope * (i + 1) for i in range(horizon)]


def forecast_category_totals(
    category_history: Dict[str, List[float]],
    horizon: int = 6,
) -> Dict[str, List[float]]:
    """Forecast per-category monthly totals using average + capped trend."""
    result: Dict[str, List[float]] = {}
    for cat, values in category_history.items():
        if not values:
            result[cat] = [0.0] * horizon
            continue
        recent = values[-6:]
        avg = sum(recent) / len(recent)
        slope = _linear_trend(recent)
        if avg != 0:
            cap = abs(avg) * 0.08
            slope = max(-cap, min(cap, slope))
        last = recent[-1]
        result[cat] = [max(0.0, last + slope * (i + 1)) for i in range(horizon)]
    return result


def forecast_savings_balance(
    history: List[float],
    current_balance: float,
    horizon: int = 6,
) -> List[float]:
    """Forecast a savings account balance using linear extrapolation."""
    all_vals = list(history) + [current_balance]
    recent = all_vals[-6:] if len(all_vals) >= 6 else all_vals
    slope = _linear_trend(recent)
    if current_balance != 0:
        cap = abs(current_balance) * 0.05
        slope = max(-cap, min(cap, slope))
    return [max(0.0, current_balance + slope * (i + 1)) for i in range(horizon)]
