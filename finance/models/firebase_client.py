from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
import time
import urllib.parse
import urllib.request
import urllib.error


@dataclass(frozen=True)
class FirebaseAuthResult:
    uid: str
    id_token: str
    refresh_token: str
    expires_in: int


def _http_json(
    *,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    timeout: float = 10.0,
) -> Any:
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("User-Agent", "Finance")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""

        try:
            data = json.loads(raw) if raw else None
        except Exception:
            data = None

        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                status = str(err.get("status", "") or "").strip()
                msg = str(err.get("message", "") or "").strip()
                if status and msg:
                    raise RuntimeError(f"{status}: {msg}")
                if msg:
                    raise RuntimeError(msg)

        if raw:
            raise RuntimeError(raw)
        code = getattr(e, "code", "")
        reason = getattr(e, "reason", "") or ""
        raise RuntimeError(f"HTTP {code} {reason}".strip())
    except Exception as e:
        raise RuntimeError(str(e))
    try:
        return json.loads(raw)
    except Exception:
        raise RuntimeError("Invalid JSON response")


class FirebaseAuthClient:
    def __init__(self, *, api_key: str) -> None:
        self._api_key = api_key.strip()

    def sign_in_with_password(self, *, email: str, password: str) -> FirebaseAuthResult:
        url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
            f"?key={urllib.parse.quote(self._api_key)}"
        )
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        data = json.dumps(payload).encode("utf-8")
        resp = _http_json(
            method="POST",
            url=url,
            headers={"Content-Type": "application/json"},
            body=data,
        )
        if not isinstance(resp, dict):
            raise RuntimeError("Invalid auth response")
        uid = str(resp.get("localId", "") or "")
        id_token = str(resp.get("idToken", "") or "")
        refresh_token = str(resp.get("refreshToken", "") or "")
        expires_in = int(float(resp.get("expiresIn", 0) or 0))
        if not uid or not id_token or not refresh_token:
            msg = str(resp.get("error", "") or "Login failed")
            raise RuntimeError(msg)
        return FirebaseAuthResult(
            uid=uid,
            id_token=id_token,
            refresh_token=refresh_token,
            expires_in=expires_in if expires_in > 0 else 3600,
        )

    def refresh_id_token(self, *, refresh_token: str) -> Tuple[str, str, int]:
        url = (
            "https://securetoken.googleapis.com/v1/token"
            f"?key={urllib.parse.quote(self._api_key)}"
        )
        form = urllib.parse.urlencode(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        ).encode("utf-8")
        resp = _http_json(
            method="POST",
            url=url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=form,
        )
        if not isinstance(resp, dict):
            raise RuntimeError("Invalid refresh response")
        id_token = str(resp.get("access_token", "") or "")
        new_refresh = str(resp.get("refresh_token", "") or refresh_token)
        expires_in = int(float(resp.get("expires_in", 0) or 0))
        if not id_token:
            raise RuntimeError("Refresh failed")
        return id_token, new_refresh, expires_in if expires_in > 0 else 3600


def _fs_value(value: Any) -> Dict[str, Any]:
    if value is None:
        return {"nullValue": None}
    if isinstance(value, dict):
        fields: Dict[str, Any] = {}
        for k, v in value.items():
            fields[str(k)] = _fs_value(v)
        return {"mapValue": {"fields": fields}}
    if isinstance(value, (list, tuple)):
        values: List[Dict[str, Any]] = []
        for item in value:
            values.append(_fs_value(item))
        return {"arrayValue": {"values": values}}
    if isinstance(value, bool):
        return {"booleanValue": bool(value)}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"integerValue": str(int(value))}
    if isinstance(value, float):
        return {"doubleValue": float(value)}
    return {"stringValue": str(value)}


def _fs_any(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return None
    if "nullValue" in raw:
        return None
    if "stringValue" in raw:
        return str(raw.get("stringValue", "") or "")
    if "doubleValue" in raw:
        try:
            return float(raw.get("doubleValue", 0.0) or 0.0)
        except Exception:
            return 0.0
    if "integerValue" in raw:
        try:
            return int(str(raw.get("integerValue", "0") or "0"))
        except Exception:
            return 0
    if "booleanValue" in raw:
        return bool(raw.get("booleanValue", False))
    if "timestampValue" in raw:
        return str(raw.get("timestampValue", "") or "")
    if "mapValue" in raw and isinstance(raw.get("mapValue"), dict):
        mv = raw.get("mapValue") or {}
        f = mv.get("fields", {})
        if not isinstance(f, dict):
            return {}
        return {k: _fs_any(v) for k, v in f.items()}
    if "arrayValue" in raw and isinstance(raw.get("arrayValue"), dict):
        av = raw.get("arrayValue") or {}
        vals = av.get("values", [])
        if not isinstance(vals, list):
            return []
        return [_fs_any(v) for v in vals if isinstance(v, dict)]
    return None


def _fs_get(fields: Dict[str, Any], key: str) -> Any:
    raw = fields.get(key)
    if not isinstance(raw, dict):
        return None
    if "stringValue" in raw:
        return str(raw.get("stringValue", "") or "")
    if "doubleValue" in raw:
        try:
            return float(raw.get("doubleValue", 0.0) or 0.0)
        except Exception:
            return 0.0
    if "integerValue" in raw:
        try:
            return int(str(raw.get("integerValue", "0") or "0"))
        except Exception:
            return 0
    if "booleanValue" in raw:
        return bool(raw.get("booleanValue", False))
    if "timestampValue" in raw:
        return str(raw.get("timestampValue", "") or "")
    return None


class FirestoreClient:
    def __init__(self, *, project_id: str) -> None:
        self._project_id = project_id.strip()

    def _doc_base(self) -> str:
        return f"https://firestore.googleapis.com/v1/projects/{self._project_id}/databases/(default)/documents"

    def list_user_movements(
        self, *, uid: str, id_token: str, page_size: int = 1000
    ) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        token: Optional[str] = None
        while True:
            params = {"pageSize": str(int(page_size))}
            if token:
                params["pageToken"] = token
            url = f"{self._doc_base()}/users/{uid}/movements?{urllib.parse.urlencode(params)}"
            resp = _http_json(
                method="GET",
                url=url,
                headers={"Authorization": f"Bearer {id_token}"},
            )
            if not isinstance(resp, dict):
                break
            batch = resp.get("documents", [])
            if isinstance(batch, list):
                for d in batch:
                    if isinstance(d, dict):
                        docs.append(d)
            token = str(resp.get("nextPageToken", "") or "").strip() or None
            if not token:
                break
        return docs

    def list_workspace_movements(
        self, *, workspace_id: str, id_token: str, page_size: int = 1000
    ) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        token: Optional[str] = None
        workspace_id = workspace_id.strip()
        if not workspace_id:
            return docs
        while True:
            params = {"pageSize": str(int(page_size))}
            if token:
                params["pageToken"] = token
            url = (
                f"{self._doc_base()}/workspaces/{workspace_id}/movements?"
                f"{urllib.parse.urlencode(params)}"
            )
            resp = _http_json(
                method="GET",
                url=url,
                headers={"Authorization": f"Bearer {id_token}"},
            )
            if not isinstance(resp, dict):
                break
            batch = resp.get("documents", [])
            if isinstance(batch, list):
                for d in batch:
                    if isinstance(d, dict):
                        docs.append(d)
            token = str(resp.get("nextPageToken", "") or "").strip() or None
            if not token:
                break
        return docs

    def list_collection(
        self, *, collection_path: str, id_token: str, page_size: int = 1000
    ) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        token: Optional[str] = None
        collection_path = collection_path.strip().strip("/")
        if not collection_path:
            return docs
        while True:
            params = {"pageSize": str(int(page_size))}
            if token:
                params["pageToken"] = token
            url = (
                f"{self._doc_base()}/{collection_path}?{urllib.parse.urlencode(params)}"
            )
            resp = _http_json(
                method="GET",
                url=url,
                headers={"Authorization": f"Bearer {id_token}"},
            )
            if not isinstance(resp, dict):
                break
            batch = resp.get("documents", [])
            if isinstance(batch, list):
                for d in batch:
                    if isinstance(d, dict):
                        docs.append(d)
            token = str(resp.get("nextPageToken", "") or "").strip() or None
            if not token:
                break
        return docs

    def query_workspace_movements_updated_after(
        self, *, workspace_id: str, id_token: str, updated_after: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Incremental movements pull using Firestore structured query (runQuery).
        Returns a list of document objects (same shape as list_collection).

        Note: This is best-effort. If query fails, caller should fall back to full list.
        """
        workspace_id = str(workspace_id or "").strip()
        updated_after = str(updated_after or "").strip()
        if not workspace_id or not updated_after:
            return []
        parent = f"workspaces/{workspace_id}"
        url = f"{self._doc_base()}/{parent}:runQuery"

        query = {
            "structuredQuery": {
                "from": [{"collectionId": "movements"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "updated_at"},
                        "op": "GREATER_THAN",
                        "value": {"stringValue": updated_after},
                    }
                },
                "orderBy": [
                    {"field": {"fieldPath": "updated_at"}, "direction": "ASCENDING"}
                ],
                "limit": int(limit) if int(limit) > 0 else 1000,
            }
        }

        resp = _http_json(
            method="POST",
            url=url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps(query).encode("utf-8"),
        )
        if not isinstance(resp, list):
            return []
        docs: List[Dict[str, Any]] = []
        for row in resp:
            if not isinstance(row, dict):
                continue
            doc = row.get("document")
            if isinstance(doc, dict):
                docs.append(doc)
        return docs

    def query_workspace_movements_updated_after_ms(
        self,
        *,
        workspace_id: str,
        id_token: str,
        updated_after_ms: int,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Incremental movements pull using updated_at_ms (int) via Firestore structured query (runQuery).
        """
        workspace_id = str(workspace_id or "").strip()
        try:
            updated_after_ms = int(updated_after_ms or 0)
        except Exception:
            updated_after_ms = 0
        if not workspace_id or updated_after_ms <= 0:
            return []
        parent = f"workspaces/{workspace_id}"
        url = f"{self._doc_base()}/{parent}:runQuery"

        query = {
            "structuredQuery": {
                "from": [{"collectionId": "movements"}],
                "where": {
                    "fieldFilter": {
                        "field": {"fieldPath": "updated_at_ms"},
                        "op": "GREATER_THAN",
                        "value": {"integerValue": str(int(updated_after_ms))},
                    }
                },
                "orderBy": [
                    {"field": {"fieldPath": "updated_at_ms"}, "direction": "ASCENDING"}
                ],
                "limit": int(limit) if int(limit) > 0 else 1000,
            }
        }

        resp = _http_json(
            method="POST",
            url=url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps(query).encode("utf-8"),
        )
        if not isinstance(resp, list):
            return []
        docs: List[Dict[str, Any]] = []
        for row in resp:
            if not isinstance(row, dict):
                continue
            doc = row.get("document")
            if isinstance(doc, dict):
                docs.append(doc)
        return docs

    def upsert_user_movement(
        self,
        *,
        uid: str,
        movement_id: str,
        id_token: str,
        fields: Dict[str, Any],
    ) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        now_ms = int(time.time() * 1000)
        body_fields = dict(fields)
        body_fields.setdefault("id", movement_id)
        body_fields.setdefault("created_at", now)
        body_fields.setdefault("created_at_ms", now_ms)
        body_fields["updated_at"] = now
        body_fields["updated_at_ms"] = now_ms
        doc = {"fields": {k: _fs_value(v) for k, v in body_fields.items()}}

        url = f"{self._doc_base()}/users/{uid}/movements/{movement_id}"
        _http_json(
            method="PATCH",
            url=url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps(doc).encode("utf-8"),
        )

    def get_document(self, *, document_path: str, id_token: str) -> Dict[str, Any]:
        url = f"{self._doc_base()}/{document_path.lstrip('/')}"
        resp = _http_json(
            method="GET",
            url=url,
            headers={"Authorization": f"Bearer {id_token}"},
        )
        if not isinstance(resp, dict):
            return {}
        return resp

    def upsert_document(
        self,
        *,
        document_path: str,
        id_token: str,
        fields: Dict[str, Any],
    ) -> None:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        now_ms = int(time.time() * 1000)
        body_fields = dict(fields)
        body_fields["updated_at"] = now
        body_fields["updated_at_ms"] = now_ms
        doc = {"fields": {k: _fs_value(v) for k, v in body_fields.items()}}
        url = f"{self._doc_base()}/{document_path.lstrip('/')}"
        _http_json(
            method="PATCH",
            url=url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps(doc).encode("utf-8"),
        )

    def commit_writes(self, *, id_token: str, writes: List[Dict[str, Any]]) -> None:
        """
        Batch write via Firestore commit endpoint to reduce round-trips.
        """
        safe_writes = [w for w in list(writes or []) if isinstance(w, dict)]
        if not safe_writes:
            return
        url = f"{self._doc_base()}:commit"
        _http_json(
            method="POST",
            url=url,
            headers={
                "Authorization": f"Bearer {id_token}",
                "Content-Type": "application/json",
            },
            body=json.dumps({"writes": safe_writes}).encode("utf-8"),
        )

    @staticmethod
    def parse_any_doc(doc: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        name = str(doc.get("name", "") or "")
        doc_id = name.split("/")[-1] if name else ""
        fields = doc.get("fields", {})
        if not isinstance(fields, dict):
            fields = {}
        out: Dict[str, Any] = {}
        for k, raw in fields.items():
            out[k] = _fs_any(raw)
        return doc_id, out

    @staticmethod
    def parse_doc(doc: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        name = str(doc.get("name", "") or "")
        movement_id = name.split("/")[-1] if name else ""
        fields = doc.get("fields", {})
        if not isinstance(fields, dict):
            fields = {}
        out: Dict[str, Any] = {}
        for k in (
            "id",
            "amount",
            "date",
            "account_name",
            "category",
            "type",
            "description",
            "event_id",
            "is_transfer",
            "deleted",
            "created_at",
            "created_at_ms",
            "updated_at",
            "updated_at_ms",
        ):
            out[k] = _fs_get(fields, k)
        if not out.get("id") and movement_id:
            out["id"] = movement_id
        return movement_id or str(out.get("id", "") or ""), out
