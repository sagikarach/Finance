from __future__ import annotations

from pathlib import Path

from ..utils.app_paths import accounts_data_dir, app_data_dir
from ..utils.safe import swallow


def _safe_unlink(p: Path) -> bool:
    with swallow(msg="_safe_unlink"):
        if p.exists() and p.is_file():
            p.unlink()
            return True
    return False


def reset_workspace_local_cache(*, workspace_id: str) -> int:
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0

    deleted = 0

    acc_dir = accounts_data_dir()
    with swallow(msg="reset_workspace_local_cache"):
        for p in acc_dir.glob(f"*_{wid}.json"):
            if p.is_file():
                _safe_unlink(p)
                deleted += 1

    with swallow(msg="reset_workspace_local_cache"):
        fb_dir = app_data_dir() / "firebase"
        if _safe_unlink(fb_dir / f"sync_state_{wid}.json"):
            deleted += 1

    with swallow(msg="reset_workspace_local_cache"):
        tr_dir = app_data_dir() / "training"
        if _safe_unlink(tr_dir / f"ml_seed_{wid}.json"):
            deleted += 1

    return int(deleted)
