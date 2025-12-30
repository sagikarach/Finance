from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.bank_movement import BankMovement, MovementType
from ..models.action_history import (
    ActionHistory,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    generate_action_id,
    get_current_timestamp,
)
from ..models.firebase_client import FirestoreClient
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_client import FirebaseAuthClient
from ..utils.app_paths import app_data_dir, accounts_data_dir


def _sync_state_path(key: str) -> Path:
    p = app_data_dir() / "firebase"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"sync_state_{key}.json"


@dataclass
class SyncState:
    remote_ids: List[str]
    applied_balance_ids: List[str]
    logged_action_ids: List[str]

    def to_dict(self) -> dict:
        return {
            "remote_ids": list(self.remote_ids),
            "applied_balance_ids": list(self.applied_balance_ids),
            "logged_action_ids": list(self.logged_action_ids),
        }

    @staticmethod
    def from_dict(d: object) -> SyncState:
        if not isinstance(d, dict):
            return SyncState(remote_ids=[], applied_balance_ids=[], logged_action_ids=[])
        raw = d.get("remote_ids", [])
        if not isinstance(raw, list):
            raw = []
        ids = [str(x) for x in raw if isinstance(x, str) and x.strip()]
        raw_applied = d.get("applied_balance_ids", [])
        if not isinstance(raw_applied, list):
            raw_applied = []
        applied = [
            str(x) for x in raw_applied if isinstance(x, str) and str(x).strip()
        ]
        raw_logged = d.get("logged_action_ids", [])
        if not isinstance(raw_logged, list):
            raw_logged = []
        logged = [str(x) for x in raw_logged if isinstance(x, str) and str(x).strip()]
        return SyncState(remote_ids=ids, applied_balance_ids=applied, logged_action_ids=logged)


def _load_sync_state(key: str) -> SyncState:
    path = _sync_state_path(key)
    if not path.exists():
        return SyncState(remote_ids=[], applied_balance_ids=[], logged_action_ids=[])
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        return SyncState.from_dict(raw)
    except Exception:
        return SyncState(remote_ids=[], applied_balance_ids=[], logged_action_ids=[])


class FirebaseMovementsSyncService:
    """
    MVP sync:
    - Pull all user movements from Firestore and merge into local JSON.
    - Push local movements that do not exist remotely yet (by id).
    """

    def __init__(
        self,
        *,
        session_store: Optional[FirebaseSessionStore] = None,
        provider: Optional[JsonFileBankMovementProvider] = None,
    ) -> None:
        self._session_store = session_store or FirebaseSessionStore()
        self._provider = provider or JsonFileBankMovementProvider()

    def ensure_user_local_file(self, key: str) -> None:
        # If user/workspace-specific file doesn't exist yet, copy the legacy shared file.
        dst = accounts_data_dir() / f"bank_movements_{key}.json"
        if dst.exists():
            return
        src = accounts_data_dir() / "bank_movements.json"
        if not src.exists():
            return
        try:
            dst.write_bytes(src.read_bytes())
        except Exception:
            pass

    def _load_session_refresh_if_needed(self):
        session = self._session_store.load()
        if not session.is_logged_in or not session.id_token:
            raise RuntimeError("Not logged in")
        # Refresh token if needed
        try:
            if not session.is_id_token_valid():
                auth = FirebaseAuthClient(api_key=session.api_key)
                id_token, refresh_token, expires_in = auth.refresh_id_token(
                    refresh_token=session.refresh_token
                )
                session.id_token = id_token
                session.refresh_token = refresh_token
                session.expires_at = __import__("time").time() + float(expires_in)
                self._session_store.save(session)
        except Exception:
            pass
        return session

    def sync_categories_only(self) -> None:
        session = self._load_session_refresh_if_needed()
        wid = str(getattr(session, "workspace_id", "") or "").strip()
        uid = session.uid
        key = wid or uid
        self.ensure_user_local_file(key)
        fs = FirestoreClient(project_id=session.project_id)
        self._sync_categories(
            fs=fs, workspace_id=wid, uid=uid, id_token=session.id_token, allow_push=True
        )

    # NOTE: This service performs pull-only sync. Push happens on every write action elsewhere.

    def sync_now(self, *, allow_push: bool = False) -> Tuple[int, int]:
        session = self._load_session_refresh_if_needed()
        wid = str(getattr(session, "workspace_id", "") or "").strip()
        uid = session.uid
        key = wid or uid
        self.ensure_user_local_file(key)
        state = _load_sync_state(key)

        fs = FirestoreClient(project_id=session.project_id)

        # Pull-only categories: bring remote categories into local cache.
        try:
            self._sync_categories(
                fs=fs,
                workspace_id=wid,
                uid=uid,
                id_token=session.id_token,
                allow_push=False,
            )
        except Exception:
            pass

        if wid:
            docs = fs.list_workspace_movements(
                workspace_id=wid, id_token=session.id_token
            )
        else:
            docs = fs.list_user_movements(uid=uid, id_token=session.id_token)

        pulled = 0
        remote_ids: List[str] = []
        remote_by_id: Dict[str, dict] = {}
        for d in docs:
            mid, fields = fs.parse_doc(d)
            if not mid:
                continue
            remote_ids.append(mid)
            remote_by_id[mid] = fields

        local = self._provider.list_movements()
        local_by_id = {m.id: m for m in local}

        # Pull: merge remote into local
        for mid, f in remote_by_id.items():
            try:
                if bool(f.get("deleted", False)):
                    if mid in local_by_id:
                        local_by_id.pop(mid, None)
                        pulled += 1
                    continue

                amount = float(f.get("amount", 0.0) or 0.0)
                date = str(f.get("date", "") or "").strip()
                account_name = str(f.get("account_name", "") or "").strip()
                category = str(f.get("category", "") or "").strip()
                t_raw = str(f.get("type", "") or "").strip()
                movement_type = _parse_movement_type(t_raw)
                description = f.get("description")
                desc_str = str(description) if isinstance(description, str) and description else None
                event_id = f.get("event_id")
                event_id_str = str(event_id).strip() if isinstance(event_id, str) and str(event_id).strip() else None

                if not date or not account_name:
                    continue

                local_by_id[mid] = BankMovement(
                    amount=amount,
                    date=date,
                    account_name=account_name,
                    category=category,
                    type=movement_type,
                    description=desc_str,
                    event_id=event_id_str,
                    id=mid,
                )
                pulled += 1
            except Exception:
                continue

        self._provider.save_movements(list(local_by_id.values()))

        # Pull events (workspace) into local cache.
        try:
            if wid:
                from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
                from ..models.one_time_event import OneTimeEvent, OneTimeEventStatus

                docs_events = fs.list_collection(
                    collection_path=f"workspaces/{wid}/events",
                    id_token=session.id_token,
                )
                events: List[OneTimeEvent] = []
                for d in docs_events:
                    try:
                        doc_id, parsed = fs.parse_any_doc(d)
                        if bool(parsed.get("deleted", False)):
                            continue
                        eid = str(parsed.get("id") or doc_id).strip()
                        name = str(parsed.get("name") or "").strip()
                        budget = float(parsed.get("budget") or 0.0)
                        status_raw = str(parsed.get("status") or OneTimeEventStatus.ACTIVE.value)
                        try:
                            status = OneTimeEventStatus(status_raw)
                        except Exception:
                            status = OneTimeEventStatus.ACTIVE
                        start_date = parsed.get("start_date")
                        end_date = parsed.get("end_date")
                        notes = parsed.get("notes")
                        events.append(
                            OneTimeEvent(
                                id=eid,
                                name=name,
                                budget=budget,
                                status=status,
                                start_date=str(start_date) if isinstance(start_date, str) and str(start_date).strip() else None,
                                end_date=str(end_date) if isinstance(end_date, str) and str(end_date).strip() else None,
                                notes=str(notes) if isinstance(notes, str) and str(notes).strip() else None,
                            )
                        )
                    except Exception:
                        continue
                JsonFileOneTimeEventProvider().save_events(events)
        except Exception:
            pass

        # Pull account definitions (workspace) into local cache.
        # Option A: bank balances are derived from movements, so we preserve local totals/history.
        try:
            if wid:
                from ..data.provider import JsonFileAccountsProvider
                from ..models.accounts import BankAccount, MoneySnapshot, Savings, SavingsAccount
                from ..models.accounts_service import AccountsService

                doc = fs.get_document(
                    document_path=f"workspaces/{wid}/meta/accounts",
                    id_token=session.id_token,
                )
                _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
                remote_bank = parsed.get("bank_accounts", [])
                remote_savings = parsed.get("savings_accounts", [])

                provider = JsonFileAccountsProvider()
                svc = AccountsService(provider)
                local_accounts = svc.load_accounts()
                local_bank_by_name = {
                    a.name: a for a in local_accounts if isinstance(a, BankAccount)
                }

                bank_accounts: List[BankAccount] = []
                if isinstance(remote_bank, list):
                    for row in remote_bank:
                        if not isinstance(row, dict):
                            continue
                        name = str(row.get("name", "") or "").strip()
                        if not name:
                            continue
                        is_liquid = bool(row.get("is_liquid", False))
                        active = bool(row.get("active", False))
                        existing = local_bank_by_name.get(name)
                        if isinstance(existing, BankAccount):
                            bank_accounts.append(
                                BankAccount(
                                    name=name,
                                    total_amount=float(existing.total_amount),
                                    is_liquid=is_liquid,
                                    history=list(existing.history),
                                    active=active,
                                )
                            )
                        else:
                            bank_accounts.append(
                                BankAccount(
                                    name=name,
                                    total_amount=0.0,
                                    is_liquid=is_liquid,
                                    history=[],
                                    active=active,
                                )
                            )

                savings_accounts: List[SavingsAccount] = []
                if isinstance(remote_savings, list):
                    for row in remote_savings:
                        if not isinstance(row, dict):
                            continue
                        name = str(row.get("name", "") or "").strip()
                        if not name:
                            continue
                        is_liquid = bool(row.get("is_liquid", False))
                        savings_rows = row.get("savings", [])
                        savings: List[Savings] = []
                        if isinstance(savings_rows, list):
                            for srow in savings_rows:
                                if not isinstance(srow, dict):
                                    continue
                                sname = str(srow.get("name", "") or "").strip()
                                if not sname:
                                    continue
                                history_rows = srow.get("history", [])
                                hist: List[MoneySnapshot] = []
                                if isinstance(history_rows, list):
                                    for h in history_rows:
                                        if not isinstance(h, dict):
                                            continue
                                        date_str = str(h.get("date", "") or "").strip()
                                        try:
                                            amt = float(h.get("amount", 0.0) or 0.0)
                                        except Exception:
                                            amt = 0.0
                                        if date_str:
                                            hist.append(
                                                MoneySnapshot(date=date_str, amount=amt)
                                            )
                                try:
                                    amt = float(srow.get("amount", 0.0) or 0.0)
                                except Exception:
                                    amt = 0.0
                                savings.append(Savings(name=sname, amount=amt, history=hist))

                        savings_accounts.append(
                            SavingsAccount(
                                name=name,
                                total_amount=0.0,
                                is_liquid=is_liquid,
                                savings=savings,
                            )
                        )

                provider.save_bank_accounts(bank_accounts)
                provider.save_savings_accounts(savings_accounts)
        except Exception:
            pass

        # Pull action history from Firebase (workspace) on sync.
        try:
            if wid:
                docs_actions = fs.list_collection(
                    collection_path=f"workspaces/{wid}/actions",
                    id_token=session.id_token,
                )
                history_provider = JsonFileActionHistoryProvider()
                local_hist = history_provider.list_history()
                by_id = {h.id: h for h in local_hist}
                for doc in docs_actions:
                    try:
                        doc_id, parsed = fs.parse_any_doc(doc)
                        hid = str(parsed.get("id") or doc_id).strip()
                        ts = str(parsed.get("timestamp") or "").strip()
                        action_data = parsed.get("action") or {}
                        if not hid or not ts or not isinstance(action_data, dict):
                            continue
                        if hid in by_id:
                            continue
                        action_obj = history_provider._deserialize_action(action_data)  # type: ignore[attr-defined]
                        if action_obj is None:
                            continue
                        by_id[hid] = ActionHistory(id=hid, timestamp=ts, action=action_obj)
                    except Exception:
                        continue
                history_provider.save_history(list(by_id.values()))
        except Exception:
            pass

        # Apply remote (mobile) movements to account balances exactly once.
        # Desktop is pull-only, so remote movements are expected to be mobile-created
        # and were not previously applied to local account snapshots.
        try:
            to_apply = [
                mid
                for mid in remote_by_id.keys()
                if mid not in set(state.applied_balance_ids)
                and not bool(remote_by_id.get(mid, {}).get("deleted", False))
            ]
            if to_apply:
                self._apply_to_account_balances(
                    movements=[local_by_id[mid] for mid in to_apply if mid in local_by_id]
                )
                state.applied_balance_ids = list(set(state.applied_balance_ids) | set(to_apply))
        except Exception:
            pass

        pushed = 0
        remote_set = set(remote_ids)

        # Save sync state (helps future optimizations)
        try:
            state.remote_ids = list(remote_set | {m.id for m in local_by_id.values()})
            _sync_state_path(key).write_text(
                json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

        return pulled, pushed

    def _apply_to_account_balances(self, *, movements: List[BankMovement]) -> None:
        if not movements:
            return
        try:
            from datetime import date as _date

            today = _date.today().isoformat()
        except Exception:
            today = ""

        # Sum deltas per bank account
        delta_by_account: Dict[str, float] = {}
        for m in movements:
            try:
                name = str(m.account_name or "").strip()
                if not name:
                    continue
                delta_by_account[name] = delta_by_account.get(name, 0.0) + float(m.amount)
            except Exception:
                continue

        if not delta_by_account:
            return

        from ..data.provider import JsonFileAccountsProvider
        from ..models.accounts_service import AccountsService
        from ..models.accounts import BankAccount, MoneySnapshot, MoneyAccount

        provider = JsonFileAccountsProvider()
        svc = AccountsService(provider)
        accounts = svc.load_accounts()

        updated: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, BankAccount) and acc.name in delta_by_account:
                delta = float(delta_by_account.get(acc.name, 0.0))
                try:
                    current_total = float(acc.total_amount)
                except Exception:
                    current_total = 0.0
                new_total = current_total + delta
                new_history = list(acc.history)
                if today:
                    new_history.append(MoneySnapshot(date=today, amount=new_total))
                updated.append(
                    BankAccount(
                        name=acc.name,
                        total_amount=new_total,
                        is_liquid=acc.is_liquid,
                        history=new_history,
                        active=acc.active,
                    )
                )
            else:
                updated.append(acc)

        svc.save_all(updated)

    def _sync_categories(
        self,
        *,
        fs: FirestoreClient,
        workspace_id: str,
        uid: str,
        id_token: str,
        allow_push: bool,
    ) -> None:
        workspace_id = (workspace_id or "").strip()
        if workspace_id:
            doc_path = f"workspaces/{workspace_id}/meta/categories"
        else:
            doc_path = f"users/{uid}/meta/categories"

        # Remote
        remote_income: List[str] = []
        remote_outcome: List[str] = []
        try:
            doc = fs.get_document(document_path=doc_path, id_token=id_token)
            _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
            ri = parsed.get("income", [])
            ro = parsed.get("outcome", [])
            if isinstance(ri, list):
                remote_income = [str(x).strip() for x in ri if isinstance(x, str) and str(x).strip()]
            if isinstance(ro, list):
                remote_outcome = [str(x).strip() for x in ro if isinstance(x, str) and str(x).strip()]
        except Exception:
            remote_income = []
            remote_outcome = []

        # Local
        try:
            local_income = list(self._provider.list_categories_for_type(True))
        except Exception:
            local_income = []
        try:
            local_outcome = list(self._provider.list_categories_for_type(False))
        except Exception:
            local_outcome = []

        merged_income = sorted({*(remote_income), *(local_income)})
        merged_outcome = sorted({*(remote_outcome), *(local_outcome)})

        # Push only when explicitly requested (push-on-write flows).
        if allow_push:
            fs.upsert_document(
                document_path=doc_path,
                id_token=id_token,
                fields={
                    "income": merged_income,
                    "outcome": merged_outcome,
                    "version": 1,
                },
            )

        # Pull merged lists into local (so mobile-added categories appear on desktop too)
        try:
            for c in merged_income:
                self._provider.add_category_for_type(c, True)
            for c in merged_outcome:
                self._provider.add_category_for_type(c, False)
        except Exception:
            pass


def _parse_movement_type(raw: str) -> MovementType:
    raw = (raw or "").strip()
    if raw in ("MONTHLY", "monthly"):
        return MovementType.MONTHLY
    if raw in ("YEARLY", "yearly"):
        return MovementType.YEARLY
    if raw in ("ONE_TIME", "one_time", "onetime"):
        return MovementType.ONE_TIME
    # Accept existing Hebrew values
    try:
        return MovementType(raw)
    except Exception:
        return MovementType.ONE_TIME


def _movement_to_firestore_fields(m: BankMovement) -> dict:
    # Store portable type codes (not Hebrew) so mobile can use them easily.
    type_code = "ONE_TIME"
    try:
        if m.type == MovementType.MONTHLY:
            type_code = "MONTHLY"
        elif m.type == MovementType.YEARLY:
            type_code = "YEARLY"
        else:
            type_code = "ONE_TIME"
    except Exception:
        type_code = "ONE_TIME"
    return {
        "id": m.id,
        "amount": float(m.amount),
        "date": str(m.date),
        "account_name": str(m.account_name),
        "category": str(m.category),
        "type": type_code,
        "description": m.description,
        "event_id": getattr(m, "event_id", None),
        "deleted": False,
        "source": "desktop",
    }


