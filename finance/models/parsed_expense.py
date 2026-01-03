from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bank_movement import BankMovement


@dataclass
class ParsedExpense:
    date: str
    description: str
    amount: float

    def to_bank_movement(
        self, account_name: str, category: str = "", movement_type=None
    ) -> "BankMovement":
        from .bank_movement import BankMovement, MovementType

        if movement_type is None:
            movement_type = MovementType.ONE_TIME

        return BankMovement(
            amount=self.amount,
            date=self.date,
            account_name=account_name,
            category=category,
            type=movement_type,
            description=self.description,
        )
