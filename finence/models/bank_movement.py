from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MovementType(StrEnum):
    MONTHLY = "חודשי"
    YEARLY = "שנתי"
    ONE_TIME = "חד פעמי"


@dataclass(frozen=True)
class BankMovement:
    amount: float
    date: str
    account_name: str
    category: str
    type: MovementType
    description: str | None = None
