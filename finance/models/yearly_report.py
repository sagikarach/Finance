from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .bank_movement import BankMovement
from .bank_movement import MovementType

MonthKey = Tuple[int, int]


@dataclass(frozen=True)
class YearlyMovementSummary:
    year: int
    total_income: float
    total_outcome: float
    net_amount: float
    movement_count: int
    income_count: int
    outcome_count: int


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


@dataclass(frozen=True)
class CategoryYearlyBreakdown:
    category: str
    year: int
    total_amount: float
    movement_count: int
    is_income: bool


@dataclass(frozen=True)
class YearlyReport:
    year: int
    summary: YearlyMovementSummary
    category_breakdowns: List[CategoryYearlyBreakdown]
    movements: List[BankMovement]
    account_breakdowns: Dict[str, YearlyMovementSummary] = field(default_factory=dict)
    month_breakdowns: Dict[MonthKey, MonthlyInYearSummary] = field(default_factory=dict)


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
