from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional
import uuid
from ..utils.safe import PARSE_ERRORS


class MovementType(StrEnum):
    """How often the movement recurs (orthogonal to its kind)."""

    MONTHLY = "חודשי"
    YEARLY = "שנתי"
    ONE_TIME = "חד פעמי"


class MovementKind(StrEnum):
    """What the movement *is*: income, expense, or a transfer between own
    accounts. Derived from the stored row (see ``BankMovement.kind``)."""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


def generate_movement_id() -> str:
    return str(uuid.uuid4())


def counts_as_transfer(movement: Any) -> bool:
    """Whether a movement is a transfer (flagged ``is_transfer``, categorised
    "העברה", or carrying transfer endpoints) — and so excluded from income/expense
    reports. The single place this is decided; works on any object exposing the
    fields, including duck-typed test doubles."""
    if bool(getattr(movement, "is_transfer", False)):
        return True
    if getattr(movement, "transfer_from", None) or getattr(movement, "transfer_to", None):
        return True
    return str(getattr(movement, "category", "") or "").strip() == "העברה"


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
    except PARSE_ERRORS:
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

        def _acct(key: str) -> str | None:
            v = raw.get(key)
            return str(v).strip() if v is not None and str(v).strip() else None

        transfer_from = _acct("transfer_from")
        transfer_to = _acct("transfer_to")
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
            transfer_from=transfer_from,
            transfer_to=transfer_to,
            id=mid,
        )
    except PARSE_ERRORS:
        return None


@dataclass(frozen=True)
class BankMovement:
    """The flat, back-compatible storage row every movement shares. Kind-specific
    behaviour is a view over this record — see :func:`build_movement`."""

    amount: float
    date: str
    account_name: str
    category: str
    type: MovementType
    is_transfer: bool = False
    description: str | None = None
    event_id: str | None = None
    # Transfer-only structured "what happened": the two accounts the money moved
    # between (None for income/expense, or for legacy transfers not yet backfilled).
    transfer_from: str | None = None
    transfer_to: str | None = None
    id: str = field(default_factory=generate_movement_id)

    @property
    def counts_as_transfer(self) -> bool:
        """True if this movement is a transfer — see :func:`counts_as_transfer`."""
        return counts_as_transfer(self)

    @property
    def kind(self) -> MovementKind:
        """What the movement is: transfers first, otherwise by amount sign."""
        if self.counts_as_transfer:
            return MovementKind.TRANSFER
        return MovementKind.INCOME if self.amount >= 0 else MovementKind.EXPENSE


# ─────────────────────────── polymorphic views ───────────────────────────
# Like build_asset() over a Mortgage: the stored row stays flat; these views
# expose the data that fits each kind.


@dataclass(frozen=True)
class Movement:
    """Base view over a stored :class:`BankMovement` — the fields every kind has."""

    record: BankMovement

    @property
    def kind(self) -> MovementKind:
        return self.record.kind

    @property
    def amount(self) -> float:
        return self.record.amount

    @property
    def date(self) -> str:
        return self.record.date

    @property
    def account_name(self) -> str:
        return self.record.account_name

    @property
    def type(self) -> MovementType:
        return self.record.type

    @property
    def description(self) -> str | None:
        return self.record.description


@dataclass(frozen=True)
class IncomeMovement(Movement):
    """הכנסה — money in."""

    @property
    def category(self) -> str:
        return self.record.category


@dataclass(frozen=True)
class ExpenseMovement(Movement):
    """הוצאה — money out."""

    @property
    def category(self) -> str:
        return self.record.category


@dataclass(frozen=True)
class TransferMovement(Movement):
    """העברה — money moved between the owner's own accounts. Carries both sides."""

    @property
    def from_account(self) -> str:
        if self.record.transfer_from:
            return self.record.transfer_from
        # legacy row: this leg's own account is the source when money left it
        return self.record.account_name if self.record.amount < 0 else ""

    @property
    def to_account(self) -> str:
        if self.record.transfer_to:
            return self.record.transfer_to
        return self.record.account_name if self.record.amount >= 0 else ""


def build_movement(record: BankMovement) -> Movement:
    """Wrap a stored row in its kind-specific view."""
    kind = record.kind
    if kind == MovementKind.TRANSFER:
        return TransferMovement(record)
    if kind == MovementKind.INCOME:
        return IncomeMovement(record)
    return ExpenseMovement(record)
