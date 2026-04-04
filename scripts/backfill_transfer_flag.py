from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _as_str(v: Any) -> str:
    return str(v or "").strip()


def _should_mark_transfer(fields: Dict[str, Any]) -> bool:
    if fields.get("is_transfer") is True:
        return False
    cat = _as_str(fields.get("category"))
    return cat == "העברה"


def main() -> int:
    from finance.models.firebase_client import FirestoreClient
    from finance.models.firebase_session import FirebaseSessionStore
    from finance.models.firebase_session_manager import FirebaseSessionManager

    p = argparse.ArgumentParser()
    p.add_argument(
        "--workspace-id",
        type=str,
        default="",
        help="Workspace ID to migrate. If omitted, uses the currently logged-in session workspace.",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Only print what would change."
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on how many docs to update (0 = no limit).",
    )
    args = p.parse_args()

    store = FirebaseSessionStore()
    session = FirebaseSessionManager(store=store).get_valid_session()
    wid = _as_str(args.workspace_id) or _as_str(getattr(session, "workspace_id", ""))
    if not wid:
        raise SystemExit("Workspace not set")

    fs = FirestoreClient(project_id=session.project_id)
    docs = fs.list_workspace_movements(workspace_id=wid, id_token=session.id_token)

    to_update: List[Tuple[str, Dict[str, Any]]] = []
    for d in docs:
        mid, fields = fs.parse_doc(d)
        if not mid or not isinstance(fields, dict):
            continue
        if _should_mark_transfer(fields):
            to_update.append((mid, fields))

    if args.limit and args.limit > 0:
        to_update = to_update[: int(args.limit)]

    print(f"Workspace: {wid}")
    print(f"Movements scanned: {len(docs)}")
    print(f"Transfers to backfill: {len(to_update)}")

    if args.dry_run:
        for mid, f in to_update[:20]:
            print(
                f"- would set is_transfer=true on {mid} (category={_as_str(f.get('category'))})"
            )
        if len(to_update) > 20:
            print(f"... and {len(to_update) - 20} more")
        return 0

    updated = 0
    for mid, _ in to_update:
        try:
            fs.upsert_document(
                document_path=f"workspaces/{wid}/movements/{mid}",
                id_token=session.id_token,
                fields={"id": mid, "is_transfer": True},
            )
            updated += 1
        except Exception as e:
            print(f"Failed updating {mid}: {e}")
            continue

    print(f"Updated: {updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
