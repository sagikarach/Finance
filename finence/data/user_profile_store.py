from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from ..models.accounts import MoneyAccount
from ..models.user import UserProfile


class UserProfileStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or (Path.cwd() / "user_profile.json")

    def load(self, default_full_name: str, accounts: List[MoneyAccount]) -> UserProfile:
        full_name = default_full_name
        avatar_path: Optional[str] = None

        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    full_name = str(data.get("full_name", default_full_name))
                    raw_avatar = data.get("avatar_path")
                    avatar_path = str(raw_avatar) if raw_avatar else None
            except Exception:
                pass
        else:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

        profile = UserProfile(full_name=full_name, avatar_path=avatar_path, accounts=list(accounts))
        self.save(profile)
        return profile

    def save(self, profile: UserProfile) -> None:
        data = {
            "full_name": profile.full_name,
            "avatar_path": profile.avatar_path,
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # Failing to save the profile should not crash the app.
            pass


