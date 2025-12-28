from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
import sys


def _candidate_roots() -> Iterable[Path]:
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str) and meipass:
        yield Path(meipass)

    try:
        # .../finence/utils/resources.py -> project root is 2 levels up from finence/
        yield Path(__file__).resolve().parents[2]
    except Exception:
        pass

    yield Path.cwd()


def find_first_existing(relative_paths: Iterable[str]) -> Optional[Path]:
    rels = [str(p).lstrip("/\\") for p in relative_paths]
    for root in _candidate_roots():
        for rel in rels:
            try:
                p = root / rel
                if p.exists():
                    return p
            except Exception:
                continue
    return None
