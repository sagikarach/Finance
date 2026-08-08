from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from ..utils.logging_setup import get_logger

_WRITE_LOCK = threading.Lock()
_log = get_logger("data")


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """Write *data* to *path* as JSON atomically.

    Writes to a temp file in the same directory, fsyncs it, then ``os.replace``s
    it into place — so a crash mid-write can never leave a half-written /
    truncated target file. A module lock serializes writers so their tempfiles
    don't collide. Mirrors the pattern the mortgage/bank-movement providers
    already use, so every workspace file is written the same crash-safe way.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    # fsync isn't available on every filesystem; harmless.
                    pass
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise


def workspace_json_path(stem: str, explicit: Any = None) -> Path:
    """Path to a per-workspace JSON file: ``<data_dir>/<stem>_<workspace|uid>.json``
    (or ``explicit`` when given). Centralizes the workspace-suffix logic that
    every provider re-implemented identically."""
    if explicit is not None:
        return Path(explicit)
    from ..models.firebase_session import (
        current_firebase_uid,
        current_firebase_workspace_id,
    )
    from ..utils.app_paths import accounts_data_dir

    key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
    suffix = f"_{key}" if key else ""
    return accounts_data_dir() / f"{stem}{suffix}.json"


def read_json_list(path: Path, deserialize) -> list:
    """Read a JSON-array file and map each item through ``deserialize``, skipping
    ``None`` results. Returns ``[]`` on a missing file, a parse error, or non-list
    content — the exact shape every provider's ``list_*`` repeated."""
    path = Path(path)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        _log.warning("could not read %s: %s", path, exc)
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        obj = deserialize(item)
        if obj is not None:
            out.append(obj)
    return out
