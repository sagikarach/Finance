from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional
import re


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
    s = str(value or "").strip()
    if not s:
        return datetime.min

    # Fast path: ISO-like formats.
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        pass

    # Common bank-export formats.
    try:
        return datetime.strptime(s, "%d/%m/%Y")
    except Exception:
        pass
    try:
        return datetime.strptime(s, "%d.%m.%Y")
    except Exception:
        pass

    # 2-digit year (e.g. 01/01/24 or 01.01.24)
    m = re.match(r"^\s*(\d{1,2})[/.](\d{1,2})[/.](\d{2})\s*$", s)
    if m:
        try:
            d = int(m.group(1))
            mo = int(m.group(2))
            yy = int(m.group(3))
            year = 2000 + yy  # assume 20xx for exports
            return datetime(year, mo, d)
        except Exception:
            return datetime.min

    # Missing year (e.g. 01/01 or 01.01) -> assume current year.
    m2 = re.match(r"^\s*(\d{1,2})[/.](\d{1,2})\s*$", s)
    if m2:
        try:
            d = int(m2.group(1))
            mo = int(m2.group(2))
            now = datetime.now()
            return datetime(int(now.year), mo, d)
        except Exception:
            return datetime.min

    return datetime.min


def latest_amount_from_history(history: Iterable[MoneySnapshot]) -> Optional[float]:
    snapshots = list(history)
    if not snapshots:
        return None
    snapshots.sort(key=lambda s: parse_iso_date(s.date))
    return float(snapshots[-1].amount)
