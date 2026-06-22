from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import uuid

from .bank_movement import BankMovement
from .movement_matching import match_movements


def generate_installment_plan_id() -> str:
    return str(uuid.uuid4())


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

    def stats(self, movements: List[BankMovement]) -> "InstallmentPlanStats":
        """Compute paid/left/total/overpaid for this plan against ``movements``."""
        matched = self.matches(movements)
        paid_count = len(matched)
        payments_left = max(0, int(self.payments_count) - paid_count)
        total_paid = 0.0
        for m in matched:
            try:
                amt = float(m.amount)
                total_paid += -amt if amt < 0 else amt
            except Exception:
                continue
        overpaid = 0.0
        try:
            if float(self.original_amount) > 0:
                overpaid = max(0.0, float(total_paid) - float(self.original_amount))
        except Exception:
            overpaid = 0.0
        return InstallmentPlanStats(
            paid_count=int(paid_count),
            payments_left=int(payments_left),
            total_paid=float(total_paid),
            overpaid=float(overpaid),
            matched_movements=matched,
        )
