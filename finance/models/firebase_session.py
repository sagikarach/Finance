from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json
import time

from ..utils.app_paths import app_data_dir


def _session_path() -> Path:
    p = app_data_dir() / "firebase"
    p.mkdir(parents=True, exist_ok=True)
    return p / "session.json"


@dataclass
class FirebaseSession:
    api_key: str = ""
    project_id: str = ""
    email: str = ""
    uid: str = ""
    workspace_id: str = ""
    refresh_token: str = ""
    id_token: str = ""
    expires_at: float = 0.0  # unix seconds

    @property
    def is_logged_in(self) -> bool:
        return bool(
            self.uid and self.refresh_token and self.api_key and self.project_id
        )

    def is_id_token_valid(self) -> bool:
        try:
            return bool(self.id_token) and time.time() < float(self.expires_at) - 30
        except Exception:
            return bool(self.id_token)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_key": self.api_key,
            "project_id": self.project_id,
            "email": self.email,
            "uid": self.uid,
            "workspace_id": self.workspace_id,
            "refresh_token": self.refresh_token,
            "id_token": self.id_token,
            "expires_at": float(self.expires_at or 0.0),
        }

    @staticmethod
    def from_dict(d: Any) -> FirebaseSession:
        if not isinstance(d, dict):
            return FirebaseSession()
        return FirebaseSession(
            api_key=str(d.get("api_key", "") or ""),
            project_id=str(d.get("project_id", "") or ""),
            email=str(d.get("email", "") or ""),
            uid=str(d.get("uid", "") or ""),
            workspace_id=str(d.get("workspace_id", "") or ""),
            refresh_token=str(d.get("refresh_token", "") or ""),
            id_token=str(d.get("id_token", "") or ""),
            expires_at=float(d.get("expires_at", 0.0) or 0.0),
        )


class FirebaseSessionStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _session_path()

    def load(self) -> FirebaseSession:
        if not self._path.exists():
            return FirebaseSession()
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return FirebaseSession.from_dict(data)
        except Exception:
            return FirebaseSession()

    def save(self, session: FirebaseSession) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def clear(self) -> None:
        try:
            if self._path.exists():
                self._path.unlink()
        except Exception:
            pass


def current_firebase_uid() -> Optional[str]:
    try:
        uid = FirebaseSessionStore().load().uid
        uid = str(uid).strip()
        return uid if uid else None
    except Exception:
        return None


def current_firebase_workspace_id() -> Optional[str]:
    try:
        wid = FirebaseSessionStore().load().workspace_id
        wid = str(wid).strip()
        return wid if wid else None
    except Exception:
        return None
