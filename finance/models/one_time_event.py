from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Dict, List, Optional
import uuid

from .accounts import parse_iso_date
from .bank_movement import BankMovement


class OneTimeEventStatus(StrEnum):
    PLANNED = "מתוכנן"
    ACTIVE = "פעיל"
    FINISHED = "הסתיים"
    ARCHIVED = "בארכיון"


def parse_one_time_event_status(raw: object) -> OneTimeEventStatus:
    text = str(raw or "").strip()
    if not text:
        return OneTimeEventStatus.ACTIVE
    try:
        return OneTimeEventStatus(text)
    except Exception:
        pass
    upper = text.upper()
    if upper in ("PLANNED", "PLAN"):
        return OneTimeEventStatus.PLANNED
    if upper in ("ACTIVE", "IN_PROGRESS"):
        return OneTimeEventStatus.ACTIVE
    if upper in ("FINISHED", "DONE", "COMPLETED"):
        return OneTimeEventStatus.FINISHED
    if upper in ("ARCHIVED", "ARCHIVE"):
        return OneTimeEventStatus.ARCHIVED
    return OneTimeEventStatus.ACTIVE


def generate_event_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class EventTotals:
    expenses: float
    income: float
    net: float
    remaining: float
    percent_used: Optional[float]
    by_category_expense: Dict[str, float]


@dataclass(frozen=True)
class OneTimeEvent:
    id: str = field(default_factory=generate_event_id)
    name: str = ""
    budget: float = 0.0
    status: OneTimeEventStatus = OneTimeEventStatus.ACTIVE
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None

    def in_range(self, movement: BankMovement) -> bool:
        """True if ``movement``'s date falls within this event's window (an open
        window — no start/end — includes everything)."""
        if not self.start_date and not self.end_date:
            return True
        dt = parse_iso_date(movement.date)
        if self.start_date and dt < parse_iso_date(self.start_date):
            return False
        if self.end_date and dt > parse_iso_date(self.end_date):
            return False
        return True

    def owns(self, movement: BankMovement) -> bool:
        """True if ``movement`` is assigned to this event and within its window."""
        return getattr(movement, "event_id", None) == self.id and self.in_range(
            movement
        )

    def totals(self, movements: List[BankMovement]) -> "EventTotals":
        """Aggregate this event's expenses/income/net/remaining over the movements
        it owns, with an expense breakdown by category."""
        expenses = 0.0
        income = 0.0
        by_cat: Dict[str, float] = {}
        for m in movements:
            if not self.owns(m):
                continue
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
        remaining = float(self.budget) - expenses
        percent_used: Optional[float] = None
        if float(self.budget) > 0:
            percent_used = expenses / float(self.budget)
        by_cat_sorted = dict(
            sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)
        )
        return EventTotals(
            expenses=float(expenses),
            income=float(income),
            net=float(net),
            remaining=float(remaining),
            percent_used=percent_used,
            by_category_expense=by_cat_sorted,
        )
