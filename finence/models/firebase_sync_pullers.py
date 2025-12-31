from __future__ import annotations

from typing import Dict, List, Tuple

from .bank_movement import BankMovement, MovementType
from .firebase_client import FirestoreClient


def parse_movement_type(raw: str) -> MovementType:
    raw = (raw or "").strip()
    if raw in ("MONTHLY", "monthly"):
        return MovementType.MONTHLY
    if raw in ("YEARLY", "yearly"):
        return MovementType.YEARLY
    if raw in ("ONE_TIME", "one_time", "onetime"):
        return MovementType.ONE_TIME
    try:
        return MovementType(raw)
    except Exception:
        return MovementType.ONE_TIME


def pull_remote_movements(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    uid: str,
    id_token: str,
) -> Tuple[List[str], Dict[str, dict]]:
    if workspace_id:
        docs = fs.list_workspace_movements(workspace_id=workspace_id, id_token=id_token)
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
            movement_type = parse_movement_type(t_raw)
            is_transfer = bool(f.get("is_transfer", False))
            if not is_transfer:
                try:
                    if str(category or "").strip() == "העברה":
                        is_transfer = True
                except Exception:
                    pass
            description = f.get("description")
            desc_str = (
                str(description)
                if isinstance(description, str) and description
                else None
            )
            event_id = f.get("event_id")
            event_id_str = (
                str(event_id).strip()
                if isinstance(event_id, str) and str(event_id).strip()
                else None
            )

            if not date or not account_name:
                continue

            local_by_id[mid] = BankMovement(
                amount=amount,
                date=date,
                account_name=account_name,
                category=category,
                type=movement_type,
                is_transfer=is_transfer,
                description=desc_str,
                event_id=event_id_str,
                id=mid,
            )
            pulled += 1
        except Exception:
            continue
    return pulled
