from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from ..models.firebase_client import FirestoreClient
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_session_manager import FirebaseSessionManager
from ..models.bank_movement import BankMovement
from ..models.one_time_event import OneTimeEvent
from ..models.installment_plan import InstallmentPlan
from ..models.notifications import Notification
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
                "is_transfer": bool(getattr(movement, "is_transfer", False)),
                "description": movement.description,
                "event_id": getattr(movement, "event_id", None),
                "deleted": False,
                "source": "desktop",
            },
        )

    def upsert_movements_bulk(
        self, movements: List[BankMovement], *, batch_size: int = 200
    ) -> int:
        items = [m for m in list(movements or []) if isinstance(m, BankMovement)]
        if not items:
            return 0
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        try:
            from ..models.firebase_client import _fs_value  # type: ignore
        except Exception:
            _fs_value = None  # type: ignore
        try:
            import time as _time

            now = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
            now_ms = int(_time.time() * 1000)
        except Exception:
            now = ""
            now_ms = 0

        def _doc_name(mid: str) -> str:
            return (
                f"projects/{s.project_id}/databases/(default)/documents/"
                f"workspaces/{wid}/movements/{mid}"
            )

        writes: List[Dict[str, Any]] = []
        attempted = 0
        for m in items:
            attempted += 1
            fields = {
                "id": str(m.id),
                "amount": float(m.amount),
                "date": str(m.date),
                "account_name": str(m.account_name),
                "category": str(m.category),
                "type": str(getattr(m.type, "value", m.type)),
                "is_transfer": bool(getattr(m, "is_transfer", False)),
                "description": m.description,
                "event_id": getattr(m, "event_id", None),
                "deleted": False,
                "source": "desktop",
                "updated_at": now,
                "updated_at_ms": int(now_ms),
            }
            writes.append(
                {
                    "update": {
                        "name": _doc_name(str(m.id)),
                        "fields": {
                            str(k): (
                                _fs_value(v)
                                if callable(_fs_value)
                                else {"stringValue": str(v)}
                            )
                            for k, v in fields.items()
                        },
                    }
                }
            )

            if len(writes) >= int(batch_size):
                try:
                    fs.commit_writes(id_token=s.id_token, writes=writes)
                except Exception:
                    pass
                writes = []

        if writes:
            try:
                fs.commit_writes(id_token=s.id_token, writes=writes)
            except Exception:
                pass

        return int(attempted)

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

    def upsert_installment_plan(self, plan: InstallmentPlan) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/installment_plans/{plan.id}",
            id_token=s.id_token,
            fields={
                "id": plan.id,
                "name": plan.name,
                "vendor_query": plan.vendor_query,
                "account_name": plan.account_name,
                "start_date": plan.start_date,
                "payments_count": int(plan.payments_count),
                "original_amount": float(plan.original_amount),
                "excluded_movement_ids": list(
                    getattr(plan, "excluded_movement_ids", []) or []
                ),
                "archived": bool(getattr(plan, "archived", False)),
                "deleted": False,
            },
        )

    def delete_installment_plan(self, *, plan_id: str) -> None:
        plan_id = str(plan_id or "").strip()
        if not plan_id:
            return
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/installment_plans/{plan_id}",
            id_token=s.id_token,
            fields={"id": plan_id, "deleted": True},
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
                        "baseline_amount": float(
                            getattr(acc, "baseline_amount", 0.0) or 0.0
                        ),
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

    def upsert_notification(self, notif: Notification) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        doc_id = (
            str(getattr(notif, "key", "") or "").strip()
            or str(getattr(notif, "id", "") or "").strip()
        )
        if not doc_id:
            return
        fs.upsert_document(
            document_path=f"workspaces/{wid}/notifications/{doc_id}",
            id_token=s.id_token,
            fields={
                "id": str(getattr(notif, "id", "") or "").strip(),
                "key": str(getattr(notif, "key", "") or "").strip(),
                "type": str(getattr(getattr(notif, "type", None), "value", notif.type)),
                "title": str(getattr(notif, "title", "") or ""),
                "message": str(getattr(notif, "message", "") or ""),
                "severity": str(
                    getattr(getattr(notif, "severity", None), "value", notif.severity)
                ),
                "created_at": str(getattr(notif, "created_at", "") or ""),
                "status": str(
                    getattr(getattr(notif, "status", None), "value", notif.status)
                ),
                "due_at": getattr(notif, "due_at", None),
                "source": str(getattr(notif, "source", "") or "system"),
                "context": dict(getattr(notif, "context", {}) or {}),
            },
        )

    def upsert_notifications_meta(self, *, enabled: bool, rules: List[dict]) -> None:
        """
        Stores notifications settings (enabled + rules) under a single meta doc.
        """
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        safe_rules: List[dict] = []
        for r in list(rules or []):
            if isinstance(r, dict):
                safe_rules.append(dict(r))
        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/notifications",
            id_token=s.id_token,
            fields={"enabled": bool(enabled), "rules": safe_rules, "version": 1},
        )

    def upsert_user_profile(
        self, *, uid: str, full_name: str, lock_enabled: bool
    ) -> None:
        """
        Stores a per-user profile. Note: password is intentionally not synced.
        """
        uid = str(uid or "").strip()
        if not uid:
            return
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/users/{uid}",
            id_token=s.id_token,
            fields={
                "uid": uid,
                "full_name": str(full_name or ""),
                "lock_enabled": bool(lock_enabled),
                "version": 1,
            },
        )

    def upsert_dashboard_meta(self, meta) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/dashboard",
            id_token=s.id_token,
            fields={
                "total_all": float(getattr(meta, "total_all", 0.0) or 0.0),
                "total_liquid": float(getattr(meta, "total_liquid", 0.0) or 0.0),
                "avg_monthly_income": float(
                    getattr(meta, "avg_monthly_income", 0.0) or 0.0
                ),
                "avg_monthly_expense": float(
                    getattr(meta, "avg_monthly_expense", 0.0) or 0.0
                ),
                "avg_months_count": int(getattr(meta, "avg_months_count", 0) or 0),
                "computed_at": str(getattr(meta, "computed_at", "") or ""),
                "version": 1,
                "source": "desktop",
            },
        )

    def upsert_workspace_grade(self, grade) -> None:
        s = self._load_session_refresh_if_needed()
        wid = self._ensure_workspace(s)
        fs = self._fs(s.project_id)
        fs.upsert_document(
            document_path=f"workspaces/{wid}/meta/grade",
            id_token=s.id_token,
            fields={
                "grade": float(getattr(grade, "grade", 0.0) or 0.0),
                "computed_at": str(getattr(grade, "computed_at", "") or ""),
                "months_used": list(getattr(grade, "months_used", []) or []),
                "components": dict(getattr(grade, "components", {}) or {}),
                "explanations": list(getattr(grade, "explanations", []) or []),
                "grade_version": int(getattr(grade, "grade_version", 1) or 1),
                "version": 1,
                "source": "desktop",
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
