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
            set(movement_types) if movement_types else None
        )

        movements: List[BankMovement] = []
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if type_set is not None and m.type not in type_set:
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
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                years.add(parse_iso_date(m.date).year)
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
            set(movement_types) if movement_types else None
        )

        out: Dict[str, List[float]] = defaultdict(lambda: [0.0] * 12)
        for m in all_movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if type_set is not None and m.type not in type_set:
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

    def _calculate_summary(
        self, movements: List[BankMovement], year: int
    ) -> YearlyMovementSummary:
        total_income = 0.0
        total_outcome = 0.0
        income_count = 0
        outcome_count = 0

        for m in movements:
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
