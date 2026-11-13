"""Explicit relationships between expenses and what the user expects (pure).

Three different things, kept apart:

* **Frequency** — a movement's ``type`` (חודשי/שנתי/חד־פעמי) says how often an
  expense recurs. It is never a link to anything.
* **Plan link** — ``plan_id`` + ``plan_occurrence`` tie a charge to one scheduled
  payment of a direct-debit plan (הוראת קבע). Charges the plan generated carry
  it from creation; older generated charges are backfilled only when their id,
  plan and scheduled date all agree; an existing expense (e.g. from a bank or
  card import) can be linked by the user. The detector checks a linked charge
  against the plan (amount, date, period, one charge per payment).
* **Marked expected** — ``expected`` on one movement: the user says this
  expense was expected. It applies to that movement only.

Installment plans keep their own text-search matching (unchanged).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .bank_movement import BankMovement
from .installment_plan import InstallmentPlan
from .unusual_expense_detector import PlanCharge, to_money
from ..utils.safe import PARSE_ERRORS

_DD_PREFIX = "dd-"
# How far a charge may be from the nearest scheduled date and still be placed
# on that payment when linking. Further away (mid-month for a monthly plan) it
# is linked "off schedule" and the detector reports it; within this but beyond
# the detector's date tolerance (7 days) it is placed and its date is reported.
_PLACE_WITHIN_DAYS = 10


def _day(raw: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except PARSE_ERRORS:
        return None


def direct_debit_plans(plans: Iterable[InstallmentPlan]) -> Dict[str, InstallmentPlan]:
    return {p.id: p for p in plans if p.is_direct_debit and p.scheduled_date(1) is not None}


def nearest_occurrence(plan: InstallmentPlan, when: date) -> Optional[Tuple[int, date]]:
    """The scheduled payment closest to ``when`` (also past the last one, so a
    late charge is recognisable as such), or None if none is within
    ``_PLACE_WITHIN_DAYS``."""
    count = max(0, int(plan.payments_count or 0))
    slots = [(n, plan.scheduled_date(n)) for n in range(1, count + 13)]
    dated = [(n, d) for n, d in slots if d is not None]
    if not dated:
        return None
    n, d = min(dated, key=lambda s: (abs((s[1] - when).days), s[0]))
    return (n, d) if abs((d - when).days) <= _PLACE_WITHIN_DAYS else None


def generated_occurrence(movement: Any, plans: Mapping[str, InstallmentPlan]) -> Optional[Tuple[str, int]]:
    """``(plan_id, number)`` for a charge the plan itself generated
    (``dd-<plan>-<n>``), verified: the plan exists, ``n`` is within the plan
    and the movement's date is that payment's scheduled date."""
    mid = str(getattr(movement, "id", "") or "")
    if not mid.startswith(_DD_PREFIX):
        return None
    head, _, num = mid[len(_DD_PREFIX):].rpartition("-")
    plan = plans.get(head)
    try:
        n = int(num)
    except ValueError:
        return None
    if plan is None or not 1 <= n <= int(plan.payments_count or 0):
        return None
    if plan.scheduled_date(n) != _day(getattr(movement, "date", "")):
        return None
    return plan.id, n


def plan_charges(
    movements: Iterable[Any], plans: Iterable[InstallmentPlan]
) -> Dict[str, PlanCharge]:
    """Every expense with an explicit (or verifiable generated) direct-debit
    link, resolved for the detector."""
    dd = direct_debit_plans(plans)
    out: Dict[str, PlanCharge] = {}
    for m in movements:
        mid = str(getattr(m, "id", "") or "")
        plan_id = str(getattr(m, "plan_id", "") or "").strip()
        occurrence = getattr(m, "plan_occurrence", None)
        if not plan_id:
            gen = generated_occurrence(m, dd)
            if gen is None:
                continue
            plan_id, occurrence = gen
        plan = dd.get(plan_id)
        if plan is None:
            continue  # unknown / deleted plan: no link to check against
        if occurrence is None:
            when = _day(getattr(m, "date", ""))
            placed = nearest_occurrence(plan, when) if when else None
            occurrence = placed[0] if placed else None
        amount = to_money(abs(float(plan.monthly_amount or 0.0))) or Decimal("0")
        out[mid] = PlanCharge(
            movement_id=mid,
            plan_id=plan.id,
            plan_name=str(plan.name or ""),
            occurrence=int(occurrence) if occurrence is not None else None,
            scheduled_date=plan.scheduled_date(int(occurrence)) if occurrence else None,
            expected_amount=amount,
            payments_count=int(plan.payments_count or 0),
        )
    return out


def backfill_generated_links(
    movements: Sequence[BankMovement], plans: Iterable[InstallmentPlan]
) -> List[BankMovement]:
    """Charges generated by a direct debit before links were stored, with the
    link added — only when id, plan and scheduled date agree. Idempotent."""
    dd = direct_debit_plans(plans)
    out: List[BankMovement] = []
    for m in movements:
        if m.plan_id:
            continue
        gen = generated_occurrence(m, dd)
        if gen is not None:
            out.append(replace(m, plan_id=gen[0], plan_occurrence=gen[1]))
    return out


def link_to_plan(movement: BankMovement, plan: Optional[InstallmentPlan]) -> BankMovement:
    """The movement linked to ``plan`` (its payment chosen by date; None when
    the date fits no payment — the detector then reports it), or unlinked when
    ``plan`` is None. Nothing else on the movement changes."""
    if plan is None:
        return replace(movement, plan_id=None, plan_occurrence=None)
    when = _day(movement.date)
    placed = nearest_occurrence(plan, when) if when else None
    return replace(movement, plan_id=plan.id, plan_occurrence=placed[0] if placed else None)


def set_expected(movement: BankMovement, expected: bool) -> BankMovement:
    return replace(movement, expected=bool(expected))


def covered_occurrences(movements: Iterable[Any]) -> set:
    """``(plan_id, n)`` already paid by a linked movement — the plan does not
    generate another charge for them."""
    return {
        (str(m.plan_id), int(m.plan_occurrence))
        for m in movements
        if getattr(m, "plan_id", None) and getattr(m, "plan_occurrence", None) is not None
    }
