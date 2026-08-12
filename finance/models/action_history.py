from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
import uuid
from ..utils.safe import PARSE_ERRORS


# Canonical Hebrew title for every action kind. Single source of truth for the
# action-history views (previously duplicated across two dialogs, which drifted —
# the mortgage/asset kinds were never added and showed as raw English keys).
# Kept complete: a test asserts every registered action_name has a title here.
ACTION_TITLES: dict[str, str] = {
    "transfer": "העברת כסף",
    "add_savings_account": "הוספת חסכון",
    "edit_savings_account": "עריכת חסכון",
    "delete_savings_account": "מחיקת חסכון",
    "add_saving": "הוספת סוג חסכון",
    "edit_saving": "עריכת סוג חסכון",
    "delete_saving": "מחיקת סוג חסכון",
    "activate_bank_account": "הפעלת חשבון",
    "deactivate_bank_account": "ביטול חשבון",
    "set_starter_amount": "הגדרת סכום התחלתי",
    "add_income_movement": "הוספת הכנסה",
    "add_outcome_movement": "הוספת הוצאה",
    "delete_movement": "מחיקת תנועה",
    "upload_outcome_file": "ייבוא קובץ הוצאות",
    "add_one_time_event": "יצירת אירוע חד־פעמי",
    "edit_one_time_event": "עריכת אירוע חד־פעמי",
    "delete_one_time_event": "מחיקת אירוע חד־פעמי",
    "assign_movement_to_one_time_event": "שיוך תנועה לאירוע",
    "unassign_movement_from_one_time_event": "הסרת שיוך תנועה מאירוע",
    "add_installment_plan": "יצירת תשלומים",
    "edit_installment_plan": "עריכת תשלומים",
    "delete_installment_plan": "מחיקת תשלומים",
    "add_mortgage": "הוספת נכס",
    "edit_mortgage": "עריכת נכס",
    "delete_mortgage": "מחיקת נכס",
}


def action_title(action_name: object) -> str:
    """Hebrew title for an action_name, falling back to the raw key (never blank)."""
    key = str(action_name or "").strip()
    return ACTION_TITLES.get(key, key or "פעולה")


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
class AddInstallmentPlanAction(Action):
    plan_id: str = field(default="")
    plan_name: str = field(default="")
    vendor_query: str = field(default="")
    account_name: str = field(default="")
    start_date: str = field(default="")
    payments_count: int = field(default=0)
    original_amount: float = field(default=0.0)


@dataclass(frozen=True)
class EditInstallmentPlanAction(Action):
    plan_id: str = field(default="")
    plan_name: str = field(default="")
    old_name: Optional[str] = field(default=None)
    new_name: Optional[str] = field(default=None)
    old_vendor_query: Optional[str] = field(default=None)
    new_vendor_query: Optional[str] = field(default=None)
    old_account_name: Optional[str] = field(default=None)
    new_account_name: Optional[str] = field(default=None)
    old_start_date: Optional[str] = field(default=None)
    new_start_date: Optional[str] = field(default=None)
    old_payments_count: Optional[int] = field(default=None)
    new_payments_count: Optional[int] = field(default=None)
    old_original_amount: Optional[float] = field(default=None)
    new_original_amount: Optional[float] = field(default=None)
    old_archived: Optional[bool] = field(default=None)
    new_archived: Optional[bool] = field(default=None)


@dataclass(frozen=True)
class DeleteInstallmentPlanAction(Action):
    plan_id: str = field(default="")
    plan_name: str = field(default="")


@dataclass(frozen=True)
class AddMortgageAction(Action):
    mortgage_id: str = field(default="")
    mortgage_name: str = field(default="")
    account_name: str = field(default="")
    start_date: str = field(default="")
    tracks_count: int = field(default=0)
    original_principal: float = field(default=0.0)


@dataclass(frozen=True)
class EditMortgageAction(Action):
    mortgage_id: str = field(default="")
    mortgage_name: str = field(default="")
    old_name: Optional[str] = field(default=None)
    new_name: Optional[str] = field(default=None)
    old_account_name: Optional[str] = field(default=None)
    new_account_name: Optional[str] = field(default=None)
    old_start_date: Optional[str] = field(default=None)
    new_start_date: Optional[str] = field(default=None)
    old_tracks_count: Optional[int] = field(default=None)
    new_tracks_count: Optional[int] = field(default=None)
    old_original_principal: Optional[float] = field(default=None)
    new_original_principal: Optional[float] = field(default=None)
    old_archived: Optional[bool] = field(default=None)
    new_archived: Optional[bool] = field(default=None)


@dataclass(frozen=True)
class DeleteMortgageAction(Action):
    mortgage_id: str = field(default="")
    mortgage_name: str = field(default="")


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
    except PARSE_ERRORS:
        return ""
