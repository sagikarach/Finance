from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bank_movement import BankMovement, MovementType


@dataclass
class ClassifiedExpense:
    """
    Represents a bank movement with its classification suggestion and confidence score.

    This model encapsulates the result of classifying an expense, including:
    - The original movement
    - Suggested category (if any)
    - Suggested movement type (if any)
    - Confidence score (0.0 to 1.0)
    """

    movement: BankMovement
    suggested_category: Optional[str] = None
    suggested_type: Optional[MovementType] = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        """Validate confidence is in valid range."""
        if self.confidence < 0.0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0

    def to_bank_movement(self) -> BankMovement:
        """
        Convert this classified expense to a BankMovement with the suggested classification.
        Preserves the original movement's ID.

        Returns:
            A BankMovement with the suggested category and type applied, and original ID
        """
        from dataclasses import replace

        return replace(
            self.movement,
            category=self.suggested_category or "",
            type=self.suggested_type or MovementType.ONE_TIME,
        )

    def to_bank_movement_with_user_input(
        self, category: str, movement_type: MovementType
    ) -> BankMovement:
        """
        Convert this classified expense to a BankMovement with user-provided classification.
        Preserves the original movement's ID.

        Args:
            category: User-selected category
            movement_type: User-selected movement type

        Returns:
            A BankMovement with the user-provided classification and original ID
        """
        from dataclasses import replace

        return replace(
            self.movement,
            category=category,
            type=movement_type,
        )
