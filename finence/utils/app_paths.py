from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
import shutil

import os
import sys

try:
    from platformdirs import user_data_dir as _platform_user_data_dir  # type: ignore
except Exception:
    _platform_user_data_dir = None


APP_NAME = "Finence"
APP_AUTHOR = "Finence"


def app_data_dir() -> Path:
    if _platform_user_data_dir is not None:
        p = Path(_platform_user_data_dir(APP_NAME, APP_AUTHOR))
    else:
        home = Path.home()
        if sys.platform == "darwin":
            p = home / "Library" / "Application Support" / APP_NAME
        elif sys.platform.startswith("win"):
            base = os.environ.get("APPDATA")
            if base:
                p = Path(base) / APP_NAME
            else:
                p = home / "AppData" / "Roaming" / APP_NAME
        else:
            p = home / ".local" / "share" / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def accounts_data_dir() -> Path:
    p = app_data_dir() / "accounts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def avatars_data_dir() -> Path:
    p = app_data_dir() / "avatars"
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_profile_path() -> Path:
    return app_data_dir() / "user_profile.json"


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
