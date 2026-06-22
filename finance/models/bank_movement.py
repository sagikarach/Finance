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
    is_transfer: bool = False
    description: str | None = None
    event_id: str | None = None
    id: str = field(default_factory=generate_movement_id)

    @property
    def counts_as_transfer(self) -> bool:
        """True if this movement is a transfer (flagged, or categorised
        "העברה") and should be excluded from income/expense reports."""
        if bool(self.is_transfer):
            return True
        return str(self.category or "").strip() == "העברה"
