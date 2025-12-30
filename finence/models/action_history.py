from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import uuid


@dataclass(frozen=True)
class Action(ABC):
    action_name: str = field(default="")
    success: bool = field(default=True)
    error_message: Optional[str] = field(default=None)


@dataclass(frozen=True)
class TransferAction(Action):
    amount: float = field(default=0.0)
    source_name: str = field(default="")
    target_name: str = field(default="")
    source_type: str = field(default="")
    target_type: str = field(default="")


@dataclass(frozen=True)
class AddSavingsAccountAction(Action):
    account_name: str = field(default="")
    is_liquid: bool = field(default=False)


@dataclass(frozen=True)
class EditSavingsAccountAction(Action):
    account_name: str = field(default="")
    old_name: Optional[str] = field(default=None)
    new_name: Optional[str] = field(default=None)
    old_is_liquid: Optional[bool] = field(default=None)
    new_is_liquid: Optional[bool] = field(default=None)


@dataclass(frozen=True)
class DeleteSavingsAccountAction(Action):
    account_name: str = field(default="")
    account_total_amount: float = field(default=0.0)


@dataclass(frozen=True)
class AddSavingAction(Action):
    account_name: str = field(default="")
    saving_name: str = field(default="")
    saving_amount: float = field(default=0.0)


@dataclass(frozen=True)
class EditSavingAction(Action):
    account_name: str = field(default="")
    saving_name: str = field(default="")
    old_amount: float = field(default=0.0)
    new_amount: float = field(default=0.0)


@dataclass(frozen=True)
class DeleteSavingAction(Action):
    account_name: str = field(default="")
    saving_name: str = field(default="")
    saving_amount: float = field(default=0.0)


@dataclass(frozen=True)
class ActivateBankAccountAction(Action):
    account_name: str = field(default="")
    starter_amount: Optional[float] = field(default=None)


@dataclass(frozen=True)
class DeactivateBankAccountAction(Action):
    account_name: str = field(default="")


@dataclass(frozen=True)
class SetStarterAmountAction(Action):
    account_name: str = field(default="")
    starter_amount: float = field(default=0.0)


@dataclass(frozen=True)
class AddIncomeMovementAction(Action):
    movement_id: str = field(default="")


@dataclass(frozen=True)
class AddOutcomeMovementAction(Action):
    movement_id: str = field(default="")


@dataclass(frozen=True)
class DeleteMovementAction(Action):
    movement_id: str = field(default="")
    account_name: str = field(default="")
    amount: float = field(default=0.0)
    date: str = field(default="")


@dataclass(frozen=True)
class UploadOutcomeFileAction(Action):
    account_name: str = field(default="")
    file_name: str = field(default="")
    total_amount: float = field(default=0.0)
    expenses_count: int = field(default=0)
    movement_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AddOneTimeEventAction(Action):
    event_id: str = field(default="")
    event_name: str = field(default="")
    budget: float = field(default=0.0)
    status: str = field(default="")


@dataclass(frozen=True)
class EditOneTimeEventAction(Action):
    event_id: str = field(default="")
    event_name: str = field(default="")
    old_name: Optional[str] = field(default=None)
    new_name: Optional[str] = field(default=None)
    old_budget: Optional[float] = field(default=None)
    new_budget: Optional[float] = field(default=None)
    old_status: Optional[str] = field(default=None)
    new_status: Optional[str] = field(default=None)


@dataclass(frozen=True)
class DeleteOneTimeEventAction(Action):
    event_id: str = field(default="")
    event_name: str = field(default="")
    unassigned_movement_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AssignMovementToOneTimeEventAction(Action):
    movement_id: str = field(default="")
    event_id: str = field(default="")


@dataclass(frozen=True)
class UnassignMovementFromOneTimeEventAction(Action):
    movement_id: str = field(default="")
    previous_event_id: Optional[str] = field(default=None)


@dataclass(frozen=True)
class ActionHistory:
    id: str
    timestamp: str
    action: Action


def generate_action_id() -> str:
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    try:
        return date.today().isoformat()
    except Exception:
        return ""
