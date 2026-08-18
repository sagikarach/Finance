"""A thin Google Drive v3 client — list a folder, download files, trash a file.

Used by the Drive-inbox importer to pull bank-statement files a Gmail rule
dropped into a Drive folder, then trash each file once it's imported so the
folder stays clean and nothing is imported twice. Trash (not permanent delete)
so a bad import stays recoverable from Drive's trash for 30 days.

HTTP is injected (``transport``) so the client is unit-testable without a
network or real credentials; the default transport uses urllib + the app's
shared SSL context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
import json
import urllib.error
import urllib.parse
import urllib.request

from .firebase_client import _ssl_context
from ..utils.safe import PARSE_ERRORS

_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"

# (method, url, headers, body) -> (status_code, body_bytes)
Transport = Callable[[str, str, Dict[str, str], Optional[bytes]], Tuple[int, bytes]]


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str = ""
    modified_time: str = ""
    size: int = 0

    @property
    def suffix(self) -> str:
        """Lower-cased extension including the dot, e.g. ``.xlsx`` (``""`` if none)."""
        name = self.name or ""
        dot = name.rfind(".")
        return name[dot:].lower() if dot >= 0 else ""


class DriveError(RuntimeError):
    """A Drive API call failed (auth, network, or a non-200 response)."""


def _default_transport(
    method: str, url: str, headers: Dict[str, str], body: Optional[bytes]
) -> Tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", "Finance")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=30.0, context=_ssl_context()) as resp:
            return int(getattr(resp, "status", 200) or 200), resp.read()
    except urllib.error.HTTPError as e:
        eb = b""
        try:
            eb = e.read()
        except PARSE_ERRORS:
            eb = b""
        return int(getattr(e, "code", 0) or 0), eb
    except Exception as e:  # noqa: BLE001 - any transport error becomes a DriveError
        raise DriveError(str(e))


@dataclass
class GoogleDriveClient:
    """Read-only Drive access. ``token_provider`` returns a *fresh* OAuth access
    token on each call (the OAuth layer handles refresh)."""

    token_provider: Callable[[], str]
    transport: Transport = _default_transport

    def _headers(self) -> Dict[str, str]:
        token = str(self.token_provider() or "").strip()
        if not token:
            raise DriveError("not signed in to Google Drive")
        return {"Authorization": f"Bearer {token}"}

    def _get_json(self, url: str) -> Dict[str, Any]:
        status, body = self.transport("GET", url, self._headers(), None)
        if status != 200:
            raise DriveError(_explain(status, body))
        try:
            data = json.loads(body.decode("utf-8", errors="replace"))
        except PARSE_ERRORS:
            raise DriveError("invalid JSON from Drive")
        return data if isinstance(data, dict) else {}

    def list_folder(self, folder_id: str) -> List[DriveFile]:
        """Every non-trashed file directly inside *folder_id* (paginated)."""
        folder_id = str(folder_id or "").strip()
        if not folder_id:
            raise DriveError("no Drive folder configured")

        files: List[DriveFile] = []
        page_token: Optional[str] = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                "pageSize": "100",
                "orderBy": "modifiedTime",
            }
            if page_token:
                params["pageToken"] = page_token
            url = f"{_DRIVE_FILES}?{urllib.parse.urlencode(params)}"
            data = self._get_json(url)
            for raw in data.get("files", []) or []:
                if not isinstance(raw, dict):
                    continue
                fid = str(raw.get("id", "") or "").strip()
                name = str(raw.get("name", "") or "").strip()
                if not fid or not name:
                    continue
                try:
                    size = int(raw.get("size", 0) or 0)
                except (TypeError, ValueError):
                    size = 0
                files.append(
                    DriveFile(
                        id=fid,
                        name=name,
                        mime_type=str(raw.get("mimeType", "") or ""),
                        modified_time=str(raw.get("modifiedTime", "") or ""),
                        size=size,
                    )
                )
            page_token = str(data.get("nextPageToken", "") or "").strip() or None
            if not page_token:
                break
        return files

    def download(self, file_id: str) -> bytes:
        """Raw bytes of a binary file (``alt=media``)."""
        file_id = str(file_id or "").strip()
        if not file_id:
            raise DriveError("no file id")
        url = f"{_DRIVE_FILES}/{urllib.parse.quote(file_id)}?alt=media"
        status, body = self.transport("GET", url, self._headers(), None)
        if status != 200:
            raise DriveError(_explain(status, body))
        return body

    def trash(self, file_id: str) -> None:
        """Move a file to Drive's trash (recoverable ~30 days). Requires the
        read/write Drive scope; a no-op-safe way to 'delete' after import."""
        file_id = str(file_id or "").strip()
        if not file_id:
            raise DriveError("no file id")
        params = urllib.parse.urlencode({"fields": "id, trashed"})
        url = f"{_DRIVE_FILES}/{urllib.parse.quote(file_id)}?{params}"
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        body = json.dumps({"trashed": True}).encode("utf-8")
        status, resp = self.transport("PATCH", url, headers, body)
        if status != 200:
            raise DriveError(_explain(status, resp))


def _explain(status: int, body: bytes) -> str:
    text = ""
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                text = str(err.get("message", "") or "")
            elif isinstance(err, str):
                text = err
    except PARSE_ERRORS:
        text = ""
    if status in (401, 403):
        return text or "Google Drive access denied — sign in again"
    return text or f"Drive HTTP {status}"
