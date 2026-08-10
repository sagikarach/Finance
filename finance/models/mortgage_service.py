from __future__ import annotations

from dataclasses import dataclass, replace
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
    purchase_summary,
)
from .movement_matching import match_movements
from ..utils.safe import PARSE_ERRORS, swallow


@dataclass(frozen=True)
class MortgageStats:
    paid_count: int
    total_paid: float
    matched_movements: List[BankMovement]


@dataclass(frozen=True)
class MatchedTotals:
    """A mortgage's matched movements split into expenses/incomes with sums."""

    expenses: List[BankMovement]
    incomes: List[BankMovement]
    total_paid: float
    total_in: float


@dataclass(frozen=True)
class AssetsSummary:
    """Portfolio headline for the assets page."""

    value: float  # total current value of active assets
    debt: float  # total outstanding mortgage/loan balance
    net: float  # value − debt (net worth)
    count: int  # number of active assets


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
        except PARSE_ERRORS:
            old = None

        self._mortgages_provider.upsert_mortgage(mortgage)

        # Flag this mortgage as a local edit not yet confirmed on the server, so
        # a background (pull-only) sync's remote-wins pull cannot overwrite it
        # before the next Sync pushes it. Cleared once successfully pushed.
        with swallow(msg="firebase sync in upsert_mortgage"):
            from ..models.firebase_session import (
                current_firebase_uid,
                current_firebase_workspace_id,
            )
            from ..models.firebase_sync_state import mark_pending_upsert_mortgage

            key = current_firebase_workspace_id() or current_firebase_uid() or ""
            if key:
                mark_pending_upsert_mortgage(key=key, mortgage_id=mortgage.id)

        with swallow(msg="firebase sync in upsert_mortgage"):
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_mortgage(mortgage)

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
        except PARSE_ERRORS:
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
        except PARSE_ERRORS:
            mortgage_name = ""

        self._mortgages_provider.delete_mortgage(mortgage_id)
        with swallow(msg="firebase sync in delete_mortgage"):
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

        with swallow(msg="firebase sync in delete_mortgage"):
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

    def total_outstanding(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
        include_archived: bool = False,
    ) -> float:
        """סך יתרת הקרן על פני כל המשכנתאות הפעילות בתאריך נתון."""
        from .asset import build_asset

        total = 0.0
        for m in self._mortgages_provider.list_mortgages():
            if not include_archived and bool(getattr(m, "archived", False)):
                continue
            try:
                total += build_asset(m).outstanding_debt(
                    as_of_date=as_of_date, assumptions=assumptions
                )
            except PARSE_ERRORS:
                continue
        return float(total)

    def total_assets_net(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
        include_archived: bool = False,
    ) -> float:
        """שווי נטו של כלל הנכסים הפעילים: סך השווי הנוכחי פחות יתרת החוב
        (משכנתאות/הלוואות). נכסים שנמכרו אינם נספרים. זהו ההון הלא-נזיל
        שמתווסף לסך העושר במסך הראשי."""
        from .asset import build_asset

        value = 0.0
        for m in self._mortgages_provider.list_mortgages():
            if not include_archived and bool(getattr(m, "archived", False)):
                continue
            if bool(getattr(m, "sold", False)):
                continue
            try:
                value += float(build_asset(m).current_value(as_of_date=as_of_date))
            except PARSE_ERRORS:
                continue
        debt = self.total_outstanding(
            as_of_date=as_of_date,
            assumptions=assumptions,
            include_archived=include_archived,
        )
        return float(value - debt)

    def assets_summary(self) -> AssetsSummary:
        """Portfolio figures for the assets page: total current value of active
        assets, total outstanding debt, net worth, and the active-asset count.
        (Active = ``build_asset(m).is_active``, matching the page's own rule.)"""
        from .asset import build_asset

        active = [a for a in self.list_mortgages() if build_asset(a).is_active]
        value = sum(float(build_asset(a).current_value()) for a in active)
        try:
            debt = self.total_outstanding()
        except PARSE_ERRORS:
            debt = 0.0
        return AssetsSummary(
            value=value, debt=debt, net=value - debt, count=len(active)
        )

    def list_movements(self) -> List[BankMovement]:
        try:
            return list(self._movements_provider.list_movements())
        except PARSE_ERRORS:
            return []

    def purchase_summary(self, mortgage: Mortgage) -> PurchaseSummary:
        """סיכום רכישה עם שיוך תנועות בפועל לעלויות חד-פעמיות."""
        return purchase_summary(mortgage, movements=self.list_movements())

    def match_movements(self, mortgage: Mortgage) -> List[BankMovement]:
        """תנועות בנק אמיתיות המשויכות למשכנתא (הוצאות — תשלומים)."""
        return match_movements(
            self._movements_provider.list_movements(),
            vendor_query=mortgage.vendor_query,
            account_name=mortgage.account_name,
            start_date=str(mortgage.start_date or ""),
            excluded_ids=getattr(mortgage, "excluded_movement_ids", []) or [],
        )

    def match_income(self, mortgage: Mortgage) -> List[BankMovement]:
        """תנועות נכנסות המשויכות למשכנתא (הכנסות — לדוגמה מתן הלוואה/החזר)."""
        return match_movements(
            self._movements_provider.list_movements(),
            vendor_query=mortgage.vendor_query,
            account_name=mortgage.account_name,
            start_date=str(mortgage.start_date or ""),
            excluded_ids=getattr(mortgage, "excluded_movement_ids", []) or [],
            include_transfers=True,
            match_income=True,
        )

    def matched_totals(self, mortgage: Mortgage) -> "MatchedTotals":
        """The mortgage's matched expenses and incomes together with their
        summed absolute amounts — everything the movements dialog shows."""
        expenses = self.match_movements(mortgage)
        incomes = self.match_income(mortgage)
        total_paid = sum(abs(float(x.amount)) for x in expenses)
        total_in = sum(abs(float(x.amount)) for x in incomes)
        return MatchedTotals(
            expenses=expenses,
            incomes=incomes,
            total_paid=float(total_paid),
            total_in=float(total_in),
        )

    def compute_stats(self, mortgage: Mortgage) -> MortgageStats:
        matched = self.match_movements(mortgage)
        total_paid = 0.0
        for m in matched:
            try:
                total_paid += abs(float(m.amount))
            except PARSE_ERRORS:
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
        # replace() נושא את כל השדות — עמיד להוספת שדות חדשים בעתיד.
        self.upsert_mortgage(replace(target, excluded_movement_ids=excluded))

    def set_prepayment_movements(
        self, *, mortgage_id: str, movement_ids: List[str]
    ) -> None:
        """קבע את רשימת התנועות (הוצאות חד-פעמיות) המקושרות כפירעון חלקי לקרן."""
        mortgage_id = str(mortgage_id or "").strip()
        if not mortgage_id:
            return
        clean = [str(x) for x in movement_ids if str(x).strip()]
        for m in self._mortgages_provider.list_mortgages():
            if m.id == mortgage_id:
                self.upsert_mortgage(replace(m, prepayment_movement_ids=clean))
                return

    def prepaid_amount(self, mortgage: Mortgage) -> float:
        """סך הפירעונות החלקיים בפועל = סכום התנועות המקושרות (ערך מוחלט)."""
        ids = set(getattr(mortgage, "prepayment_movement_ids", []) or [])
        if not ids:
            return 0.0
        total = 0.0
        for mv in self.list_movements():
            if str(getattr(mv, "id", "")) in ids:
                try:
                    total += abs(float(mv.amount))
                except PARSE_ERRORS:
                    continue
        return float(total)

    def linked_prepayment_movements(self, mortgage: Mortgage) -> List[BankMovement]:
        """התנועות המקושרות כפירעון חלקי."""
        ids = set(getattr(mortgage, "prepayment_movement_ids", []) or [])
        if not ids:
            return []
        return [mv for mv in self.list_movements() if str(getattr(mv, "id", "")) in ids]
