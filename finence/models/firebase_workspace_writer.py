from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from ..models.firebase_client import FirestoreClient
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_session_manager import FirebaseSessionManager
from ..models.bank_movement import BankMovement
from ..models.one_time_event import OneTimeEvent
from ..models.accounts import (
    MoneyAccount,
    BankAccount,
    BudgetAccount,
    SavingsAccount,
    MoneySnapshot,
)


class FirebaseWorkspaceWriter:
    def __init__(self, session_store: Optional[FirebaseSessionStore] = None) -> None:
        self._store = session_store or FirebaseSessionStore()

    def _load_session_refresh_if_needed(self):
        return FirebaseSessionManager(store=self._store).get_valid_session()

    def _fs(self, project_id: str) -> FirestoreClient:
        return FirestoreClient(project_id=project_id)

    def _wid(self, session) -> str:
        return str(getattr(session, "workspace_id", "") or "").strip()

    def _ensure_workspace(self, session) -> str:
        wid = self._wid(session)
        if not wid:
            raise RuntimeError("Workspace not set")
        return wid

    def upsert_movement(self, movement: BankMovement) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/movements/{movement.id}",
            id_token=s.id_token,
            fields={
                "id": movement.id,
                "amount": float(movement.amount),
                "date": str(movement.date),
                "account_name": str(movement.account_name),
                "category": str(movement.category),
                "type": str(getattr(movement.type, "value", movement.type)),
                "description": movement.description,
                "event_id": getattr(movement, "event_id", None),
                "deleted": False,
                "source": "desktop",
            },
        )

    def delete_movement(self, *, movement_id: str) -> None:
        movement_id = str(movement_id or "").strip()
        if not movement_id:
            return
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/movements/{movement_id}",
            id_token=s.id_token,
            fields={"id": movement_id, "deleted": True, "source": "desktop"},
        )

    def upsert_categories(self, *, income: List[str], outcome: List[str]) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/categories",
            id_token=s.id_token,
            fields={"income": list(income), "outcome": list(outcome), "version": 1},
        )

    def upsert_event(self, event: OneTimeEvent) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/events/{event.id}",
            id_token=s.id_token,
            fields={
                "id": event.id,
                "name": event.name,
                "budget": float(event.budget),
                "status": str(getattr(event.status, "value", event.status)),
                "start_date": event.start_date,
                "end_date": event.end_date,
                "notes": event.notes,
                "deleted": False,
            },
        )

    def delete_event(self, *, event_id: str) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/events/{event_id}",
            id_token=s.id_token,
            fields={"id": event_id, "deleted": True},
        )

    def upsert_accounts_snapshot(self, accounts: List[MoneyAccount]) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)

        bank: List[Dict[str, Any]] = []
        savings: List[Dict[str, Any]] = []
        for acc in accounts:
            if isinstance(acc, BankAccount):
                bank.append(
                    {
                        "kind": "bank",
                        "name": acc.name,
                        "is_liquid": bool(acc.is_liquid),
                        "active": bool(getattr(acc, "active", False)),
                    }
                )
            elif isinstance(acc, BudgetAccount):
                hist: List[Dict[str, Any]] = []
                try:
                    for h in list(getattr(acc, "history", []) or []):
                        if isinstance(h, MoneySnapshot):
                            hist.append(
                                {"date": str(h.date), "amount": float(h.amount)}
                            )
                        elif isinstance(h, dict):
                            hist.append(
                                {
                                    "date": str(h.get("date", "") or ""),
                                    "amount": float(h.get("amount", 0.0) or 0.0),
                                }
                            )
                except Exception:
                    hist = []
                bank.append(
                    {
                        "kind": "budget",
                        "name": acc.name,
                        "is_liquid": False,
                        "active": bool(getattr(acc, "active", False)),
                        "monthly_budget": float(
                            getattr(acc, "monthly_budget", 0.0) or 0.0
                        ),
                        "reset_day": int(getattr(acc, "reset_day", 1) or 1),
                        "last_reset_period": str(
                            getattr(acc, "last_reset_period", "") or ""
                        ),
                        "total_amount": float(getattr(acc, "total_amount", 0.0) or 0.0),
                        "history": hist,
                    }
                )
            elif isinstance(acc, SavingsAccount):
                try:
                    savings.append(
                        asdict(acc) if is_dataclass(acc) else {"name": acc.name}
                    )
                except Exception:
                    savings.append({"name": getattr(acc, "name", "")})

        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/accounts",
            id_token=s.id_token,
            fields={"bank_accounts": bank, "savings_accounts": savings, "version": 1},
        )

    def upsert_action_history(self, entry) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        try:
            action = entry.action
            action_dict = (
                asdict(action)
                if is_dataclass(action) and not isinstance(action, type)
                else {"action_name": str(getattr(action, "action_name", ""))}
            )
        except Exception:
            action_dict = {"action_name": str(getattr(entry.action, "action_name", ""))}
        fs.upsert_document(
            document_path=f"workspaces/{wid}/actions/{entry.id}",
            id_token=s.id_token,
            fields={
                "id": entry.id,
                "timestamp": entry.timestamp,
                "uid": s.uid,
                "action": action_dict,
            },
        )

    def upsert_ml_seed(self, *, examples: List[Dict[str, Any]]) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/ml_seed",
            id_token=s.id_token,
            fields={"examples": list(examples), "version": 1},
        )
