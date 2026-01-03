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

    def to_dict(self) -> dict:
        return {
            "remote_ids": list(self.remote_ids),
            "applied_balance_ids": list(self.applied_balance_ids),
            "logged_action_ids": list(self.logged_action_ids),
        }

    @staticmethod
    def from_dict(d: object) -> "SyncState":
        if not isinstance(d, dict):
            return SyncState(
                remote_ids=[], applied_balance_ids=[], logged_action_ids=[]
            )
        raw = d.get("remote_ids", [])
        if not isinstance(raw, list):
            raw = []
        ids = [str(x) for x in raw if isinstance(x, str) and x.strip()]

        raw_applied = d.get("applied_balance_ids", [])
        if not isinstance(raw_applied, list):
            raw_applied = []
        applied = [str(x) for x in raw_applied if isinstance(x, str) and str(x).strip()]

        raw_logged = d.get("logged_action_ids", [])
        if not isinstance(raw_logged, list):
            raw_logged = []
        logged = [str(x) for x in raw_logged if isinstance(x, str) and str(x).strip()]

        return SyncState(
            remote_ids=ids,
            applied_balance_ids=applied,
            logged_action_ids=logged,
        )


def load_sync_state(key: str) -> SyncState:
    path = sync_state_path(key)
    if not path.exists():
        return SyncState(remote_ids=[], applied_balance_ids=[], logged_action_ids=[])
    try:
        raw = json.loads(path.read_text(encoding="utf-8") or "{}")
        return SyncState.from_dict(raw)
    except Exception:
        return SyncState(remote_ids=[], applied_balance_ids=[], logged_action_ids=[])


def save_sync_state(key: str, state: SyncState) -> None:
    try:
        sync_state_path(key).write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
