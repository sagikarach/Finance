"""Workspace membership — who may read/write ``workspaces/{wid}``.

A workspace is shared by every Firebase account listed under
``workspaces/{wid}/members/{uid}`` (the same schema the mobile app writes).
``firestore.rules`` lets only members touch a workspace's data, so the desktop
must make sure the logged-in account is a member before it syncs.

Joining works like the mobile "join by code": knowing the workspace id is what
lets an account add itself. Workspace ids are random 12-character codes, so
treat one like a password and only share it with people who should see the data.
"""

from __future__ import annotations

import threading
import time
from typing import Set, Tuple

from .firebase_client import FirestoreClient
from ..utils.logging_setup import get_logger

_log = get_logger("models")

_VERIFIED: Set[Tuple[str, str, str]] = set()
_VERIFIED_LOCK = threading.Lock()


def _is_not_found(exc: BaseException) -> bool:
    msg = str(exc or "")
    return "NOT_FOUND" in msg or "HTTP 404" in msg


def _exists(fs: FirestoreClient, *, document_path: str, id_token: str) -> bool:
    try:
        doc = fs.get_document(document_path=document_path, id_token=id_token)
    except RuntimeError as exc:
        if _is_not_found(exc):
            return False
        raise
    return bool(isinstance(doc, dict) and doc.get("name"))


def ensure_workspace_membership(
    *, fs: FirestoreClient, project_id: str, workspace_id: str, uid: str, id_token: str
) -> None:
    """Make ``uid`` a member of ``workspace_id`` (creating the workspace with
    ``uid`` as owner when it doesn't exist yet). Cached per process, so it costs
    at most two reads per (account, workspace). Raises ``RuntimeError`` when the
    server refuses (e.g. ``PERMISSION_DENIED``)."""
    wid = str(workspace_id or "").strip()
    uid = str(uid or "").strip()
    if not wid or not uid:
        return
    cache_key = (str(project_id or ""), uid, wid)
    with _VERIFIED_LOCK:
        if cache_key in _VERIFIED:
            return

    member_path = f"workspaces/{wid}/members/{uid}"
    if not _exists(fs, document_path=member_path, id_token=id_token):
        ws_exists = _exists(fs, document_path=f"workspaces/{wid}", id_token=id_token)
        # Member doc first: the rules only let a member update the workspace doc.
        fs.upsert_document(
            document_path=member_path,
            id_token=id_token,
            fields={
                "role": "editor" if ws_exists else "owner",
                "joined_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
        if not ws_exists:
            fs.upsert_document(
                document_path=f"workspaces/{wid}",
                id_token=id_token,
                fields={"version": 1, "created_by": uid},
            )
        _log.info("joined workspace %s as %s", wid, "editor" if ws_exists else "owner")

    with _VERIFIED_LOCK:
        _VERIFIED.add(cache_key)


# ---- onboarding: create / join / remember the active workspace --------------

_CODE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_workspace_code() -> str:
    """A random share code like ``AB12-CD34-EF56`` (same format as mobile)."""
    import secrets

    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(12))
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def normalize_workspace_code(code: str) -> str:
    return str(code or "").strip().upper()


def workspace_exists(fs: FirestoreClient, *, workspace_id: str, id_token: str) -> bool:
    return _exists(fs, document_path=f"workspaces/{workspace_id}", id_token=id_token)


def create_workspace(
    *, fs: FirestoreClient, project_id: str, uid: str, id_token: str
) -> str:
    """Create a brand-new workspace owned by ``uid`` and return its share code."""
    for _ in range(5):
        wid = generate_workspace_code()
        if not workspace_exists(fs, workspace_id=wid, id_token=id_token):
            ensure_workspace_membership(
                fs=fs, project_id=project_id, workspace_id=wid, uid=uid, id_token=id_token
            )
            return wid
    raise RuntimeError("לא הצלחנו ליצור תקציב חדש, נסה שוב")


def join_workspace(
    *, fs: FirestoreClient, project_id: str, workspace_id: str, uid: str, id_token: str
) -> str:
    """Join an existing workspace by its share code. Unlike
    ``ensure_workspace_membership`` this never creates one, so a typo fails
    instead of silently starting an empty budget."""
    wid = normalize_workspace_code(workspace_id)
    if not wid:
        raise RuntimeError("חובה להזין קוד שיתוף")
    if not workspace_exists(fs, workspace_id=wid, id_token=id_token):
        raise RuntimeError("קוד השיתוף לא נמצא. בדוק שהקלדת אותו נכון.")
    ensure_workspace_membership(
        fs=fs, project_id=project_id, workspace_id=wid, uid=uid, id_token=id_token
    )
    return wid


def get_active_workspace_id(fs: FirestoreClient, *, uid: str, id_token: str) -> str:
    """The workspace this account last used (``users/{uid}.active_workspace_id``,
    shared with mobile), or ``""``."""
    try:
        doc = fs.get_document(document_path=f"users/{uid}", id_token=id_token)
    except RuntimeError as exc:
        if _is_not_found(exc):
            return ""
        raise
    try:
        _, parsed = fs.parse_any_doc(doc)
    except (KeyError, TypeError, ValueError):
        return ""
    return str(parsed.get("active_workspace_id", "") or "").strip()


def set_active_workspace_id(
    fs: FirestoreClient, *, uid: str, workspace_id: str, id_token: str
) -> None:
    fs.patch_document_fields(
        document_path=f"users/{uid}",
        id_token=id_token,
        fields={"active_workspace_id": str(workspace_id or "").strip()},
    )
