from __future__ import annotations

from dataclasses import dataclass, field
import uuid


def generate_installment_plan_id() -> str:
    return str(uuid.uuid4())


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
