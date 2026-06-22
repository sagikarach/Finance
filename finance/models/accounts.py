from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional
import re


@dataclass(frozen=True)
class MoneySnapshot:
    date: str
    amount: float

    def when(self) -> datetime:
        """The snapshot's date parsed to a ``datetime`` (tolerant of formats)."""
        return parse_iso_date(self.date)

    def is_future(self, now: Optional[datetime] = None) -> bool:
        """True if this snapshot is dated after ``now`` (default: now). Future
        snapshots are projections or date typos and must not count as current."""
        return self.when() > (now if now is not None else datetime.now())


def _latest_non_future_snapshot(
    history: Iterable[MoneySnapshot], now: Optional[datetime] = None
) -> Optional[MoneySnapshot]:
    """The most recent snapshot that is not in the future. Falls back to the
    latest overall only if every snapshot is future-dated; ``None`` if empty."""
    snapshots = list(history)
    if not snapshots:
        return None
    ref = now if now is not None else datetime.now()
    pool = [s for s in snapshots if not s.is_future(ref)] or snapshots
    return max(pool, key=lambda s: s.when())


@dataclass(frozen=True)
class Savings:
    name: str
    amount: float
    history: List[MoneySnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        latest = _latest_non_future_snapshot(self.history)
        if latest is not None:
            object.__setattr__(self, "amount", float(latest.amount))

    def last_changed(self) -> datetime:
        """When this envelope last changed (latest non-future snapshot date)."""
        latest = _latest_non_future_snapshot(self.history)
        return latest.when() if latest is not None else datetime.min


@dataclass(frozen=True)
class MoneyAccount:
    name: str
    total_amount: float
    is_liquid: bool

    @property
    def is_savings(self) -> bool:
        return False

    def current_balance(self) -> float:
        return float(self.total_amount)

    def recalculated(
        self, ledger: "MovementLedger", today: str
    ) -> "MoneyAccount":
        """Return a copy with its balance recomputed from ``ledger``.

        Base behaviour: unchanged. Subclasses whose balance is derived from
        movements (bank, budget) override this; savings are persisted directly
        and so keep the base no-op.
        """
        return self


@dataclass(frozen=True)
class BankAccount(MoneyAccount):
    history: List[MoneySnapshot] = field(default_factory=list)
    active: bool = False
    baseline_amount: float = 0.0

    def __post_init__(self) -> None:
        latest = _latest_non_future_snapshot(self.history)
        if latest is not None:
            object.__setattr__(self, "total_amount", float(latest.amount))

    def recalculated(self, ledger: "MovementLedger", today: str) -> "BankAccount":
        balance = float(self.baseline_amount) + ledger.total_for(self.name)
        return BankAccount(
            name=self.name,
            total_amount=balance,
            is_liquid=self.is_liquid,
            history=_with_today_snapshot(self.history, today, balance),
            active=self.active,
            baseline_amount=float(self.baseline_amount),
        )


@dataclass(frozen=True)
class BudgetAccount(MoneyAccount):
    history: List[MoneySnapshot] = field(default_factory=list)
    active: bool = False
    monthly_budget: float = 0.0
    reset_day: int = 1
    last_reset_period: str = ""

    def __post_init__(self) -> None:
        latest = _latest_non_future_snapshot(self.history)
        if latest is not None:
            object.__setattr__(self, "total_amount", float(latest.amount))

    def recalculated(self, ledger: "MovementLedger", today: str) -> "BudgetAccount":
        from .budget_period import budget_period_end_key, current_budget_period_end_key

        reset_day = min(max(int(self.reset_day or 1), 1), 28)
        cur_key = current_budget_period_end_key(reset_day)
        spent = 0.0
        for m in ledger.movements_for(self.name):
            if bool(getattr(m, "is_transfer", False)):
                continue
            amt = float(getattr(m, "amount", 0.0) or 0.0)
            if amt >= 0:
                continue
            key = budget_period_end_key(str(getattr(m, "date", "") or ""), reset_day)
            if key is None or key != cur_key:
                continue
            spent += abs(amt)
        remaining = max(float(self.monthly_budget or 0.0) - spent, 0.0)
        return BudgetAccount(
            name=self.name,
            total_amount=remaining,
            is_liquid=False,
            history=_with_today_snapshot(self.history, today, remaining),
            active=self.active,
            monthly_budget=float(self.monthly_budget or 0.0),
            reset_day=int(self.reset_day or 1),
            last_reset_period=str(self.last_reset_period or ""),
        )


@dataclass(frozen=True)
class SavingsAccount(MoneyAccount):
    savings: List[Savings] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.savings:
            total = sum(s.amount for s in self.savings)
            object.__setattr__(self, "total_amount", float(total))

    @property
    def is_savings(self) -> bool:
        return True

    def merged_with_local(self, local: "SavingsAccount") -> "SavingsAccount":
        """Merge this (remote) account with the ``local`` copy during a pull,
        keeping per envelope whichever side changed most recently. A tie
        favours local, so an unsynced local change is never clobbered by stale
        remote data. New envelopes on either side are preserved."""
        local_by_name = {e.name: e for e in local.savings}
        remote_by_name = {e.name: e for e in self.savings}
        merged: List[Savings] = []
        for r in self.savings:
            l = local_by_name.get(r.name)
            if l is None or r.last_changed() > l.last_changed():
                merged.append(r)
            else:
                merged.append(l)  # local newer or tied -> keep local
        for l in local.savings:
            if l.name not in remote_by_name:
                merged.append(l)
        return SavingsAccount(
            name=self.name,
            total_amount=0.0,
            is_liquid=self.is_liquid,
            savings=merged,
        )


class MovementLedger:
    """Aggregates bank movements for balance recalculation. Duck-typed: each
    movement only needs ``account_name`` and ``amount`` (and optionally
    ``is_transfer`` / ``date``)."""

    def __init__(self, movements: Iterable) -> None:
        self._by_name: dict[str, list] = {}
        for m in movements:
            name = getattr(m, "account_name", "")
            self._by_name.setdefault(name, []).append(m)

    def total_for(self, name: str) -> float:
        total = 0.0
        for m in self._by_name.get(name, []):
            try:
                total += float(getattr(m, "amount", 0.0) or 0.0)
            except Exception:
                pass
        return total

    def movements_for(self, name: str) -> list:
        return list(self._by_name.get(name, []))


def _with_today_snapshot(
    history: List[MoneySnapshot], today: str, amount: float
) -> List[MoneySnapshot]:
    """Return ``history`` with today's balance recorded: replace the trailing
    snapshot if it is already dated ``today``, otherwise append a new one."""
    new_history = list(history)
    if not today:
        return new_history
    if new_history and str(new_history[-1].date) == str(today):
        new_history[-1] = MoneySnapshot(date=today, amount=amount)
    else:
        new_history.append(MoneySnapshot(date=today, amount=amount))
    return new_history


def compute_total_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts))


def compute_total_liquid_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts if a.is_liquid))


def compute_savings_account_total_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(sum(a.total_amount for a in accounts if a.is_savings))


def compute_savings_account_liquid_amount(accounts: Iterable[MoneyAccount]) -> float:
    return float(
        sum(a.total_amount for a in accounts if a.is_savings and a.is_liquid)
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


def to_iso_date(value: str) -> str:
    """Normalize a date string to ISO ``YYYY-MM-DD``.

    Reuses :func:`parse_iso_date` so every format the app already tolerates
    (DD/MM/YYYY, DD.MM.YYYY, 2-digit years, ...) is accepted. Returns the
    stripped original unchanged if it cannot be parsed, so an unexpected
    input is never silently discarded.
    """
    s = str(value or "").strip()
    if not s:
        return ""
    dt = parse_iso_date(s)
    if dt == datetime.min:
        return s
    return dt.date().isoformat()


def latest_amount_from_history(history: Iterable[MoneySnapshot]) -> Optional[float]:
    """The current balance implied by ``history``: the amount of the most recent
    non-future snapshot. Thin wrapper over :func:`_latest_non_future_snapshot`
    kept for callers that work with a bare history list."""
    latest = _latest_non_future_snapshot(history)
    return float(latest.amount) if latest is not None else None
