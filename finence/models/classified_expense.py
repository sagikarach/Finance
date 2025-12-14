from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .bank_movement import BankMovement, MovementType


@dataclass
class ClassifiedExpense:
    movement: BankMovement
    suggested_category: Optional[str] = None
    suggested_type: Optional[MovementType] = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.confidence < 0.0:
            self.confidence = 0.0
        elif self.confidence > 1.0:
            self.confidence = 1.0

    def to_bank_movement(self) -> BankMovement:
        from dataclasses import replace

        return replace(
            self.movement,
            category=self.suggested_category or "",
            type=self.suggested_type or MovementType.ONE_TIME,
        )

    def to_bank_movement_with_user_input(
        self, category: str, movement_type: MovementType
    ) -> BankMovement:
        from dataclasses import replace

        return replace(
            self.movement,
            category=category,
            type=movement_type,
        )
