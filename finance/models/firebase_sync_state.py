from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import json

from ..utils.app_paths import app_data_dir


def sync_state_path(key: str) -> Path:
    p = app_data_dir() / "firebase"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"sync_state_{key}.json"


@dataclass
class SyncState:
    remote_ids: List[str]
    applied_balance_ids: List[str]
    logged_action_ids: List[str]
    pending_delete_movement_ids: List[str]
    pending_delete_event_ids: List[str]
    pending_delete_installment_plan_ids: List[str]
    last_remote_updated_at: str
    last_remote_updated_at_ms: int
    last_workspace_cache_pull_at_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "remote_ids": list(self.remote_ids),
            "applied_balance_ids": list(self.applied_balance_ids),
            "logged_action_ids": list(self.logged_action_ids),
            "pending_delete_movement_ids": list(self.pending_delete_movement_ids),
            "pending_delete_event_ids": list(self.pending_delete_event_ids),
            "pending_delete_installment_plan_ids": list(
                self.pending_delete_installment_plan_ids
            ),
            "last_remote_updated_at": str(self.last_remote_updated_at or ""),
            "last_remote_updated_at_ms": int(self.last_remote_updated_at_ms or 0),
            "last_workspace_cache_pull_at_ms": int(
                self.last_workspace_cache_pull_at_ms or 0
            ),
        }

    @staticmethod
    def from_dict(d: object) -> "SyncState":
        if not isinstance(d, dict):
            return SyncState(
                remote_ids=[],
                applied_balance_ids=[],
                logged_action_ids=[],
                pending_delete_movement_ids=[],
                pending_delete_event_ids=[],
                pending_delete_installment_plan_ids=[],
                last_remote_updated_at="",
                last_remote_updated_at_ms=0,
                last_workspace_cache_pull_at_ms=0,
            )
        raw = d.get("remote_ids", [])
        if not isinstance(raw, list):
            raw = []
        ids = [str(x).strip() for x in raw if x is not None and str(x).strip()]

        raw_applied = d.get("applied_balance_ids", [])
        if not isinstance(raw_applied, list):
            raw_applied = []
        applied = [str(x).strip() for x in raw_applied if x is not None and str(x).strip()]

        raw_logged = d.get("logged_action_ids", [])
        if not isinstance(raw_logged, list):
            raw_logged = []
        logged = [str(x) for x in raw_logged if isinstance(x, str) and str(x).strip()]

        raw_del_mov = d.get("pending_delete_movement_ids", [])
        if not isinstance(raw_del_mov, list):
            raw_del_mov = []
        del_mov = [str(x) for x in raw_del_mov if isinstance(x, str) and str(x).strip()]

        raw_del_evt = d.get("pending_delete_event_ids", [])
        if not isinstance(raw_del_evt, list):
            raw_del_evt = []
        del_evt = [str(x) for x in raw_del_evt if isinstance(x, str) and str(x).strip()]

        raw_del_pl = d.get("pending_delete_installment_plan_ids", [])
        if not isinstance(raw_del_pl, list):
            raw_del_pl = []
        del_pl = [str(x) for x in raw_del_pl if isinstance(x, str) and str(x).strip()]

        last_remote_updated_at = str(d.get("last_remote_updated_at", "") or "").strip()
        try:
            last_remote_updated_at_ms = int(d.get("last_remote_updated_at_ms", 0) or 0)
        except Exception:
            last_remote_updated_at_ms = 0
        try:
            last_workspace_cache_pull_at_ms = int(
                d.get("last_workspace_cache_pull_at_ms", 0) or 0
            )
        except Exception:
            last_workspace_cache_pull_at_ms = 0
        return SyncState(
            remote_ids=ids,
            applied_balance_ids=applied,
            logged_action_ids=logged,
            pending_delete_movement_ids=del_mov,
            pending_delete_event_ids=del_evt,
            pending_delete_installment_plan_ids=del_pl,
            last_remote_updated_at=last_remote_updated_at,
            last_remote_updated_at_ms=last_remote_updated_at_ms,
            last_workspace_cache_pull_at_ms=last_workspace_cache_pull_at_ms,
        )


def load_sync_state(key: str) -> SyncState:
    path = sync_state_path(key)
    if not path.exists():
        return SyncState(
            remote_ids=[],
            applied_balance_ids=[],
            logged_action_ids=[],
            pending_delete_movement_ids=[],
            pending_delete_event_ids=[],
            pending_delete_installment_plan_ids=[],
            last_remote_updated_at="",
            last_remote_updated_at_ms=0,
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        return SyncState.from_dict(raw)
    except Exception:
        return SyncState(
            remote_ids=[],
            applied_balance_ids=[],
            logged_action_ids=[],
            pending_delete_movement_ids=[],
            pending_delete_event_ids=[],
            pending_delete_installment_plan_ids=[],
            last_remote_updated_at="",
            last_remote_updated_at_ms=0,
        )


def _uniq(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in list(items or []):
        x = str(x or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def add_pending_delete(*, key: str, kind: str, item_id: str) -> None:
    """
    Record a delete to be pushed on next Sync.
    kind: movement | event | installment_plan
    """
    key = str(key or "").strip()
    item_id = str(item_id or "").strip()
    kind = str(kind or "").strip().lower()
    if not key or not item_id:
        return
    try:
        state = load_sync_state(key)
        if kind == "movement":
            state.pending_delete_movement_ids = _uniq(
                list(getattr(state, "pending_delete_movement_ids", []) or [])
                + [item_id]
            )
        elif kind == "event":
            state.pending_delete_event_ids = _uniq(
                list(getattr(state, "pending_delete_event_ids", []) or []) + [item_id]
            )
        elif kind in ("installment", "installment_plan", "plan"):
            state.pending_delete_installment_plan_ids = _uniq(
                list(getattr(state, "pending_delete_installment_plan_ids", []) or [])
                + [item_id]
            )
        save_sync_state(key, state)
    except Exception:
        return


def save_sync_state(key: str, state: SyncState) -> None:
    try:
        sync_state_path(key).write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
