from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class MoneySnapshot:
    date: str
    amount: float


@dataclass(frozen=True)
class MoneyAccount:
    name: str
    amount: float
    is_liquid: bool
    history: List[MoneySnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.history:
            latest = latest_amount_from_history(self.history)
            if latest is not None:
                object.__setattr__(self, "amount", float(latest))


def compute_total_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.amount for a in accounts))


def compute_total_liquid_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.amount for a in accounts if a.is_liquid))


def parse_iso_date(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        try:
            return datetime.strptime(value, "%Y-%m-%d")
        except Exception:
            return datetime.min


def latest_amount_from_history(history: Iterable[MoneySnapshot]) -> Optional[float]:
    snapshots = list(history)
    if not snapshots:
        return None
    snapshots.sort(key=lambda s: parse_iso_date(s.date))
    return float(snapshots[-1].amount)
