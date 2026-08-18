"""One-time migration: rewrite every stored ``date`` to canonical ISO.

Historically dates were saved in whatever format their source produced
(``dd/mm/yyyy``, ``dd.mm.yy``, ``dd-mm-yyyy``, ...). Reads tolerate the mix, but
it's fragile — mobile is ISO-only. New writes are now normalized at the model
level (:class:`BankMovement`, :class:`MoneySnapshot`); this pass fixes the data
already on disk so the whole store settles on one format.

Idempotent and guarded by a marker file, so it scans once per data directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..utils.app_paths import accounts_data_dir
from ..utils.dates import to_iso_date
from ..utils.logging_setup import get_logger

_log = get_logger(__name__)

_MARKER_NAME = ".dates_normalized"


def _normalize_in_place(obj: Any) -> bool:
    """Recursively normalize every ``"date"`` string to ISO. Returns True if
    anything changed. Timestamp-like values (carrying a time component) are
    left alone so nothing is truncated."""
    changed = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "date" and isinstance(value, str) and value.strip():
                if "T" in value or ":" in value:
                    continue  # a datetime, not a plain day — don't touch
                iso = to_iso_date(value)
                if iso != value:
                    obj[key] = iso
                    changed = True
            elif isinstance(value, (dict, list)):
                changed = _normalize_in_place(value) or changed
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                changed = _normalize_in_place(item) or changed
    return changed


def migrate_dates_to_iso(data_dir: Optional[Path] = None) -> int:
    """Normalize dates in every ``*.json`` under the accounts data dir to ISO.

    Runs once per directory (guarded by a marker file). Returns the number of
    files rewritten. Never raises — a bad file is skipped, not fatal.
    """
    base = Path(data_dir) if data_dir is not None else accounts_data_dir()
    marker = base / _MARKER_NAME
    try:
        if marker.exists():
            return 0
    except OSError:
        return 0

    changed_files = 0
    try:
        json_files = sorted(base.glob("*.json"))
    except OSError:
        json_files = []

    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _log.warning("date migration: skipping %s (%s)", path.name, exc)
            continue
        if _normalize_in_place(data):
            try:
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                changed_files += 1
                _log.info("date migration: normalized dates in %s", path.name)
            except OSError as exc:
                _log.warning("date migration: could not write %s (%s)", path.name, exc)

    try:
        marker.write_text("done", encoding="utf-8")
    except OSError:
        pass

    if changed_files:
        _log.info("date migration: normalized %d file(s) to ISO", changed_files)
    return changed_files
