from __future__ import annotations

import json
import time
import threading
from typing import Dict, List, Optional, Tuple

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import JsonFileAccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts_service import AccountsService
from ..models.bank_movement import BankMovement
from ..models.firebase_client import FirestoreClient
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_session_manager import FirebaseSessionManager
from ..utils.app_paths import accounts_data_dir, app_data_dir
from ..models.firebase_sync_state import load_sync_state, save_sync_state
from ..models.firebase_sync_categories import sync_categories
from ..models.firebase_sync_pullers import (
    pull_remote_movements,
    merge_remote_into_local,
)
from ..models.firebase_sync_workspace_cache import (
    pull_events_to_local_cache,
    pull_installment_plans_to_local_cache,
    pull_notifications_to_local_cache,
    pull_notifications_meta_to_local_cache,
    pull_user_profile_to_local_cache,
    pull_ml_seed_best_effort,
)
from ..models.firebase_sync_accounts_meta import pull_accounts_meta_to_local_cache
from ..models.firebase_sync_action_history import pull_action_history_to_local_cache
from ..models.firebase_sync_balance_apply import (
    apply_movements_to_account_balances_once,
)


class FirebaseMovementsSyncService:
    _SYNC_LOCK = threading.Lock()

    def __init__(
        self,
        *,
        session_store: Optional[FirebaseSessionStore] = None,
        provider: Optional[JsonFileBankMovementProvider] = None,
    ) -> None:
        self._session_store = session_store or FirebaseSessionStore()
        self._provider = provider or JsonFileBankMovementProvider()
        self._accounts_provider = JsonFileAccountsProvider()
        self._accounts_service = AccountsService(self._accounts_provider)
        self._history_provider = JsonFileActionHistoryProvider()

    def ensure_user_local_file(self, key: str) -> None:
        dst = accounts_data_dir() / f"bank_movements_{key}.json"
        if dst.exists():
            return
        src = accounts_data_dir() / "bank_movements.json"
        try:
            wid = str(self._session_store.load().workspace_id or "").strip()
        except Exception:
            wid = ""
        if wid and str(key or "").strip() == wid:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.exists():
                    dst.write_bytes(src.read_bytes())
                else:
                    dst.write_text("[]", encoding="utf-8")
            except Exception:
                pass
            return
        try:
            any_scoped = False
            for p in accounts_data_dir().glob("bank_movements_*.json"):
                try:
                    if p.is_file():
                        any_scoped = True
                        break
                except Exception:
                    continue
            if (not any_scoped) and src.exists():
                try:
                    dst.write_bytes(src.read_bytes())
                    return
                except Exception:
                    pass
        except Exception:
            pass
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text("[]", encoding="utf-8")
        except Exception:
            pass

    def _load_session_refresh_if_needed(self):
        return FirebaseSessionManager(store=self._session_store).get_valid_session()

    def _best_effort(self, fn, *args, **kwargs) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            return

    def _sync_categories_pull_only(
        self, *, fs: FirestoreClient, wid: str, uid: str, id_token: str
    ) -> None:
        sync_categories(
            fs=fs,
            workspace_id=wid,
            uid=uid,
            id_token=id_token,
            provider=self._provider,
            allow_push=False,
        )

    def _pull_and_merge_movements(
        self,
        *,
        fs: FirestoreClient,
        wid: str,
        uid: str,
        id_token: str,
        state=None,
    ) -> Tuple[int, List[str], Dict[str, dict], Dict[str, BankMovement]]:
        updated_after = ""
        updated_after_ms = 0
        try:
            updated_after = str(
                getattr(state, "last_remote_updated_at", "") or ""
            ).strip()
        except Exception:
            updated_after = ""
        try:
            updated_after_ms = int(getattr(state, "last_remote_updated_at_ms", 0) or 0)
        except Exception:
            updated_after_ms = 0

        remote_ids, remote_by_id = pull_remote_movements(
            fs=fs,
            workspace_id=wid,
            uid=uid,
            id_token=id_token,
            updated_after=updated_after,
            updated_after_ms=updated_after_ms,
        )
        local = self._provider.list_movements()
        local_by_id = {m.id: m for m in local}
        pulled = merge_remote_into_local(
            remote_by_id=remote_by_id, local_by_id=local_by_id
        )
        self._provider.save_movements(list(local_by_id.values()))

        # Advance incremental watermark (best-effort)
        try:
            max_u = updated_after
            max_ms = int(updated_after_ms or 0)
            for _mid, f in remote_by_id.items():
                u = str(f.get("updated_at", "") or "").strip()
                if u and (not max_u or u > max_u):
                    max_u = u
                try:
                    ums = int(f.get("updated_at_ms", 0) or 0)
                except Exception:
                    ums = 0
                if ums and ums > max_ms:
                    max_ms = ums
            if state is not None and max_u:
                state.last_remote_updated_at = str(max_u)
            if state is not None and max_ms > 0:
                state.last_remote_updated_at_ms = int(max_ms)
        except Exception:
            pass

        return pulled, remote_ids, remote_by_id, local_by_id

    def _pull_workspace_caches(
        self,
        *,
        fs: FirestoreClient,
        wid: str,
        uid: str,
        id_token: str,
        allow_push: bool,
    ) -> None:
        if not wid:
            return
        # Run sequentially for stability (avoid native crashes seen under heavy concurrent pulls).
        pull_ml_seed_best_effort(workspace_id=wid, ensure_in_firebase=bool(allow_push))
        pull_events_to_local_cache(fs=fs, workspace_id=wid, id_token=id_token)
        pull_installment_plans_to_local_cache(
            fs=fs, workspace_id=wid, id_token=id_token
        )
        pull_notifications_to_local_cache(fs=fs, workspace_id=wid, id_token=id_token)
        pull_notifications_meta_to_local_cache(
            fs=fs, workspace_id=wid, id_token=id_token
        )
        pull_user_profile_to_local_cache(
            fs=fs, workspace_id=wid, uid=str(uid or ""), id_token=id_token
        )
        pull_accounts_meta_to_local_cache(
            fs=fs,
            workspace_id=wid,
            id_token=id_token,
            accounts_provider=self._accounts_provider,
            accounts_service=self._accounts_service,
        )
        pull_action_history_to_local_cache(
            fs=fs,
            workspace_id=wid,
            id_token=id_token,
            history_provider=self._history_provider,
        )

    def _apply_balances_once(
        self,
        *,
        state,
        local_by_id: Dict[str, BankMovement],
        remote_by_id: Dict[str, dict],
    ) -> None:
        state.applied_balance_ids = apply_movements_to_account_balances_once(
            local_by_id=local_by_id,
            remote_by_id=remote_by_id,
            applied_balance_ids=state.applied_balance_ids,
            accounts_service=self._accounts_service,
        )

    def sync_categories_only(self) -> None:
        try:
            from ..models.sync_gate import allow_firebase_push

            if not allow_firebase_push():
                return
        except Exception:
            return
        session = self._load_session_refresh_if_needed()
        wid = str(getattr(session, "workspace_id", "") or "").strip()
        uid = session.uid
        key = wid or uid
        self.ensure_user_local_file(key)
        fs = FirestoreClient(project_id=session.project_id)
        sync_categories(
            fs=fs,
            workspace_id=wid,
            uid=uid,
            id_token=session.id_token,
            provider=self._provider,
            allow_push=True,
        )

    def sync_now(self, *, allow_push: bool = False) -> Tuple[int, int]:
        from ..models.sync_gate import sync_context

        lock = FirebaseMovementsSyncService._SYNC_LOCK
        if not lock.acquire(blocking=False):
            # Another sync is already running; avoid concurrent pulls to prevent crashes.
            return 0, 0

        try:
            t0 = time.perf_counter()
            session = self._load_session_refresh_if_needed()
            wid = str(getattr(session, "workspace_id", "") or "").strip()
            uid = session.uid
            key = wid or uid
            self.ensure_user_local_file(key)
            state = load_sync_state(key)

            fs = FirestoreClient(project_id=session.project_id)

            t_push = 0.0
            pushed = 0
            with sync_context():
                if bool(allow_push):
                    t_push0 = time.perf_counter()
                    pushed = self._push_all_local(
                        fs=fs, wid=wid, uid=uid, id_token=session.id_token, state=state
                    )
                    self._best_effort(self._push_dashboard_meta)
                    t_push = float(time.perf_counter() - t_push0)

            t_cat0 = time.perf_counter()
            self._best_effort(
                self._sync_categories_pull_only,
                fs=fs,
                wid=wid,
                uid=uid,
                id_token=session.id_token,
            )
            t_cat = float(time.perf_counter() - t_cat0)

            t_mov0 = time.perf_counter()
            pulled, remote_ids, remote_by_id, local_by_id = (
                self._pull_and_merge_movements(
                    fs=fs, wid=wid, uid=uid, id_token=session.id_token, state=state
                )
            )
            t_mov = float(time.perf_counter() - t_mov0)

            t_cache0 = time.perf_counter()
            self._best_effort(
                self._pull_workspace_caches,
                fs=fs,
                wid=wid,
                uid=uid,
                id_token=session.id_token,
                allow_push=bool(allow_push),
            )
            t_cache = float(time.perf_counter() - t_cache0)

            t_bal0 = time.perf_counter()
            self._best_effort(
                self._apply_balances_once,
                state=state,
                local_by_id=local_by_id,
                remote_by_id=remote_by_id,
            )
            t_bal = float(time.perf_counter() - t_bal0)

            remote_set = set(remote_ids)

            state.remote_ids = list(remote_set | {m.id for m in local_by_id.values()})
            self._best_effort(save_sync_state, key, state)

            # Save timings to help diagnose slow syncs
            try:
                p = app_data_dir() / "firebase"
                p.mkdir(parents=True, exist_ok=True)
                (p / "last_sync_profile.json").write_text(
                    json.dumps(
                        {
                            "workspace_id": wid,
                            "allow_push": bool(allow_push),
                            "pulled": int(pulled),
                            "pushed": int(pushed),
                            "remote_docs_seen": int(len(remote_by_id or {})),
                            "timings_sec": {
                                "total": float(time.perf_counter() - t0),
                                "push_all_local": float(t_push),
                                "sync_categories_pull_only": float(t_cat),
                                "pull_movements_merge_save": float(t_mov),
                                "pull_workspace_caches": float(t_cache),
                                "apply_balances_once": float(t_bal),
                            },
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except Exception:
                pass

            return pulled, pushed
        finally:
            try:
                lock.release()
            except Exception:
                pass

    def _push_all_local(
        self, *, fs: FirestoreClient, wid: str, uid: str, id_token: str, state
    ) -> int:
        pushed = 0
        if not wid or not id_token:
            return 0
        try:
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter
            from ..data.provider import JsonFileAccountsProvider
            from ..models.accounts_service import AccountsService
            from ..data.notifications_provider import JsonFileNotificationsProvider
            from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
            from ..data.installment_plan_provider import JsonFileInstallmentPlanProvider
            from ..data.action_history_provider import JsonFileActionHistoryProvider
            from ..models.firebase_sync_state import save_sync_state
            from ..utils.app_paths import user_profile_path
            import json

            writer = FirebaseWorkspaceWriter(session_store=self._session_store)

            try:
                income = list(self._provider.list_categories_for_type(True))
            except Exception:
                income = []
            try:
                outcome = list(self._provider.list_categories_for_type(False))
            except Exception:
                outcome = []
            try:
                writer.upsert_categories(income=income, outcome=outcome)
                pushed += 1
            except Exception:
                pass

            del_mov = list(getattr(state, "pending_delete_movement_ids", []) or [])
            kept_mov: list[str] = []
            for mid in del_mov:
                try:
                    writer.delete_movement(movement_id=str(mid))
                    pushed += 1
                except Exception:
                    kept_mov.append(str(mid))
            state.pending_delete_movement_ids = kept_mov

            del_evt = list(getattr(state, "pending_delete_event_ids", []) or [])
            kept_evt: list[str] = []
            for eid in del_evt:
                try:
                    writer.delete_event(event_id=str(eid))
                    pushed += 1
                except Exception:
                    kept_evt.append(str(eid))
            state.pending_delete_event_ids = kept_evt

            del_pl = list(
                getattr(state, "pending_delete_installment_plan_ids", []) or []
            )
            kept_pl: list[str] = []
            for pid in del_pl:
                try:
                    writer.delete_installment_plan(plan_id=str(pid))
                    pushed += 1
                except Exception:
                    kept_pl.append(str(pid))
            state.pending_delete_installment_plan_ids = kept_pl

            try:
                movements = list(self._provider.list_movements())
            except Exception:
                movements = []
            if movements:
                try:
                    pushed += int(writer.upsert_movements_bulk(movements))
                except Exception:
                    for m in movements:
                        try:
                            writer.upsert_movement(m)
                            pushed += 1
                        except Exception:
                            continue

            acc_svc = AccountsService(JsonFileAccountsProvider())
            accounts = acc_svc.load_accounts()
            # Guard: never push an empty accounts list – that would overwrite
            # the remote workspace's account metadata with nothing, which can
            # happen right after a user-switch before the pull has completed.
            if accounts:
                try:
                    writer.upsert_accounts_snapshot(accounts)
                    pushed += 1
                except Exception:
                    pass

            for e in list(JsonFileOneTimeEventProvider().list_events()):
                try:
                    writer.upsert_event(e)
                    pushed += 1
                except Exception:
                    continue

            for p in list(JsonFileInstallmentPlanProvider().list_plans()):
                try:
                    writer.upsert_installment_plan(p)
                    pushed += 1
                except Exception:
                    continue

            prov = JsonFileNotificationsProvider()
            try:
                rules = [
                    {
                        "id": r.id,
                        "type": str(getattr(r.type, "value", r.type)),
                        "enabled": bool(getattr(r, "enabled", True)),
                        "schedule": str(getattr(r, "schedule", "daily") or "daily"),
                        "params": dict(getattr(r, "params", {}) or {}),
                    }
                    for r in prov.list_rules()
                ]
                writer.upsert_notifications_meta(enabled=prov.is_enabled(), rules=rules)
                pushed += 1
            except Exception:
                pass
            try:
                for n in list(prov.list_notifications()):
                    try:
                        writer.upsert_notification(n)
                        pushed += 1
                    except Exception:
                        continue
            except Exception:
                pass

            try:
                hist = JsonFileActionHistoryProvider().list_history()
            except Exception:
                hist = []
            logged = set(getattr(state, "logged_action_ids", []) or [])
            new_logged: list[str] = list(getattr(state, "logged_action_ids", []) or [])
            for entry in hist:
                try:
                    eid = str(getattr(entry, "id", "") or "").strip()
                except Exception:
                    continue
                if not eid or eid in logged:
                    continue
                try:
                    writer.upsert_action_history(entry)
                    pushed += 1
                    new_logged.append(eid)
                    logged.add(eid)
                except Exception:
                    continue
            state.logged_action_ids = new_logged

            try:
                path = user_profile_path()
                if path.exists():
                    raw = json.loads(path.read_text(encoding="utf-8") or "{}")
                else:
                    raw = {}
                if isinstance(raw, dict):
                    full_name = str(raw.get("full_name", "") or "")
                    lock_enabled = bool(raw.get("lock_enabled", False))
                    writer.upsert_user_profile(
                        uid=str(uid), full_name=full_name, lock_enabled=lock_enabled
                    )
                    pushed += 1
            except Exception:
                pass

            try:
                save_sync_state(str(wid or uid), state)
            except Exception:
                pass
        except Exception:
            return pushed
        return pushed

    def _push_dashboard_meta(self) -> None:
        try:
            from ..models.dashboard_meta_service import DashboardMetaService
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter
            from ..models.user_grade_service import UserGradeService

            meta = DashboardMetaService(
                accounts_provider=self._accounts_provider,
                movement_provider=self._provider,
            ).compute()
            writer = FirebaseWorkspaceWriter()
            writer.upsert_dashboard_meta(meta)
            try:
                grade = UserGradeService(movement_provider=self._provider).compute()
                writer.upsert_workspace_grade(grade)
            except Exception:
                pass
        except Exception:
            return
