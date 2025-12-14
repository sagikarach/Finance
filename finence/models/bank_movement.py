from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import uuid


class MovementType(StrEnum):
    MONTHLY = "חודשי"
    YEARLY = "שנתי"
    ONE_TIME = "חד פעמי"


def generate_movement_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class BankMovement:
    amount: float
    date: str
    account_name: str
    category: str
    type: MovementType
    description: str | None = None
    id: str = field(default_factory=generate_movement_id)
