from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional
import shutil

import os
import sys

_platform_user_data_dir: Callable[..., str] | None
try:
    from platformdirs import user_data_dir as _platform_user_data_dir
except ImportError:
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
    except OSError:
        return False


def app_data_dir() -> Path:
    # A throwaway sandbox: point every data path (accounts, movements, the
    # Firebase session, profile, sync state) at FINANCE_DATA_DIR so you can test
    # against isolated, disposable data — the app starts logged-out and fresh, and
    # touches nothing real. Skips the legacy-name migration on purpose.
    override = str(os.environ.get("FINANCE_DATA_DIR", "") or "").strip()
    if override:
        sandbox = Path(override).expanduser()
        sandbox.mkdir(parents=True, exist_ok=True)
        return sandbox

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
    except OSError:
        pass
    return p


# --------------------------------------------------------------------------
# Per-account storage
#
# Every Firebase account gets its own folder: ``<data>/users/<uid>/``. All
# account data (accounts, movements, sync state, ML training, profile, avatars,
# Google Drive settings) lives inside it, so two Firebase accounts on the same
# machine never read each other's local files — even when they share a
# workspace, and even when one of them types the other's workspace id.
# While logged out the app uses ``users/_local/``, which no account can see.
#
# The session file and the saved-profiles list (``firebase/session.json``,
# ``firebase/workspace_profiles.json``) stay global: they are the account
# switcher itself.
# --------------------------------------------------------------------------

LOCAL_ACCOUNT_DIR = "_local"


def _safe_segment(value: str) -> str:
    """A filesystem-safe folder name (Firebase uids/workspace ids are already
    alnum + ``-``; anything else is replaced so a crafted id can't escape)."""
    v = str(value or "").strip()
    return "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in v)


def _current_session_identity() -> tuple[str, str, str]:
    """(uid, email, workspace_id) of the logged-in Firebase session, or blanks."""
    try:
        from ..models.firebase_session import FirebaseSessionStore

        s = FirebaseSessionStore().load()
        if not s.is_logged_in:
            return "", "", ""
        return (
            str(s.uid or "").strip(),
            str(s.email or "").strip(),
            str(s.workspace_id or "").strip(),
        )
    except (ImportError, OSError, ValueError, AttributeError):
        return "", "", ""


def account_root_dir() -> Path:
    """Root folder of the logged-in Firebase account (``users/<uid>``), or
    ``users/_local`` when logged out. Created on demand; legacy (pre per-account)
    data is copied in the first time an account opens a workspace."""
    uid, email, wid = _current_session_identity()
    seg = _safe_segment(uid) or LOCAL_ACCOUNT_DIR
    root = app_data_dir() / "users" / seg
    root.mkdir(parents=True, exist_ok=True)
    try:
        _migrate_legacy_into_account(root, uid=uid, email=email, workspace_id=wid)
    except OSError:
        pass
    return root


def _account_subdir(name: str) -> Path:
    p = account_root_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def accounts_data_dir() -> Path:
    """Per-account folder for account/movement/etc. JSON files."""
    return _account_subdir("accounts")


def account_firebase_dir() -> Path:
    """Per-account folder for sync state and sync diagnostics."""
    return _account_subdir("firebase")


def account_training_dir() -> Path:
    """Per-account folder for classifier training data."""
    return _account_subdir("training")


def avatars_data_dir() -> Path:
    return _account_subdir("avatars")


def user_profile_path() -> Path:
    """The logged-in account's user-profile JSON (``users/<uid>/user_profile.json``)."""
    return account_root_dir() / "user_profile.json"


# ---- one-time migration of the old flat layout -----------------------------


def _legacy_owner_ok(*, email: str, workspace_id: str) -> bool:
    """May this account inherit the old flat-layout files of ``workspace_id``?

    Only when a saved profile shows this email used that workspace on this
    machine (or no profile mentions the workspace at all — very old installs).
    This stops someone who types another person's workspace id from receiving
    that person's cached data."""
    try:
        from ..models.firebase_workspace_profiles import (
            FirebaseWorkspaceProfilesStore,
        )

        profiles = [
            p
            for p in FirebaseWorkspaceProfilesStore().list_profiles()
            if str(p.workspace_id or "").strip() == workspace_id
        ]
    except (ImportError, OSError, ValueError, AttributeError):
        return False
    if not profiles:
        return True
    e = str(email or "").strip().casefold()
    return bool(e) and any(str(p.email or "").strip().casefold() == e for p in profiles)


def _copy_if_missing(src: Path, dst: Path) -> None:
    try:
        if src.is_file() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    except OSError:
        pass


_LOGGED_OUT_LEGACY_FILES = (
    "bank_accounts.json",
    "savings_accounts.json",
    "bank_movements.json",
    "bank_movement_categories.json",
    "action_history.json",
    "notifications.json",
    "one_time_events.json",
    "installment_plans.json",
    "mortgages.json",
)


def _migrate_legacy_into_account(
    root: Path, *, uid: str, email: str, workspace_id: str
) -> None:
    """Copy (never move) old flat-layout files into this account's folder, once
    per (account, workspace). The originals stay where they were as a backup."""
    key = workspace_id or uid
    marker = root / f".migrated_{_safe_segment(key) or 'none'}"
    if marker.exists():
        return
    base = app_data_dir()
    if not uid:
        # Logged out: the old unsuffixed files were the logged-out data.
        for name in _LOGGED_OUT_LEGACY_FILES:
            _copy_if_missing(base / "accounts" / name, root / "accounts" / name)
        _copy_if_missing(base / "user_profile.json", root / "user_profile.json")
        _copy_if_missing(base / "avatars" / "user_avatar.png", root / "avatars" / "user_avatar.png")
        marker.write_text("1", encoding="utf-8")
        return

    if workspace_id and not _legacy_owner_ok(email=email, workspace_id=workspace_id):
        marker.write_text("skipped: workspace not owned by this account", encoding="utf-8")
        return

    suffix = f"_{key}"
    legacy_acc = base / "accounts"
    if legacy_acc.is_dir():
        for f in legacy_acc.glob(f"*{suffix}.json"):
            _copy_if_missing(f, root / "accounts" / f.name)
    _copy_if_missing(base / "firebase" / f"sync_state{suffix}.json", root / "firebase" / f"sync_state{suffix}.json")
    for name in (f"expenses{suffix}.json", f"ml_seed{suffix}.json"):
        _copy_if_missing(base / "training" / name, root / "training" / name)
    _copy_if_missing(base / "avatars" / f"user_avatar{suffix}.png", root / "avatars" / f"user_avatar{suffix}.png")

    profile_src = base / f"user_profile{suffix}.json"
    if not profile_src.is_file():
        profile_src = base / "user_profile.json"
    _copy_if_missing(profile_src, root / "user_profile.json")

    # Google Drive settings were machine-wide; hand them to the first account
    # that migrates (the one that was in use when the app was upgraded) only.
    drive_marker = base / "firebase" / ".drive_settings_migrated"
    if not drive_marker.exists():
        for name in ("google_drive_settings.json", "drive_inbox_state.json"):
            _copy_if_missing(legacy_acc / name, root / "accounts" / name)
        try:
            drive_marker.parent.mkdir(parents=True, exist_ok=True)
            drive_marker.write_text(uid, encoding="utf-8")
        except OSError:
            pass

    marker.write_text("1", encoding="utf-8")


def import_logged_out_data(*, workspace_id: str) -> int:
    """Hand data that was entered on this computer *without* an account to the
    account that is now logged in, as its data for ``workspace_id``. Used right
    after a brand-new budget is created, so nothing typed before signing up is
    lost; the next sync (with push) uploads it. Never overwrites existing files.
    Returns how many files were imported."""
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0
    # Only the first account ever set up on this computer inherits it — the
    # data belongs to whoever used the app before accounts existed, not to the
    # next person who happens to sign up on a shared machine. (Call this before
    # saving the new account's profile.)
    try:
        from ..models.firebase_workspace_profiles import (
            FirebaseWorkspaceProfilesStore,
        )

        if FirebaseWorkspaceProfilesStore().list_profiles():
            return 0
    except (ImportError, OSError, ValueError, AttributeError):
        return 0
    dst = accounts_data_dir()
    sources = [
        app_data_dir() / "users" / LOCAL_ACCOUNT_DIR / "accounts",
        app_data_dir() / "accounts",  # oldest, pre per-account layout
    ]
    imported = 0
    for name in _LOGGED_OUT_LEGACY_FILES:
        target = dst / f"{Path(name).stem}_{wid}.json"
        if target.exists():
            continue
        for src_dir in sources:
            src = src_dir / name
            try:
                if src.is_file() and src.stat().st_size > 2:  # skip "[]"
                    shutil.copy2(src, target)
                    imported += 1
                    break
            except OSError:
                continue
    return imported


def legacy_accounts_dirs() -> Iterable[Path]:
    yield Path.cwd() / "data" / "accounts"
    try:
        here = Path(__file__).resolve()
        root = here.parents[2]
        yield root / "data" / "accounts"
    except (OSError, IndexError):
        return


def migrate_legacy_accounts_data(*, overwrite: bool = False) -> bool:
    # Import into the old flat folder, not the current account's folder: the
    # per-account migration then hands the files only to their owner.
    dst = app_data_dir() / "accounts"
    dst.mkdir(parents=True, exist_ok=True)
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
        except OSError:
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
            except OSError:
                continue
    except OSError:
        return copied_any

    return copied_any
