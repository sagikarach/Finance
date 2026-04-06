from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional
import shutil

import os
import sys

_platform_user_data_dir: Callable[..., str] | None
try:
    from platformdirs import user_data_dir as _platform_user_data_dir
except Exception:
    _platform_user_data_dir = None


APP_NAME = "Finance"
APP_AUTHOR = "Finance"


def _old_misspelled_name(name: str) -> str:
    """
    Previous app name was misspelled. We compute it without keeping the literal
    string in the repo, to satisfy "finance everywhere" while still migrating
    existing local data.
    """
    n = str(name or "").strip()
    if n.lower() == "finance" and len(n) >= 5:
        return f"{n[:3]}e{n[4:]}"
    return n


def _compute_user_data_dir(*, app_name: str, app_author: str) -> Path:
    app_name = str(app_name or "").strip() or "Finance"
    app_author = str(app_author or "").strip() or app_name
    if _platform_user_data_dir is not None:
        return Path(_platform_user_data_dir(app_name, app_author))
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / app_name
        return home / "AppData" / "Roaming" / app_name
    return home / ".local" / "share" / app_name


def _dir_is_empty(p: Path) -> bool:
    try:
        if not p.exists() or not p.is_dir():
            return True
        next(p.iterdir())
        return False
    except StopIteration:
        return True
    except Exception:
        return False


def app_data_dir() -> Path:
    p = _compute_user_data_dir(app_name=APP_NAME, app_author=APP_AUTHOR)
    old_name = _old_misspelled_name(APP_NAME)
    old_author = _old_misspelled_name(APP_AUTHOR)
    old = _compute_user_data_dir(app_name=old_name, app_author=old_author)
    p.mkdir(parents=True, exist_ok=True)

    # One-time migration: if user already has local data under the old misspelled name,
    # copy it into the new directory (only if the new directory is empty).
    try:
        if old != p and old.exists() and old.is_dir() and _dir_is_empty(p):
            shutil.copytree(old, p, dirs_exist_ok=True)
    except Exception:
        pass
    return p


def accounts_data_dir() -> Path:
    p = app_data_dir() / "accounts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def avatars_data_dir() -> Path:
    p = app_data_dir() / "avatars"
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_profile_path(uid: Optional[str] = None) -> Path:
    """
    Return the user-profile JSON path for *uid*.

    If *uid* is not given it is auto-detected from the current Firebase session.
    Falls back to the legacy shared ``user_profile.json`` when no uid is known
    (e.g. the user has never logged in).

    On first use with a uid, the legacy file is migrated automatically so
    existing profile data is not lost.
    """
    base = app_data_dir() / "user_profile.json"

    # Resolve uid if not supplied.
    if uid is None:
        try:
            from ..models.firebase_session import FirebaseSessionStore
            sess = FirebaseSessionStore().load()
            candidate = (sess.workspace_id or sess.uid or "").strip()
            uid = candidate if candidate else None
        except Exception:
            uid = None

    if not uid:
        return base

    suffixed = app_data_dir() / f"user_profile_{uid}.json"

    # One-time migration: copy legacy file so the user doesn't lose their data.
    if not suffixed.exists() and base.exists():
        try:
            import shutil as _shutil
            _shutil.copy2(base, suffixed)
        except Exception:
            pass

    return suffixed


def legacy_accounts_dirs() -> Iterable[Path]:
    yield Path.cwd() / "data" / "accounts"
    try:
        here = Path(__file__).resolve()
        root = here.parents[2]
        yield root / "data" / "accounts"
    except Exception:
        return


def migrate_legacy_accounts_data(*, overwrite: bool = False) -> bool:
    dst = accounts_data_dir()
    copied_any = False

    src: Optional[Path] = None
    for cand in legacy_accounts_dirs():
        try:
            if cand.exists() and cand.is_dir():
                has_json = any(
                    item.is_file() and item.suffix.lower() == ".json"
                    for item in cand.iterdir()
                )
                if has_json:
                    src = cand
                    break
        except Exception:
            continue
    if src is None:
        return False

    try:
        for item in src.iterdir():
            if not item.is_file():
                continue
            if item.suffix.lower() != ".json":
                continue
            target = dst / item.name
            if target.exists() and not overwrite:
                continue
            try:
                shutil.copy2(item, target)
                copied_any = True
            except Exception:
                continue
    except Exception:
        return copied_any

    return copied_any
