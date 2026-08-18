from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional
from ..utils.safe import PARSE_ERRORS
# Re-exported for the many callers that import them from ``accounts``; the logic
# lives in the leaf ``utils.dates`` module to keep the models free of a cycle.
from ..utils.dates import parse_iso_date, to_iso_date  # noqa: F401
from .bank_movement import counts_as_transfer


@dataclass(frozen=True)
class MoneySnapshot:
    date: str
    amount: float

    def __post_init__(self) -> None:
        # Canonicalize on construction so every stored snapshot date is ISO,
        # regardless of the source format. Frozen dataclass -> setattr bypass.
        object.__setattr__(self, "date", to_iso_date(self.date))

    def when(self) -> datetime:
        """The snapshot's date parsed to a ``datetime`` (tolerant of formats)."""
        return parse_iso_date(self.date)

    def is_future(self, now: Optional[datetime] = None) -> bool:
        """True if this snapshot is dated after ``now`` (default: now). Future
        snapshots are projections or date typos and must not count as current."""
        return self.when() > (now if now is not None else datetime.now())

    def to_dict(self) -> dict:
        return {"date": self.date, "amount": self.amount}

    @classmethod
    def from_dict(cls, d: dict) -> "MoneySnapshot":
        return cls(date=str(d.get("date", "")), amount=float(d.get("amount", 0.0)))


def _latest_non_future_snapshot(
    history: Iterable[MoneySnapshot], now: Optional[datetime] = None
) -> Optional[MoneySnapshot]:
    """The most recent snapshot that is not in the future. Falls back to the
    latest overall only if every snapshot is future-dated; ``None`` if empty."""
    snapshots = list(history)
    if not snapshots:
        return None
    ref = now if now is not None else datetime.now()
    pool = [s for s in snapshots if not s.is_future(ref)] or list(snapshots)
    # Stable sort then take the last: when several snapshots share the latest
    # date, the one recorded last (latest in input order) wins — matching how
    # balances are appended within a day (e.g. a same-day recalc supersedes
    # earlier same-day points).
    pool = sorted(pool, key=lambda s: s.when())
    return pool[-1]


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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "amount": self.amount,
            "history": [s.to_dict() for s in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Savings":
        return cls(
            name=str(d.get("name", "")).strip(),
            amount=float(d.get("amount", 0.0) or 0.0),
            history=_history_from_dicts(d.get("history", [])),
        )


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

    def to_storage_dict(self) -> dict:
        return {
            "name": self.name,
            "is_liquid": self.is_liquid,
            "total_amount": self.total_amount,
            "active": bool(self.active),
            "history": [s.to_dict() for s in self.history],
            "baseline_amount": float(self.baseline_amount or 0.0),
        }

    def to_remote_dict(self) -> dict:
        # Bank balances are rebuilt from movements on pull, so the remote
        # snapshot carries only structure (no history/total).
        return {
            "kind": "bank",
            "name": self.name,
            "is_liquid": bool(self.is_liquid),
            "active": bool(self.active),
            "baseline_amount": float(self.baseline_amount or 0.0),
        }

    @classmethod
    def from_storage_dict(cls, item: dict) -> "BankAccount":
        return cls(
            name=str(item.get("name", "")).strip(),
            total_amount=float(item.get("total_amount", 0.0) or 0.0),
            is_liquid=bool(item.get("is_liquid", False)),
            history=_history_from_dicts(item.get("history", [])),
            active=bool(item.get("active", False)),
            baseline_amount=float(item.get("baseline_amount", 0.0) or 0.0),
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
            if counts_as_transfer(m):
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

    def to_storage_dict(self) -> dict:
        return {
            "name": self.name,
            "is_liquid": self.is_liquid,
            "total_amount": self.total_amount,
            "active": bool(self.active),
            "history": [s.to_dict() for s in self.history],
            "kind": "budget",
            "monthly_budget": float(self.monthly_budget),
            "reset_day": int(self.reset_day),
            "last_reset_period": str(self.last_reset_period or ""),
        }

    def to_remote_dict(self) -> dict:
        return {
            "kind": "budget",
            "name": self.name,
            "is_liquid": False,
            "active": bool(self.active),
            "monthly_budget": float(self.monthly_budget or 0.0),
            "reset_day": int(self.reset_day or 1),
            "last_reset_period": str(self.last_reset_period or ""),
            "total_amount": float(self.total_amount or 0.0),
            "history": [s.to_dict() for s in self.history],
        }

    @classmethod
    def from_storage_dict(cls, item: dict) -> "BudgetAccount":
        return cls(
            name=str(item.get("name", "")).strip(),
            total_amount=float(item.get("total_amount", 0.0) or 0.0),
            is_liquid=False,
            history=_history_from_dicts(item.get("history", [])),
            active=bool(item.get("active", False)),
            monthly_budget=float(item.get("monthly_budget", 0.0) or 0.0),
            reset_day=int(item.get("reset_day", 1) or 1),
            last_reset_period=str(item.get("last_reset_period", "") or "").strip(),
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

    def to_storage_dict(self) -> dict:
        return {
            "name": self.name,
            "is_liquid": self.is_liquid,
            "total_amount": self.total_amount,
            "savings": [s.to_dict() for s in self.savings],
        }

    def to_remote_dict(self) -> dict:
        # Matches the previous asdict(SavingsAccount) shape used on the remote.
        return {
            "name": self.name,
            "total_amount": self.total_amount,
            "is_liquid": self.is_liquid,
            "savings": [s.to_dict() for s in self.savings],
        }

    @classmethod
    def from_storage_dict(cls, item: dict) -> "SavingsAccount":
        savings: List[Savings] = []
        raw = item.get("savings", [])
        if isinstance(raw, list):
            for sd in raw:
                try:
                    if not str(sd.get("name", "")).strip():
                        continue
                    savings.append(Savings.from_dict(sd))
                except PARSE_ERRORS:
                    continue
        return cls(
            name=str(item.get("name", "")).strip(),
            total_amount=float(item.get("total_amount", 0.0) or 0.0),
            is_liquid=bool(item.get("is_liquid", False)),
            savings=savings,
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
            except PARSE_ERRORS:
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


def _history_from_dicts(raw) -> List[MoneySnapshot]:
    """Tolerantly parse a list of {date, amount} dicts into snapshots, skipping
    malformed rows (matches the providers' historical leniency)."""
    out: List[MoneySnapshot] = []
    if isinstance(raw, list):
        for row in raw:
            try:
                out.append(MoneySnapshot.from_dict(row))
            except PARSE_ERRORS:
                continue
    return out


def bank_entry_from_storage_dict(item: dict) -> Optional[MoneyAccount]:
    """Build a bank-file account (BankAccount or BudgetAccount) from a stored
    dict, dispatching on its ``kind``. Returns None when it has no name."""
    if not isinstance(item, dict):
        return None
    if not str(item.get("name", "")).strip():
        return None
    kind = str(item.get("kind", "") or "").strip().lower()
    if kind == "budget":
        return BudgetAccount.from_storage_dict(item)
    return BankAccount.from_storage_dict(item)


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


