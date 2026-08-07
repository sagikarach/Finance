from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

_WRITE_LOCK = threading.Lock()


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
