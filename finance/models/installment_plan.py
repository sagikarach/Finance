from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
import uuid

from .bank_movement import BankMovement
from .movement_matching import match_movements
from ..utils.safe import PARSE_ERRORS


# Plan kinds. An installment plan is tracked by matching real bank movements;
# a direct debit (הוראת קבע) is a fixed amount charged on the same day every
# month, so its schedule and progress come straight from the calendar.
KIND_INSTALLMENTS = "installments"
KIND_DIRECT_DEBIT = "direct_debit"
PLAN_KINDS = (KIND_INSTALLMENTS, KIND_DIRECT_DEBIT)


def generate_installment_plan_id() -> str:
    return str(uuid.uuid4())


def normalize_plan_kind(value: object) -> str:
    kind = str(value or "").strip()
    return kind if kind in PLAN_KINDS else KIND_INSTALLMENTS


def _add_months_on_day(start: date, months: int, day: int) -> date:
    """``start`` moved ``months`` months ahead, on ``day`` (clamped to the
    month's last day — a charge on the 31st falls on Feb 28/29)."""
    total = start.month - 1 + int(months)
    year = start.year + total // 12
    month = total % 12 + 1
    return date(year, month, min(int(day), monthrange(year, month)[1]))


@dataclass(frozen=True)
class ScheduledPayment:
    number: int  # 1-based
    date: date
    amount: float
    done: bool  # the charge date has arrived


@dataclass(frozen=True)
class InstallmentPlanStats:
    paid_count: int
    payments_left: int
    total_paid: float
    overpaid: float
    matched_movements: List[BankMovement]


@dataclass(frozen=True)
class InstallmentPlan:
    id: str = field(default_factory=generate_installment_plan_id)
    name: str = ""
    vendor_query: str = ""
    account_name: str = ""
    start_date: str = ""
    payments_count: int = 0
    original_amount: float = 0.0
    excluded_movement_ids: list[str] = field(default_factory=list)
    archived: bool = False
    kind: str = KIND_INSTALLMENTS
    monthly_amount: float = 0.0  # direct debit: the fixed monthly charge
    charge_day: int = 0  # direct debit: day of month (1-31); 0 = start date's day

    @property
    def is_direct_debit(self) -> bool:
        return normalize_plan_kind(self.kind) == KIND_DIRECT_DEBIT

    def schedule(self, today: Optional[date] = None) -> List[ScheduledPayment]:
        """Direct debit: every charge date and amount. The first charge is the
        first ``charge_day`` on/after ``start_date``. Empty for other kinds."""
        if not self.is_direct_debit:
            return []
        count = int(self.payments_count or 0)
        if count <= 0:
            return []
        try:
            start = date.fromisoformat(str(self.start_date or "")[:10])
        except PARSE_ERRORS:
            return []
        day = int(self.charge_day or 0)
        if not 1 <= day <= 31:
            day = start.day
        first_offset = 0 if _add_months_on_day(start, 0, day) >= start else 1
        today = today or date.today()
        amount = abs(float(self.monthly_amount or 0.0))
        out: List[ScheduledPayment] = []
        for i in range(count):
            d = _add_months_on_day(start, first_offset + i, day)
            out.append(ScheduledPayment(number=i + 1, date=d, amount=amount, done=d <= today))
        return out

    def matches(self, movements: List[BankMovement]) -> List[BankMovement]:
        """The bank movements that count as this plan's payments."""
        count = int(self.payments_count or 0)
        return match_movements(
            movements,
            vendor_query=self.vendor_query,
            account_name=self.account_name,
            start_date=str(self.start_date or ""),
            excluded_ids=self.excluded_movement_ids or [],
            max_count=count if count > 0 else None,
        )

    def stats(
        self, movements: List[BankMovement], today: Optional[date] = None
    ) -> "InstallmentPlanStats":
        """Compute paid/left/total/overpaid for this plan against ``movements``.
        A direct debit is counted by its schedule instead (charges are fixed)."""
        if self.is_direct_debit:
            sched = self.schedule(today)
            done = [p for p in sched if p.done]
            return InstallmentPlanStats(
                paid_count=len(done),
                payments_left=len(sched) - len(done),
                total_paid=float(sum(p.amount for p in done)),
                overpaid=0.0,
                matched_movements=[],
            )
        matched = self.matches(movements)
        paid_count = len(matched)
        payments_left = max(0, int(self.payments_count) - paid_count)
        total_paid = 0.0
        for m in matched:
            try:
                amt = float(m.amount)
                total_paid += -amt if amt < 0 else amt
            except PARSE_ERRORS:
                continue
        overpaid = 0.0
        try:
            if float(self.original_amount) > 0:
                overpaid = max(0.0, float(total_paid) - float(self.original_amount))
        except PARSE_ERRORS:
            overpaid = 0.0
        return InstallmentPlanStats(
            paid_count=int(paid_count),
            payments_left=int(payments_left),
            total_paid=float(total_paid),
            overpaid=float(overpaid),
            matched_movements=matched,
        )
