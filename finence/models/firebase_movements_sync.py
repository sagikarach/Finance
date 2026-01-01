from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import JsonFileAccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts_service import AccountsService
from ..models.bank_movement import BankMovement
from ..models.firebase_client import FirestoreClient
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_session_manager import FirebaseSessionManager
from ..utils.app_paths import accounts_data_dir
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
    pull_ml_seed_best_effort,
)
from ..models.firebase_sync_accounts_meta import pull_accounts_meta_to_local_cache
from ..models.firebase_sync_action_history import pull_action_history_to_local_cache
from ..models.firebase_sync_balance_apply import (
    apply_movements_to_account_balances_once,
)


class FirebaseMovementsSyncService:
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
        if not src.exists():
            return
        try:
            dst.write_bytes(src.read_bytes())
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
    ) -> Tuple[int, List[str], Dict[str, dict], Dict[str, BankMovement]]:
        remote_ids, remote_by_id = pull_remote_movements(
            fs=fs, workspace_id=wid, uid=uid, id_token=id_token
        )
        local = self._provider.list_movements()
        local_by_id = {m.id: m for m in local}
        pulled = merge_remote_into_local(
            remote_by_id=remote_by_id, local_by_id=local_by_id
        )
        self._provider.save_movements(list(local_by_id.values()))
        return pulled, remote_ids, remote_by_id, local_by_id

    def _pull_workspace_caches(
        self, *, fs: FirestoreClient, wid: str, id_token: str
    ) -> None:
        if not wid:
            return
        pull_ml_seed_best_effort(workspace_id=wid)
        pull_events_to_local_cache(fs=fs, workspace_id=wid, id_token=id_token)
        pull_installment_plans_to_local_cache(
            fs=fs, workspace_id=wid, id_token=id_token
        )
        pull_notifications_to_local_cache(fs=fs, workspace_id=wid, id_token=id_token)
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
        _ = allow_push
        session = self._load_session_refresh_if_needed()
        wid = str(getattr(session, "workspace_id", "") or "").strip()
        uid = session.uid
        key = wid or uid
        self.ensure_user_local_file(key)
        state = load_sync_state(key)

        fs = FirestoreClient(project_id=session.project_id)

        self._best_effort(
            self._sync_categories_pull_only,
            fs=fs,
            wid=wid,
            uid=uid,
            id_token=session.id_token,
        )

        pulled, remote_ids, remote_by_id, local_by_id = self._pull_and_merge_movements(
            fs=fs, wid=wid, uid=uid, id_token=session.id_token
        )

        self._best_effort(
            self._pull_workspace_caches, fs=fs, wid=wid, id_token=session.id_token
        )

        self._best_effort(
            self._apply_balances_once,
            state=state,
            local_by_id=local_by_id,
            remote_by_id=remote_by_id,
        )

        pushed = 0
        remote_set = set(remote_ids)

        state.remote_ids = list(remote_set | {m.id for m in local_by_id.values()})
        self._best_effort(save_sync_state, key, state)

        return pulled, pushed
