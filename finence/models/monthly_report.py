from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .bank_movement import BankMovement


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
