from __future__ import annotations

from pathlib import Path

from ..utils.app_paths import accounts_data_dir, app_data_dir


def _safe_unlink(p: Path) -> None:
    try:
        if p.exists() and p.is_file():
            p.unlink()
    except Exception:
        pass


def reset_workspace_local_cache(*, workspace_id: str) -> int:
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0

    deleted = 0

    acc_dir = accounts_data_dir()
    try:
        for p in acc_dir.glob(f"*_{wid}.json"):
            if p.is_file():
                _safe_unlink(p)
                deleted += 1
    except Exception:
        pass

    try:
        fb_dir = app_data_dir() / "firebase"
        _safe_unlink(fb_dir / f"sync_state_{wid}.json")
        deleted += 1
    except Exception:
        pass

    try:
        tr_dir = app_data_dir() / "training"
        _safe_unlink(tr_dir / f"ml_seed_{wid}.json")
        deleted += 1
    except Exception:
        pass

    return int(deleted)
