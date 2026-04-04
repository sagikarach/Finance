from __future__ import annotations

from typing import Dict, Optional, Protocol

from .firebase_client import FirestoreClient
from .action_history import ActionHistory
from .action_history import Action


class ActionHistoryProviderProto(Protocol):
    def list_history(self) -> list[ActionHistory]: ...

    def save_history(self, entries: list[ActionHistory]) -> None: ...

    def _deserialize_action(self, action_data: dict) -> Action | None: ...


def pull_action_history_to_local_cache(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    id_token: str,
    history_provider: Optional[ActionHistoryProviderProto] = None,
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return

    try:
        from ..data.action_history_provider import JsonFileActionHistoryProvider

        docs_actions = fs.list_collection(
            collection_path=f"workspaces/{workspace_id}/actions",
            id_token=id_token,
        )
        provider = history_provider or JsonFileActionHistoryProvider()
        local_hist = provider.list_history()
        by_id: Dict[str, ActionHistory] = {h.id: h for h in local_hist}

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
                action_obj = provider._deserialize_action(action_data)
                if action_obj is None:
                    continue
                by_id[hid] = ActionHistory(id=hid, timestamp=ts, action=action_obj)
            except Exception:
                continue

        # Ensure stable ordering so "latest N" UI shows the newest actions reliably.
        entries = list(by_id.values())
        try:
            entries.sort(key=lambda h: (str(h.timestamp or ""), str(h.id or "")))
        except Exception:
            pass
        provider.save_history(entries)
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning(
            "pull_action_history_to_local_cache failed: %s", _e
        )
