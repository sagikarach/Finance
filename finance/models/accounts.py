from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class MoneySnapshot:
    date: str
    amount: float


@dataclass(frozen=True)
class Savings:
    name: str
    amount: float
    history: List[MoneySnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.history:
            latest = latest_amount_from_history(self.history)
            if latest is not None:
                object.__setattr__(self, "amount", float(latest))


@dataclass(frozen=True)
class MoneyAccount:
    name: str
    total_amount: float
    is_liquid: bool


@dataclass(frozen=True)
class BankAccount(MoneyAccount):
    history: List[MoneySnapshot] = field(default_factory=list)
    active: bool = False
    baseline_amount: float = 0.0

    def __post_init__(self) -> None:
        if self.history:
            latest = latest_amount_from_history(self.history)
            if latest is not None:
                object.__setattr__(self, "total_amount", float(latest))


@dataclass(frozen=True)
class BudgetAccount(MoneyAccount):
    history: List[MoneySnapshot] = field(default_factory=list)
    active: bool = False
    monthly_budget: float = 0.0
    reset_day: int = 1
    last_reset_period: str = ""

    def __post_init__(self) -> None:
        if self.history:
            latest = latest_amount_from_history(self.history)
            if latest is not None:
                object.__setattr__(self, "total_amount", float(latest))


@dataclass(frozen=True)
class SavingsAccount(MoneyAccount):
    savings: List[Savings] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.savings:
            total = sum(s.amount for s in self.savings)
            object.__setattr__(self, "total_amount", float(total))


def compute_total_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts))


def compute_total_liquid_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts if a.is_liquid))


def compute_savings_account_total_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts if isinstance(a, SavingsAccount)))


def compute_savings_account_liquid_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(
        sum(
            a.total_amount
            for a in accounts
            if isinstance(a, SavingsAccount) and a.is_liquid
        )
    )


def parse_iso_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            try:
                return datetime.strptime(value, "%d/%m/%Y")
            except Exception:
                try:
                    return datetime.strptime(value, "%d.%m.%Y")
                except Exception:
                    return datetime.min


def latest_amount_from_history(history: Iterable[MoneySnapshot]) -> Optional[float]:
    snapshots = list(history)
    if not snapshots:
        return None
    snapshots.sort(key=lambda s: parse_iso_date(s.date))
    return float(snapshots[-1].amount)


