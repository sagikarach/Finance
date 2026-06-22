from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .accounts import parse_iso_date
from .bank_movement import BankMovement
from .bank_movement import MovementType

MonthKey = Tuple[int, int]


def _income_outcome_counts(movements: List[BankMovement]) -> tuple[float, float, int, int]:
    total_income = 0.0
    total_outcome = 0.0
    income_count = 0
    outcome_count = 0
    for m in movements:
        try:
            amount = float(m.amount)
        except Exception:
            continue
        if amount > 0:
            total_income += amount
            income_count += 1
        elif amount < 0:
            total_outcome += abs(amount)
            outcome_count += 1
    return total_income, total_outcome, income_count, outcome_count


@dataclass(frozen=True)
class YearlyMovementSummary:
    year: int
    total_income: float
    total_outcome: float
    net_amount: float
    movement_count: int
    income_count: int
    outcome_count: int

    @classmethod
    def from_movements(
        cls, movements: List[BankMovement], year: int
    ) -> "YearlyMovementSummary":
        ti, to, ic, oc = _income_outcome_counts(movements)
        return cls(
            year=year,
            total_income=ti,
            total_outcome=to,
            net_amount=ti - to,
            movement_count=len(movements),
            income_count=ic,
            outcome_count=oc,
        )


@dataclass(frozen=True)
class MonthlyInYearSummary:
    year: int
    month: int
    total_income: float
    total_outcome: float
    net_amount: float
    movement_count: int
    income_count: int
    outcome_count: int

    @property
    def month_key(self) -> MonthKey:
        return (self.year, self.month)

    @classmethod
    def from_movements(
        cls, movements: List[BankMovement], year: int, month: int
    ) -> "MonthlyInYearSummary":
        ti, to, ic, oc = _income_outcome_counts(movements)
        return cls(
            year=year,
            month=month,
            total_income=ti,
            total_outcome=to,
            net_amount=ti - to,
            movement_count=len(movements),
            income_count=ic,
            outcome_count=oc,
        )


@dataclass(frozen=True)
class CategoryYearlyBreakdown:
    category: str
    year: int
    total_amount: float
    movement_count: int
    is_income: bool

    @staticmethod
    def breakdowns_for(
        movements: List[BankMovement], year: int
    ) -> List["CategoryYearlyBreakdown"]:
        data: Dict[Tuple[str, bool], List[float]] = defaultdict(list)
        for m in movements:
            try:
                amount = float(m.amount)
            except Exception:
                continue
            category = m.category or "שונות"
            data[(category, amount > 0)].append(abs(amount))
        out = [
            CategoryYearlyBreakdown(
                category=category,
                year=year,
                total_amount=sum(amounts),
                movement_count=len(amounts),
                is_income=is_income,
            )
            for (category, is_income), amounts in data.items()
        ]
        out.sort(key=lambda x: (not x.is_income, -x.total_amount))
        return out


@dataclass(frozen=True)
class YearlyReport:
    year: int
    summary: YearlyMovementSummary
    category_breakdowns: List[CategoryYearlyBreakdown]
    movements: List[BankMovement]
    account_breakdowns: Dict[str, YearlyMovementSummary] = field(default_factory=dict)
    month_breakdowns: Dict[MonthKey, MonthlyInYearSummary] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        movements: List[BankMovement],
        year: int,
        account_names: Optional[List[str]] = None,
        movement_types: Optional[Set[MovementType]] = None,
    ) -> "YearlyReport":
        """Build the year's report from ``movements``: keep that year's
        non-transfer movements (optionally limited to ``account_names`` and
        ``movement_types``), then summarize by total, category, account, month."""
        account_set = set(account_names) if account_names else None
        type_set = set(movement_types) if movement_types is not None else None

        selected: List[BankMovement] = []
        for m in movements:
            try:
                if account_set is not None and m.account_name not in account_set:
                    continue
                if type_set is not None and m.type not in type_set:
                    continue
                if m.counts_as_transfer:
                    continue
                if parse_iso_date(m.date).year != year:
                    continue
                selected.append(m)
            except Exception:
                continue
        selected.sort(key=lambda x: parse_iso_date(x.date), reverse=True)

        by_account: Dict[str, List[BankMovement]] = defaultdict(list)
        for m in selected:
            by_account[m.account_name].append(m)

        by_month: Dict[MonthKey, List[BankMovement]] = defaultdict(list)
        for m in selected:
            try:
                dt = parse_iso_date(m.date)
                by_month[(dt.year, dt.month)].append(m)
            except Exception:
                continue

        return cls(
            year=year,
            summary=YearlyMovementSummary.from_movements(selected, year),
            category_breakdowns=CategoryYearlyBreakdown.breakdowns_for(selected, year),
            movements=selected,
            account_breakdowns={
                name: YearlyMovementSummary.from_movements(ms, year)
                for name, ms in by_account.items()
            },
            month_breakdowns={
                key: MonthlyInYearSummary.from_movements(ms, key[0], key[1])
                for key, ms in by_month.items()
            },
        )


@dataclass(frozen=True)
class MonthTypeSummary:
    year: int
    month: int
    income_monthly: float
    income_yearly: float
    income_one_time: float
    expense_monthly: float
    expense_yearly: float
    expense_one_time: float

    @property
    def net_balance(self) -> float:
        return (self.income_monthly + self.income_yearly + self.income_one_time) - (
            self.expense_monthly + self.expense_yearly + self.expense_one_time
        )

    @property
    def month_key(self) -> MonthKey:
        return (self.year, self.month)


def movement_type_to_bucket(movement_type: MovementType) -> str:
    if movement_type == MovementType.MONTHLY:
        return "monthly"
    if movement_type == MovementType.YEARLY:
        return "yearly"
    return "one_time"
