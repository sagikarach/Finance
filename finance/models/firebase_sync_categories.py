from __future__ import annotations

from typing import List

from .firebase_client import FirestoreClient
from ..utils.safe import PARSE_ERRORS, swallow
from ..utils.logging_setup import get_logger
_log = get_logger("models")


def sync_categories(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    uid: str,
    id_token: str,
    provider,
    allow_push: bool,
) -> None:
    workspace_id = (workspace_id or "").strip()
    if workspace_id:
        doc_path = f"workspaces/{workspace_id}/meta/categories"
    else:
        doc_path = f"users/{uid}/meta/categories"

    remote_income: List[str] = []
    remote_outcome: List[str] = []
    try:
        doc = fs.get_document(document_path=doc_path, id_token=id_token)
        _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
        ri = parsed.get("income", [])
        ro = parsed.get("outcome", [])
        if isinstance(ri, list):
            remote_income = [
                str(x).strip() for x in ri if isinstance(x, str) and str(x).strip()
            ]
        if isinstance(ro, list):
            remote_outcome = [
                str(x).strip() for x in ro if isinstance(x, str) and str(x).strip()
            ]
    except Exception as exc:  # noqa: BLE001
        _log.debug("sync_categories: %s", exc)
        remote_income = []
        remote_outcome = []

    try:
        local_income = list(provider.list_categories_for_type(True))
    except PARSE_ERRORS:
        local_income = []
    try:
        local_outcome = list(provider.list_categories_for_type(False))
    except PARSE_ERRORS:
        local_outcome = []

    merged_income = sorted({*(remote_income), *(local_income)})
    merged_outcome = sorted({*(remote_outcome), *(local_outcome)})

    if allow_push:
        fs.upsert_document(
            document_path=doc_path,
            id_token=id_token,
            fields={"income": merged_income, "outcome": merged_outcome, "version": 1},
        )

    with swallow(msg="sync_categories"):
        for c in merged_income:
            provider.add_category_for_type(c, True)
        for c in merged_outcome:
            provider.add_category_for_type(c, False)
