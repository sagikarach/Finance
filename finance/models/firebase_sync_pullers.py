from __future__ import annotations

from typing import Dict, List, Tuple

from .bank_movement import BankMovement, deserialize_bank_movement
from .firebase_client import FirestoreClient
from ..utils.safe import PARSE_ERRORS, swallow
from ..utils.logging_setup import get_logger
_log = get_logger("models")


def pull_remote_movements(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    uid: str,
    id_token: str,
    updated_after: str = "",
    updated_after_ms: int = 0,
) -> Tuple[List[str], Dict[str, dict]]:
    if workspace_id:
        updated_after = str(updated_after or "").strip()
        try:
            updated_after_ms = int(updated_after_ms or 0)
        except PARSE_ERRORS:
            updated_after_ms = 0
        docs = None
        if updated_after_ms > 0:
            try:
                docs = fs.query_workspace_movements_updated_after_ms(
                    workspace_id=workspace_id,
                    id_token=id_token,
                    updated_after_ms=updated_after_ms,
                    limit=1000,
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug("pull_remote_movements: %s", exc)
                docs = None
        elif updated_after:
            try:
                docs = fs.query_workspace_movements_updated_after(
                    workspace_id=workspace_id,
                    id_token=id_token,
                    updated_after=updated_after,
                )
            except Exception as exc:  # noqa: BLE001
                _log.debug("pull_remote_movements: %s", exc)
                docs = None
        if docs is None:
            docs = fs.list_workspace_movements(
                workspace_id=workspace_id, id_token=id_token
            )
    else:
        docs = fs.list_user_movements(uid=uid, id_token=id_token)

    remote_ids: List[str] = []
    remote_by_id: Dict[str, dict] = {}
    for d in docs:
        mid, fields = fs.parse_doc(d)
        if not mid:
            continue
        remote_ids.append(mid)
        remote_by_id[mid] = fields
    return remote_ids, remote_by_id


def merge_remote_into_local(
    *,
    remote_by_id: Dict[str, dict],
    local_by_id: Dict[str, BankMovement],
) -> int:
    pulled = 0
    for mid, f in remote_by_id.items():
        with swallow(msg="merge_remote_into_local"):
            if bool(f.get("deleted", False)):
                if mid in local_by_id:
                    local_by_id.pop(mid, None)
                    pulled += 1
                continue

            mv = deserialize_bank_movement(f, movement_id=mid)
            if mv is None:
                continue
            local_by_id[mid] = mv
            pulled += 1
    return pulled
