from __future__ import annotations

from typing import List, Optional, Tuple

from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)
from ..data.one_time_event_provider import (
    JsonFileOneTimeEventProvider,
    OneTimeEventProvider,
)
from ..data.action_history_provider import (
    ActionHistoryProvider,
    JsonFileActionHistoryProvider,
)
from .accounts import parse_iso_date
from .bank_movement import BankMovement, MovementType
from .action_history import (
    ActionHistory,
    Action,
    AddOneTimeEventAction,
    EditOneTimeEventAction,
    DeleteOneTimeEventAction,
    AssignMovementToOneTimeEventAction,
    UnassignMovementFromOneTimeEventAction,
    generate_action_id,
    get_current_timestamp,
)
from .one_time_event import EventTotals, OneTimeEvent, OneTimeEventStatus


class OneTimeEventsService:
    def __init__(
        self,
        *,
        events_provider: Optional[OneTimeEventProvider] = None,
        movements_provider: Optional[BankMovementProvider] = None,
        history_provider: Optional[ActionHistoryProvider] = None,
    ) -> None:
        self._events_provider = events_provider or JsonFileOneTimeEventProvider()
        self._movements_provider = movements_provider or JsonFileBankMovementProvider()
        self._history_provider: ActionHistoryProvider = (
            history_provider or JsonFileActionHistoryProvider()
        )

    def list_events(self) -> List[OneTimeEvent]:
        events = self._events_provider.list_events()
        events.sort(key=lambda e: (str(e.status.value), e.name))
        return events

    def upsert_event(self, event: OneTimeEvent) -> None:
        old = None
        try:
            for e in self._events_provider.list_events():
                if e.id == event.id:
                    old = e
                    break
        except Exception:
            old = None
        self._events_provider.upsert_event(event)
        try:
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_event(event)
        except Exception:
            pass
        try:
            action_obj: Action
            if old is None:
                action_obj = AddOneTimeEventAction(
                    action_name="add_one_time_event",
                    event_id=event.id,
                    event_name=event.name,
                    budget=float(event.budget),
                    status=str(event.status.value),
                )
            else:
                old_name = old.name if old.name != event.name else None
                new_name = event.name if old.name != event.name else None
                old_budget = (
                    float(old.budget)
                    if float(old.budget) != float(event.budget)
                    else None
                )
                new_budget = (
                    float(event.budget)
                    if float(old.budget) != float(event.budget)
                    else None
                )
                old_status = (
                    str(old.status.value)
                    if str(old.status.value) != str(event.status.value)
                    else None
                )
                new_status = (
                    str(event.status.value)
                    if str(old.status.value) != str(event.status.value)
                    else None
                )
                action_obj = EditOneTimeEventAction(
                    action_name="edit_one_time_event",
                    event_id=event.id,
                    event_name=event.name,
                    old_name=old_name,
                    new_name=new_name,
                    old_budget=old_budget,
                    new_budget=new_budget,
                    old_status=old_status,
                    new_status=new_status,
                )
            history_entry = ActionHistory(
                id=generate_action_id(),
                timestamp=get_current_timestamp(),
                action=action_obj,
            )
            self._history_provider.add_action(history_entry)
        except Exception:
            pass

    def delete_event(self, event_id: str) -> None:
        event_name = ""
        try:
            for e in self._events_provider.list_events():
                if e.id == event_id:
                    event_name = e.name
                    break
        except Exception:
            event_name = ""
        self._events_provider.delete_event(event_id)
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
                add_pending_delete(key=key, kind="event", item_id=event_id)

            if allow_firebase_push():
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().delete_event(event_id=event_id)
        except Exception:
            pass
        movements = self._movements_provider.list_movements()
        updated: List[BankMovement] = []
        changed = False
        unassigned_ids: List[str] = []
        for m in movements:
            if getattr(m, "event_id", None) == event_id:
                try:
                    unassigned_ids.append(str(m.id))
                except Exception:
                    pass
                updated.append(
                    BankMovement(
                        amount=m.amount,
                        date=m.date,
                        account_name=m.account_name,
                        category=m.category,
                        type=m.type,
                        description=m.description,
                        event_id=None,
                        id=m.id,
                        is_transfer=bool(getattr(m, "is_transfer", False)),
                    )
                )
                changed = True
            else:
                updated.append(m)
        if changed:
            self._movements_provider.save_movements(updated)
            try:
                from ..models.sync_gate import allow_firebase_push

                if allow_firebase_push():
                    from ..models.firebase_workspace_writer import (
                        FirebaseWorkspaceWriter,
                    )

                    w = FirebaseWorkspaceWriter()
                    _unassigned_set = set(unassigned_ids)
                    for m in updated:
                        try:
                            if getattr(m, "id", "") in _unassigned_set:
                                w.upsert_movement(m)
                        except Exception:
                            continue
            except Exception:
                pass
        try:
            action_obj = DeleteOneTimeEventAction(
                action_name="delete_one_time_event",
                event_id=event_id,
                event_name=event_name,
                unassigned_movement_ids=list(unassigned_ids),
            )
            history_entry = ActionHistory(
                id=generate_action_id(),
                timestamp=get_current_timestamp(),
                action=action_obj,
            )
            self._history_provider.add_action(history_entry)
        except Exception:
            pass

    def list_one_time_movements(self) -> List[BankMovement]:
        out: List[BankMovement] = []
        for m in self._movements_provider.list_movements():
            try:
                if m.type == MovementType.ONE_TIME:
                    out.append(m)
            except Exception:
                continue
        out.sort(key=lambda m: parse_iso_date(m.date))
        return out

    def assign_movement(self, movement_id: str, event_id: Optional[str]) -> None:
        movements = self._movements_provider.list_movements()
        updated: List[BankMovement] = []
        changed = False
        previous_event_id: Optional[str] = None
        for m in movements:
            if m.id != movement_id:
                updated.append(m)
                continue
            if m.type != MovementType.ONE_TIME:
                updated.append(m)
                continue
            try:
                previous_event_id = getattr(m, "event_id", None)
            except Exception:
                previous_event_id = None
            if getattr(m, "event_id", None) == event_id:
                updated.append(m)
                continue
            updated.append(
                BankMovement(
                    amount=m.amount,
                    date=m.date,
                    account_name=m.account_name,
                    category=m.category,
                    type=m.type,
                    description=m.description,
                    event_id=event_id,
                    id=m.id,
                    is_transfer=bool(getattr(m, "is_transfer", False)),
                )
            )
            changed = True
        if changed:
            self._movements_provider.save_movements(updated)
            try:
                from ..models.sync_gate import allow_firebase_push

                if allow_firebase_push():
                    from ..models.firebase_workspace_writer import (
                        FirebaseWorkspaceWriter,
                    )

                    for m in updated:
                        if m.id == movement_id:
                            FirebaseWorkspaceWriter().upsert_movement(m)
                            break
            except Exception:
                pass
            try:
                action_obj: Action
                if event_id is None:
                    action_obj = UnassignMovementFromOneTimeEventAction(
                        action_name="unassign_movement_from_one_time_event",
                        movement_id=movement_id,
                        previous_event_id=previous_event_id,
                    )
                else:
                    action_obj = AssignMovementToOneTimeEventAction(
                        action_name="assign_movement_to_one_time_event",
                        movement_id=movement_id,
                        event_id=event_id,
                    )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action_obj,
                )
                self._history_provider.add_action(history_entry)
            except Exception:
                pass

    def event_totals(self, event: OneTimeEvent) -> EventTotals:
        # The event owns the aggregation; the service just supplies the movements.
        return event.totals(self.list_one_time_movements())

    def movements_for_event(
        self, event: OneTimeEvent
    ) -> Tuple[List[BankMovement], List[BankMovement]]:
        movements = self.list_one_time_movements()
        in_range = self._filter_by_range(event, movements)
        assigned: List[BankMovement] = []
        unassigned: List[BankMovement] = []
        for m in in_range:
            if getattr(m, "event_id", None) == event.id:
                assigned.append(m)
            elif getattr(m, "event_id", None) in (None, ""):
                unassigned.append(m)
        assigned.sort(key=lambda m: parse_iso_date(m.date))
        unassigned.sort(key=lambda m: parse_iso_date(m.date))
        return assigned, unassigned

    def _filter_by_range(
        self, event: OneTimeEvent, movements: List[BankMovement]
    ) -> List[BankMovement]:
        return [m for m in movements if event.in_range(m)]

    @staticmethod
    def default_event(name: str = "אירוע חדש") -> OneTimeEvent:
        return OneTimeEvent(name=name, budget=0.0, status=OneTimeEventStatus.ACTIVE)
