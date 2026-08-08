from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

from .accounts import parse_iso_date
from .bank_movement import BankMovement, MovementType
from ..utils.safe import PARSE_ERRORS


def _is_in_month(date_str: str, year: int, month: int) -> bool:
    try:
        dt = parse_iso_date(date_str)
        return dt.year == year and dt.month == month
    except PARSE_ERRORS:
        return False


@dataclass(frozen=True)
class MonthlyMovementSummary:
    year: int
    month: int
    total_income: float
    total_outcome: float
    net_amount: float
    movement_count: int
    income_count: int
    outcome_count: int

    @property
    def month_key(self) -> tuple[int, int]:
        return (self.year, self.month)

    @classmethod
    def from_movements(
        cls, movements: List[BankMovement], year: int, month: int
    ) -> "MonthlyMovementSummary":
        total_income = 0.0
        total_outcome = 0.0
        income_count = 0
        outcome_count = 0
        for movement in movements:
            try:
                amount = float(movement.amount)
            except PARSE_ERRORS:
                continue
            if amount > 0:
                total_income += amount
                income_count += 1
            elif amount < 0:
                total_outcome += abs(amount)
                outcome_count += 1
        return cls(
            year=year,
            month=month,
            total_income=total_income,
            total_outcome=total_outcome,
            net_amount=total_income - total_outcome,
            movement_count=len(movements),
            income_count=income_count,
            outcome_count=outcome_count,
        )


@dataclass(frozen=True)
class CategoryMonthlyBreakdown:
    category: str
    year: int
    month: int
    total_amount: float
    movement_count: int
    is_income: bool

    @property
    def month_key(self) -> tuple[int, int]:
        return (self.year, self.month)

    @staticmethod
    def breakdowns_for(
        movements: List[BankMovement], year: int, month: int
    ) -> List["CategoryMonthlyBreakdown"]:
        category_data: Dict[tuple[str, bool], List[float]] = defaultdict(list)
        for movement in movements:
            try:
                amount = float(movement.amount)
            except PARSE_ERRORS:
                continue
            category = movement.category or "שונות"
            category_data[(category, amount > 0)].append(abs(amount))

        breakdowns = [
            CategoryMonthlyBreakdown(
                category=category,
                year=year,
                month=month,
                total_amount=sum(amounts),
                movement_count=len(amounts),
                is_income=is_income,
            )
            for (category, is_income), amounts in category_data.items()
        ]
        breakdowns.sort(key=lambda x: (not x.is_income, -x.total_amount))
        return breakdowns


@dataclass(frozen=True)
class MonthlyReport:
    year: int
    month: int
    summary: MonthlyMovementSummary
    category_breakdowns: List[CategoryMonthlyBreakdown]
    movements: List[BankMovement]
    account_breakdowns: Dict[str, MonthlyMovementSummary]

    @property
    def month_key(self) -> tuple[int, int]:
        return (self.year, self.month)

    @classmethod
    def build(
        cls,
        movements: List[BankMovement],
        year: int,
        month: int,
        account_names: Optional[List[str]] = None,
    ) -> "MonthlyReport":
        """Build the report for ``year``/``month`` from ``movements``: keep only
        this month's recurring (MONTHLY) non-transfer movements (optionally
        limited to ``account_names``), then summarize by total, category, and
        account."""
        account_set = set(account_names) if account_names else None
        selected = [
            m
            for m in movements
            if _is_in_month(m.date, year, month)
            and m.type == MovementType.MONTHLY
            and not m.counts_as_transfer
            and (account_set is None or m.account_name in account_set)
        ]

        by_account: Dict[str, List[BankMovement]] = defaultdict(list)
        for m in selected:
            by_account[m.account_name].append(m)

        return cls(
            year=year,
            month=month,
            summary=MonthlyMovementSummary.from_movements(selected, year, month),
            category_breakdowns=CategoryMonthlyBreakdown.breakdowns_for(
                selected, year, month
            ),
            movements=selected,
            account_breakdowns={
                name: MonthlyMovementSummary.from_movements(ms, year, month)
                for name, ms in by_account.items()
            },
        )
