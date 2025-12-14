from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bank_movement import BankMovement


@dataclass
class ParsedExpense:
    """
    Represents an expense parsed from a CSV file.

    This model encapsulates the raw data extracted from CSV before it's
    converted to a BankMovement and classified.
    """

    date: str
    description: str
    amount: float

    def to_bank_movement(
        self, account_name: str, category: str = "", movement_type=None
    ) -> "BankMovement":
        """
        Convert this parsed expense to a BankMovement.

        Args:
            account_name: The name of the bank account
            category: Optional category (defaults to empty string)
            movement_type: Optional MovementType (defaults to ONE_TIME)

        Returns:
            A BankMovement instance
        """
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
