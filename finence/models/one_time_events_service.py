from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)
from ..data.one_time_event_provider import (
    JsonFileOneTimeEventProvider,
    OneTimeEventProvider,
)
from .accounts import parse_iso_date
from .bank_movement import BankMovement, MovementType
from .one_time_event import OneTimeEvent, OneTimeEventStatus


@dataclass(frozen=True)
class EventTotals:
    expenses: float
    income: float
    net: float
    remaining: float
    percent_used: Optional[float]
    by_category_expense: Dict[str, float]


class OneTimeEventsService:
    def __init__(
        self,
        *,
        events_provider: Optional[OneTimeEventProvider] = None,
        movements_provider: Optional[BankMovementProvider] = None,
    ) -> None:
        self._events_provider = events_provider or JsonFileOneTimeEventProvider()
        self._movements_provider = movements_provider or JsonFileBankMovementProvider()

    def list_events(self) -> List[OneTimeEvent]:
        events = self._events_provider.list_events()
        events.sort(key=lambda e: (str(e.status.value), e.name))
        return events

    def upsert_event(self, event: OneTimeEvent) -> None:
        self._events_provider.upsert_event(event)

    def delete_event(self, event_id: str) -> None:
        self._events_provider.delete_event(event_id)
        # Unassign movements from this event
        movements = self._movements_provider.list_movements()
        updated: List[BankMovement] = []
        changed = False
        for m in movements:
            if getattr(m, "event_id", None) == event_id:
                updated.append(
                    BankMovement(
                        amount=m.amount,
                        date=m.date,
                        account_name=m.account_name,
                        category=m.category,
                        type=m.type,
                        description=m.description,
                        event_id=None,
                        id=m.id,
                    )
                )
                changed = True
            else:
                updated.append(m)
        if changed:
            self._movements_provider.save_movements(updated)

    def list_one_time_movements(self) -> List[BankMovement]:
        out: List[BankMovement] = []
        for m in self._movements_provider.list_movements():
            try:
                if m.type == MovementType.ONE_TIME:
                    out.append(m)
            except Exception:
                continue
        out.sort(key=lambda m: parse_iso_date(m.date))
        return out

    def assign_movement(self, movement_id: str, event_id: Optional[str]) -> None:
        movements = self._movements_provider.list_movements()
        updated: List[BankMovement] = []
        changed = False
        for m in movements:
            if m.id != movement_id:
                updated.append(m)
                continue
            if m.type != MovementType.ONE_TIME:
                updated.append(m)
                continue
            if getattr(m, "event_id", None) == event_id:
                updated.append(m)
                continue
            updated.append(
                BankMovement(
                    amount=m.amount,
                    date=m.date,
                    account_name=m.account_name,
                    category=m.category,
                    type=m.type,
                    description=m.description,
                    event_id=event_id,
                    id=m.id,
                )
            )
            changed = True
        if changed:
            self._movements_provider.save_movements(updated)

    def event_totals(self, event: OneTimeEvent) -> EventTotals:
        movements = self.list_one_time_movements()
        filtered = self._filter_by_event_and_range(event, movements)

        expenses = 0.0
        income = 0.0
        by_cat: Dict[str, float] = {}

        for m in filtered:
            try:
                amt = float(m.amount)
            except Exception:
                continue
            if amt < 0:
                a = abs(amt)
                expenses += a
                cat = (m.category or "אחר").strip() or "אחר"
                by_cat[cat] = float(by_cat.get(cat, 0.0) + a)
            elif amt > 0:
                income += amt

        net = income - expenses
        remaining = float(event.budget) - expenses
        percent_used: Optional[float] = None
        if float(event.budget) > 0:
            percent_used = expenses / float(event.budget)

        by_cat_sorted = dict(sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True))
        return EventTotals(
            expenses=float(expenses),
            income=float(income),
            net=float(net),
            remaining=float(remaining),
            percent_used=percent_used,
            by_category_expense=by_cat_sorted,
        )

    def movements_for_event(
        self, event: OneTimeEvent
    ) -> Tuple[List[BankMovement], List[BankMovement]]:
        movements = self.list_one_time_movements()
        in_range = self._filter_by_range(event, movements)
        assigned: List[BankMovement] = []
        unassigned: List[BankMovement] = []
        for m in in_range:
            if getattr(m, "event_id", None) == event.id:
                assigned.append(m)
            elif getattr(m, "event_id", None) in (None, ""):
                unassigned.append(m)
        assigned.sort(key=lambda m: parse_iso_date(m.date))
        unassigned.sort(key=lambda m: parse_iso_date(m.date))
        return assigned, unassigned

    def _filter_by_event_and_range(
        self, event: OneTimeEvent, movements: List[BankMovement]
    ) -> List[BankMovement]:
        out: List[BankMovement] = []
        for m in movements:
            if getattr(m, "event_id", None) != event.id:
                continue
            if not self._in_range(event, m):
                continue
            out.append(m)
        return out

    def _filter_by_range(
        self, event: OneTimeEvent, movements: List[BankMovement]
    ) -> List[BankMovement]:
        if not event.start_date and not event.end_date:
            return list(movements)
        return [m for m in movements if self._in_range(event, m)]

    def _in_range(self, event: OneTimeEvent, movement: BankMovement) -> bool:
        if not event.start_date and not event.end_date:
            return True
        dt = parse_iso_date(movement.date)
        if event.start_date:
            if dt < parse_iso_date(event.start_date):
                return False
        if event.end_date:
            if dt > parse_iso_date(event.end_date):
                return False
        return True

    @staticmethod
    def default_event(name: str = "אירוע חדש") -> OneTimeEvent:
        return OneTimeEvent(name=name, budget=0.0, status=OneTimeEventStatus.ACTIVE)
