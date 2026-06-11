from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..data.action_history_provider import (
    ActionHistoryProvider,
    JsonFileActionHistoryProvider,
)
from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)
from ..data.mortgage_provider import (
    JsonFileMortgageProvider,
    MortgageProvider,
)
from .action_history import (
    Action,
    ActionHistory,
    generate_action_id,
    get_current_timestamp,
)
from .bank_movement import BankMovement
from .mortgage import Mortgage
from .mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    PurchaseSummary,
    mortgage_outstanding,
    purchase_summary,
)
from .movement_matching import match_movements


@dataclass(frozen=True)
class MortgageStats:
    paid_count: int
    total_paid: float
    matched_movements: List[BankMovement]


class MortgageService:
    def __init__(
        self,
        *,
        mortgages_provider: Optional[MortgageProvider] = None,
        movements_provider: Optional[BankMovementProvider] = None,
        history_provider: Optional[ActionHistoryProvider] = None,
    ) -> None:
        self._mortgages_provider = mortgages_provider or JsonFileMortgageProvider()
        self._movements_provider = (
            movements_provider or JsonFileBankMovementProvider()
        )
        self._history_provider: ActionHistoryProvider = (
            history_provider or JsonFileActionHistoryProvider()
        )

    def list_mortgages(self) -> List[Mortgage]:
        mortgages = self._mortgages_provider.list_mortgages()
        mortgages.sort(
            key=lambda m: (bool(getattr(m, "archived", False)), str(m.name or ""))
        )
        return mortgages

    def upsert_mortgage(self, mortgage: Mortgage) -> None:
        old: Optional[Mortgage] = None
        try:
            for m in self._mortgages_provider.list_mortgages():
                if m.id == mortgage.id:
                    old = m
                    break
        except Exception:
            old = None

        self._mortgages_provider.upsert_mortgage(mortgage)
        try:
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_mortgage(mortgage)
        except Exception:
            pass

        try:
            from .action_history import AddMortgageAction, EditMortgageAction

            action_obj: Action
            if old is None:
                action_obj = AddMortgageAction(
                    action_name="add_mortgage",
                    mortgage_id=mortgage.id,
                    mortgage_name=mortgage.name,
                    account_name=mortgage.account_name,
                    start_date=mortgage.start_date,
                    tracks_count=len(mortgage.tracks),
                    original_principal=float(mortgage.original_principal),
                )
            else:
                old_tracks = len(old.tracks)
                new_tracks = len(mortgage.tracks)
                old_principal = float(old.original_principal)
                new_principal = float(mortgage.original_principal)
                action_obj = EditMortgageAction(
                    action_name="edit_mortgage",
                    mortgage_id=mortgage.id,
                    mortgage_name=mortgage.name,
                    old_name=old.name if old.name != mortgage.name else None,
                    new_name=mortgage.name if old.name != mortgage.name else None,
                    old_account_name=old.account_name
                    if old.account_name != mortgage.account_name
                    else None,
                    new_account_name=mortgage.account_name
                    if old.account_name != mortgage.account_name
                    else None,
                    old_start_date=old.start_date
                    if old.start_date != mortgage.start_date
                    else None,
                    new_start_date=mortgage.start_date
                    if old.start_date != mortgage.start_date
                    else None,
                    old_tracks_count=old_tracks if old_tracks != new_tracks else None,
                    new_tracks_count=new_tracks if old_tracks != new_tracks else None,
                    old_original_principal=old_principal
                    if old_principal != new_principal
                    else None,
                    new_original_principal=new_principal
                    if old_principal != new_principal
                    else None,
                    old_archived=bool(old.archived)
                    if bool(old.archived) != bool(mortgage.archived)
                    else None,
                    new_archived=bool(mortgage.archived)
                    if bool(old.archived) != bool(mortgage.archived)
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

    def delete_mortgage(self, mortgage_id: str) -> None:
        mortgage_id = str(mortgage_id or "").strip()
        if not mortgage_id:
            return
        mortgage_name = ""
        try:
            for m in self._mortgages_provider.list_mortgages():
                if m.id == mortgage_id:
                    mortgage_name = m.name
                    break
        except Exception:
            mortgage_name = ""

        self._mortgages_provider.delete_mortgage(mortgage_id)
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
                add_pending_delete(key=key, kind="mortgage", item_id=mortgage_id)

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().delete_mortgage(mortgage_id=mortgage_id)
        except Exception:
            pass

        try:
            from .action_history import DeleteMortgageAction

            self._history_provider.add_action(
                ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=DeleteMortgageAction(
                        action_name="delete_mortgage",
                        mortgage_id=mortgage_id,
                        mortgage_name=mortgage_name,
                    ),
                )
            )
        except Exception:
            pass

    def total_outstanding(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
        include_archived: bool = False,
    ) -> float:
        """סך יתרת הקרן על פני כל המשכנתאות הפעילות בתאריך נתון."""
        total = 0.0
        for m in self._mortgages_provider.list_mortgages():
            if not include_archived and bool(getattr(m, "archived", False)):
                continue
            try:
                total += mortgage_outstanding(m, as_of_date, assumptions)
            except Exception:
                continue
        return float(total)

    def list_movements(self) -> List[BankMovement]:
        try:
            return list(self._movements_provider.list_movements())
        except Exception:
            return []

    def purchase_summary(self, mortgage: Mortgage) -> PurchaseSummary:
        """סיכום רכישה עם שיוך תנועות בפועל לעלויות חד-פעמיות."""
        return purchase_summary(mortgage, movements=self.list_movements())

    def match_movements(self, mortgage: Mortgage) -> List[BankMovement]:
        """תנועות בנק אמיתיות המשויכות למשכנתא (לפי טקסט הזיהוי והחשבון)."""
        return match_movements(
            self._movements_provider.list_movements(),
            vendor_query=mortgage.vendor_query,
            account_name=mortgage.account_name,
            start_date=str(mortgage.start_date or ""),
            excluded_ids=getattr(mortgage, "excluded_movement_ids", []) or [],
        )

    def compute_stats(self, mortgage: Mortgage) -> MortgageStats:
        matched = self.match_movements(mortgage)
        total_paid = 0.0
        for m in matched:
            try:
                total_paid += abs(float(m.amount))
            except Exception:
                continue
        return MortgageStats(
            paid_count=len(matched),
            total_paid=float(total_paid),
            matched_movements=matched,
        )

    def exclude_movement(self, *, mortgage_id: str, movement_id: str) -> None:
        mortgage_id = str(mortgage_id or "").strip()
        movement_id = str(movement_id or "").strip()
        if not mortgage_id or not movement_id:
            return
        target: Optional[Mortgage] = None
        for m in self._mortgages_provider.list_mortgages():
            if m.id == mortgage_id:
                target = m
                break
        if target is None:
            return
        excluded = list(getattr(target, "excluded_movement_ids", []) or [])
        if movement_id in excluded:
            return
        excluded.append(movement_id)
        self.upsert_mortgage(
            Mortgage(
                id=target.id,
                name=target.name,
                account_name=target.account_name,
                vendor_query=target.vendor_query,
                start_date=target.start_date,
                tracks=list(target.tracks),
                excluded_movement_ids=excluded,
                archived=bool(target.archived),
                property_price=float(target.property_price),
                equity=float(target.equity),
                equity_query=str(target.equity_query),
                one_time_costs=list(target.one_time_costs),
                monthly_costs=list(target.monthly_costs),
                kind=target.kind,
                current_value=float(target.current_value),
            )
        )
