from __future__ import annotations

from typing import List, Optional

from ..data.action_history_provider import (
    ActionHistoryProvider,
    JsonFileActionHistoryProvider,
)
from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)
from ..data.installment_plan_provider import (
    InstallmentPlanProvider,
    JsonFileInstallmentPlanProvider,
)
from .action_history import (
    Action,
    ActionHistory,
    generate_action_id,
    get_current_timestamp,
)
from .installment_plan import InstallmentPlan, InstallmentPlanStats


class InstallmentsService:
    def __init__(
        self,
        *,
        plans_provider: Optional[InstallmentPlanProvider] = None,
        movements_provider: Optional[BankMovementProvider] = None,
        history_provider: Optional[ActionHistoryProvider] = None,
    ) -> None:
        self._plans_provider = plans_provider or JsonFileInstallmentPlanProvider()
        self._movements_provider = movements_provider or JsonFileBankMovementProvider()
        self._history_provider: ActionHistoryProvider = (
            history_provider or JsonFileActionHistoryProvider()
        )

    def list_plans(self) -> List[InstallmentPlan]:
        plans = self._plans_provider.list_plans()
        plans.sort(
            key=lambda p: (bool(getattr(p, "archived", False)), str(p.name or ""))
        )
        return plans

    def upsert_plan(self, plan: InstallmentPlan) -> None:
        old: Optional[InstallmentPlan] = None
        try:
            for p in self._plans_provider.list_plans():
                if p.id == plan.id:
                    old = p
                    break
        except Exception:
            old = None

        self._plans_provider.upsert_plan(plan)
        try:
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_installment_plan(plan)
        except Exception:
            pass

        try:
            from .action_history import (
                AddInstallmentPlanAction,
                EditInstallmentPlanAction,
            )

            action_obj: Action
            if old is None:
                action_obj = AddInstallmentPlanAction(
                    action_name="add_installment_plan",
                    plan_id=plan.id,
                    plan_name=plan.name,
                    vendor_query=plan.vendor_query,
                    account_name=plan.account_name,
                    start_date=plan.start_date,
                    payments_count=int(plan.payments_count),
                    original_amount=float(plan.original_amount),
                )
            else:
                action_obj = EditInstallmentPlanAction(
                    action_name="edit_installment_plan",
                    plan_id=plan.id,
                    plan_name=plan.name,
                    old_name=old.name if old.name != plan.name else None,
                    new_name=plan.name if old.name != plan.name else None,
                    old_vendor_query=old.vendor_query
                    if old.vendor_query != plan.vendor_query
                    else None,
                    new_vendor_query=plan.vendor_query
                    if old.vendor_query != plan.vendor_query
                    else None,
                    old_account_name=old.account_name
                    if old.account_name != plan.account_name
                    else None,
                    new_account_name=plan.account_name
                    if old.account_name != plan.account_name
                    else None,
                    old_start_date=old.start_date
                    if old.start_date != plan.start_date
                    else None,
                    new_start_date=plan.start_date
                    if old.start_date != plan.start_date
                    else None,
                    old_payments_count=int(old.payments_count)
                    if int(old.payments_count) != int(plan.payments_count)
                    else None,
                    new_payments_count=int(plan.payments_count)
                    if int(old.payments_count) != int(plan.payments_count)
                    else None,
                    old_original_amount=float(old.original_amount)
                    if float(old.original_amount) != float(plan.original_amount)
                    else None,
                    new_original_amount=float(plan.original_amount)
                    if float(old.original_amount) != float(plan.original_amount)
                    else None,
                    old_archived=bool(old.archived)
                    if bool(old.archived) != bool(plan.archived)
                    else None,
                    new_archived=bool(plan.archived)
                    if bool(old.archived) != bool(plan.archived)
                    else None,
                )

            self._history_provider.add_action(
                ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action_obj,
                )
            )
        except Exception:
            pass

    def delete_plan(self, plan_id: str) -> None:
        plan_id = str(plan_id or "").strip()
        if not plan_id:
            return
        plan_name = ""
        try:
            for p in self._plans_provider.list_plans():
                if p.id == plan_id:
                    plan_name = p.name
                    break
        except Exception:
            plan_name = ""

        self._plans_provider.delete_plan(plan_id)
        try:
            from ..models.firebase_session import (
                current_firebase_uid,
                current_firebase_workspace_id,
            )
            from ..models.firebase_sync_state import add_pending_delete
            from ..models.sync_gate import allow_firebase_push

            key = (
                current_firebase_workspace_id() or current_firebase_uid() or ""
            ).strip()
            if key:
                add_pending_delete(key=key, kind="installment_plan", item_id=plan_id)

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().delete_installment_plan(plan_id=plan_id)
        except Exception:
            pass

        try:
            from .action_history import DeleteInstallmentPlanAction

            self._history_provider.add_action(
                ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=DeleteInstallmentPlanAction(
                        action_name="delete_installment_plan",
                        plan_id=plan_id,
                        plan_name=plan_name,
                    ),
                )
            )
        except Exception:
            pass

    def exclude_movement(self, *, plan_id: str, movement_id: str) -> None:
        plan_id = str(plan_id or "").strip()
        movement_id = str(movement_id or "").strip()
        if not plan_id or not movement_id:
            return
        plan = None
        for p in self._plans_provider.list_plans():
            if p.id == plan_id:
                plan = p
                break
        if plan is None:
            return
        excluded = list(getattr(plan, "excluded_movement_ids", []) or [])
        if movement_id in excluded:
            return
        excluded.append(movement_id)
        self.upsert_plan(
            InstallmentPlan(
                id=plan.id,
                name=plan.name,
                vendor_query=plan.vendor_query,
                account_name=plan.account_name,
                start_date=plan.start_date,
                payments_count=int(plan.payments_count),
                original_amount=float(plan.original_amount),
                excluded_movement_ids=excluded,
                archived=bool(plan.archived),
            )
        )

    def compute_stats(self, plan: InstallmentPlan) -> InstallmentPlanStats:
        # The plan owns the math; the service just supplies the movements.
        return plan.stats(self._movements_provider.list_movements())
