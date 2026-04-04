from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import List, Optional
import json
import time

from ..utils.app_paths import app_data_dir


def _profiles_path() -> Path:
    p = app_data_dir() / "firebase"
    p.mkdir(parents=True, exist_ok=True)
    return p / "workspace_profiles.json"


@dataclass
class WorkspaceProfile:
    name: str
    workspace_id: str
    email: str = ""
    last_used_at: float = 0.0
    remember_password: bool = False
    keychain_account: str = ""
    display_name: str = ""
    avatar_path: str = ""

    def to_dict(self) -> dict:
        return {
            "name": str(self.name or ""),
            "workspace_id": str(self.workspace_id or ""),
            "email": str(self.email or ""),
            "last_used_at": float(self.last_used_at or 0.0),
            "remember_password": bool(self.remember_password),
            "keychain_account": str(self.keychain_account or ""),
            "display_name": str(self.display_name or ""),
            "avatar_path": str(self.avatar_path or ""),
        }

    @staticmethod
    def from_dict(d: object) -> Optional["WorkspaceProfile"]:
        if not isinstance(d, dict):
            return None
        name = str(d.get("name", "") or "").strip()
        wid = str(d.get("workspace_id", "") or "").strip()
        if not name or not wid:
            return None
        email = str(d.get("email", "") or "").strip()
        try:
            last_used_at = float(d.get("last_used_at", 0.0) or 0.0)
        except Exception:
            last_used_at = 0.0
        remember_password = bool(d.get("remember_password", False))
        keychain_account = str(d.get("keychain_account", "") or "").strip()
        display_name = str(d.get("display_name", "") or "").strip()
        avatar_path = str(d.get("avatar_path", "") or "").strip()
        return WorkspaceProfile(
            name=name,
            workspace_id=wid,
            email=email,
            last_used_at=last_used_at,
            remember_password=remember_password,
            keychain_account=keychain_account,
            display_name=display_name,
            avatar_path=avatar_path,
        )


class FirebaseWorkspaceProfilesStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _profiles_path()
        self._load_ok: bool = True

    def list_profiles(self) -> List[WorkspaceProfile]:
        if not self._path.exists():
            self._load_ok = True
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8") or "[]")
        except Exception:
            self._load_ok = False
            return []
        if not isinstance(raw, list):
            self._load_ok = False
            return []
        self._load_ok = True
        out: List[WorkspaceProfile] = []
        for item in raw:
            p = WorkspaceProfile.from_dict(item)
            if p is not None:
                out.append(p)
        out.sort(key=lambda x: (-float(x.last_used_at or 0.0), x.name.casefold()))
        return out

    def save_profiles(self, profiles: List[WorkspaceProfile]) -> None:
        if not self._load_ok:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.to_dict() for p in list(profiles or [])]
        _tmp = self._path.with_suffix(".tmp")
        with _tmp.open("w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=2))
            f.flush()
            os.fsync(f.fileno())
        os.replace(_tmp, self._path)

    def upsert(
        self,
        *,
        name: str,
        workspace_id: str,
        email: str = "",
        remember_password: bool = False,
        keychain_account: str = "",
    ) -> None:
        name = str(name or "").strip()
        workspace_id = str(workspace_id or "").strip()
        email = str(email or "").strip()
        if not name or not workspace_id:
            return
        keychain_account = str(keychain_account or "").strip()
        items = self.list_profiles()
        updated: List[WorkspaceProfile] = []
        found = False
        for p in items:
            if p.name.casefold() == name.casefold():
                updated.append(
                    WorkspaceProfile(
                        name=name,
                        workspace_id=workspace_id,
                        email=email or p.email,
                        last_used_at=time.time(),
                        remember_password=bool(
                            remember_password or getattr(p, "remember_password", False)
                        ),
                        keychain_account=keychain_account
                        or getattr(p, "keychain_account", ""),
                        display_name=str(getattr(p, "display_name", "") or ""),
                        avatar_path=str(getattr(p, "avatar_path", "") or ""),
                    )
                )
                found = True
            else:
                updated.append(p)
        if not found:
            updated.append(
                WorkspaceProfile(
                    name=name,
                    workspace_id=workspace_id,
                    email=email,
                    last_used_at=time.time(),
                    remember_password=bool(remember_password),
                    keychain_account=keychain_account,
                    display_name="",
                    avatar_path="",
                )
            )
        self.save_profiles(updated)

    def touch(self, *, name: str) -> None:
        name = str(name or "").strip()
        if not name:
            return
        items = self.list_profiles()
        updated: List[WorkspaceProfile] = []
        changed = False
        for p in items:
            if p.name.casefold() == name.casefold():
                updated.append(
                    WorkspaceProfile(
                        name=p.name,
                        workspace_id=p.workspace_id,
                        email=p.email,
                        last_used_at=time.time(),
                        remember_password=bool(getattr(p, "remember_password", False)),
                        keychain_account=str(getattr(p, "keychain_account", "") or ""),
                        display_name=str(getattr(p, "display_name", "") or ""),
                        avatar_path=str(getattr(p, "avatar_path", "") or ""),
                    )
                )
                changed = True
            else:
                updated.append(p)
        if changed:
            self.save_profiles(updated)

    def find_by_workspace_id(self, *, workspace_id: str) -> Optional[WorkspaceProfile]:
        wid = str(workspace_id or "").strip()
        if not wid:
            return None
        for p in self.list_profiles():
            try:
                if str(getattr(p, "workspace_id", "") or "").strip() == wid:
                    return p
            except Exception:
                continue
        return None

    def update_ui_prefs(
        self,
        *,
        workspace_id: str,
        display_name: Optional[str] = None,
        avatar_path: Optional[str] = None,
    ) -> None:
        wid = str(workspace_id or "").strip()
        if not wid:
            return
        items = self.list_profiles()
        updated: List[WorkspaceProfile] = []
        changed = False
        for p in items:
            try:
                if str(getattr(p, "workspace_id", "") or "").strip() != wid:
                    updated.append(p)
                    continue
            except Exception:
                updated.append(p)
                continue

            new_display = str(getattr(p, "display_name", "") or "")
            new_avatar = str(getattr(p, "avatar_path", "") or "")
            if display_name is not None:
                new_display = str(display_name or "").strip()
            if avatar_path is not None:
                new_avatar = str(avatar_path or "").strip()

            updated.append(
                WorkspaceProfile(
                    name=str(getattr(p, "name", "") or ""),
                    workspace_id=wid,
                    email=str(getattr(p, "email", "") or ""),
                    last_used_at=float(getattr(p, "last_used_at", 0.0) or 0.0),
                    remember_password=bool(getattr(p, "remember_password", False)),
                    keychain_account=str(getattr(p, "keychain_account", "") or ""),
                    display_name=new_display,
                    avatar_path=new_avatar,
                )
            )
            changed = True

        if changed:
            self.save_profiles(updated)

    def upsert_recent(
        self,
        *,
        workspace_id: str,
        email: str = "",
        remember_password: bool = False,
        keychain_account: str = "",
    ) -> None:
        workspace_id = str(workspace_id or "").strip()
        email = str(email or "").strip()
        if not workspace_id:
            return
        base = email or "Workspace"
        short = workspace_id.replace("-", "")
        suffix = short[-4:] if len(short) >= 4 else short
        name = f"{base} · {suffix}" if suffix else base
        self.upsert(
            name=name,
            workspace_id=workspace_id,
            email=email,
            remember_password=remember_password,
            keychain_account=keychain_account,
        )

    def delete(self, *, name: str) -> None:
        name = str(name or "").strip()
        if not name:
            return
        items = self.list_profiles()
        kept = [p for p in items if p.name.casefold() != name.casefold()]
        self.save_profiles(kept)
