from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import List, Optional

from ..data.action_history_provider import (
    ActionHistoryProvider,
    JsonFileActionHistoryProvider,
)
from .bank_movement import BankMovement
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
from ..utils.safe import PARSE_ERRORS, swallow


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
        except PARSE_ERRORS:
            old = None

        self._plans_provider.upsert_plan(plan)
        with swallow(msg="firebase sync in upsert_plan"):
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_installment_plan(plan)

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
        except PARSE_ERRORS:
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
        except PARSE_ERRORS:
            plan_name = ""

        self._plans_provider.delete_plan(plan_id)
        with swallow(msg="firebase sync in delete_plan"):
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

        with swallow(msg="firebase sync in delete_plan"):
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
        self.upsert_plan(replace(plan, excluded_movement_ids=excluded))

    def post_due_direct_debits(self, today: Optional[date] = None) -> int:
        """Post every due, not-yet-posted direct debit charge as an expense
        movement on its account. Returns how many movements were created.

        Idempotent: each charge has a fixed movement id, and the plan's
        ``posted_count`` advances so a movement the user deleted stays deleted.
        """
        try:
            plans = self._plans_provider.list_plans()
            existing = self._movements_provider.list_movements()
        except PARSE_ERRORS:
            return 0
        from .plan_links import backfill_generated_links, covered_occurrences

        # Charges generated before plan links were stored get their link,
        # only where id, plan and scheduled date agree (idempotent).
        backfilled = {m.id: m for m in backfill_generated_links(existing, plans)}
        if backfilled:
            existing = [backfilled.get(m.id, m) for m in existing]
        existing_ids = {str(m.id) for m in existing}
        # A payment already covered by an expense the user linked to the plan
        # (e.g. imported from the bank) is not generated a second time.
        covered = covered_occurrences(existing)
        new_movements: List[BankMovement] = []
        advanced: List[InstallmentPlan] = []
        for plan in plans:
            due = plan.due_movements(today)
            if not due:
                continue
            new_movements.extend(
                m for m in due
                if str(m.id) not in existing_ids
                and (plan.id, int(m.plan_occurrence or 0)) not in covered
            )
            last = max(int(m.id.rsplit("-", 1)[-1]) for m in due)
            advanced.append(replace(plan, posted_count=last))
        if not new_movements and not advanced and not backfilled:
            return 0

        if new_movements or backfilled:
            self._movements_provider.save_movements(list(existing) + new_movements)
        for plan in advanced:
            self._plans_provider.upsert_plan(plan)

        with swallow(msg="firebase sync in post_due_direct_debits"):
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                w = FirebaseWorkspaceWriter()
                for m in new_movements + list(backfilled.values()):
                    with swallow(msg="push direct debit movement"):
                        w.upsert_movement(m)
                for plan in advanced:
                    with swallow(msg="push direct debit plan"):
                        w.upsert_installment_plan(plan)

        with swallow(msg="history in post_due_direct_debits"):
            from .action_history import AddOutcomeMovementAction

            for m in new_movements:
                self._history_provider.add_action(
                    ActionHistory(
                        id=generate_action_id(),
                        timestamp=get_current_timestamp(),
                        action=AddOutcomeMovementAction(
                            action_name="add_outcome_movement", movement_id=m.id
                        ),
                    )
                )
        return len(new_movements)

    def compute_stats(self, plan: InstallmentPlan) -> InstallmentPlanStats:
        # The plan owns the math; the service just supplies the movements.
        if plan.is_direct_debit:
            return plan.stats([])
        return plan.stats(self._movements_provider.list_movements())
