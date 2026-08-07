from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional
import uuid


class MovementType(StrEnum):
    MONTHLY = "חודשי"
    YEARLY = "שנתי"
    ONE_TIME = "חד פעמי"


def generate_movement_id() -> str:
    return str(uuid.uuid4())


def parse_movement_type(raw: object) -> "MovementType":
    """Coerce a raw type string into a MovementType, tolerating case/format
    variants (MONTHLY/monthly, ONE_TIME/onetime, …). Defaults to ONE_TIME."""
    text = str(raw or "").strip()
    if text in ("MONTHLY", "monthly"):
        return MovementType.MONTHLY
    if text in ("YEARLY", "yearly"):
        return MovementType.YEARLY
    if text in ("ONE_TIME", "one_time", "onetime"):
        return MovementType.ONE_TIME
    try:
        return MovementType(text)
    except Exception:
        return MovementType.ONE_TIME


def deserialize_bank_movement(
    raw: Any, *, movement_id: Optional[str] = None
) -> "Optional[BankMovement]":
    """Build a BankMovement from a raw JSON dict, or None if it's unusable
    (missing date/account, or not a dict). Shared by the local provider and the
    Firebase puller so the parsing lives in one place."""
    if not isinstance(raw, dict):
        return None
    try:
        amount = float(raw.get("amount", 0.0) or 0.0)
        date = str(raw.get("date", "") or "").strip()
        account_name = str(raw.get("account_name", "") or "").strip()
        if not date or not account_name:
            return None
        category = str(raw.get("category", "") or "").strip()
        movement_type = parse_movement_type(raw.get("type", ""))
        is_transfer = bool(raw.get("is_transfer", False))
        if not is_transfer and category == "העברה":
            is_transfer = True
        desc = raw.get("description")
        description = str(desc) if isinstance(desc, str) and desc else None
        eid = raw.get("event_id")
        event_id = (
            str(eid).strip() if eid is not None and str(eid).strip() else None
        )
        mid = movement_id
        if mid is None:
            rid = raw.get("id")
            mid = str(rid).strip() if rid is not None else ""
            if not mid:
                mid = generate_movement_id()
        return BankMovement(
            amount=amount,
            date=date,
            account_name=account_name,
            category=category,
            type=movement_type,
            is_transfer=is_transfer,
            description=description,
            event_id=event_id,
            id=mid,
        )
    except Exception:
        return None


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
