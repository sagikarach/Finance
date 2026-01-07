from __future__ import annotations

import threading
from contextlib import contextmanager


_tls = threading.local()


def is_syncing() -> bool:
    try:
        return bool(getattr(_tls, "syncing", False))
    except Exception:
        return False


def allow_firebase_push() -> bool:
    """
    Policy: we only push to Firebase when the user explicitly presses Sync.
    """
    return is_syncing()


@contextmanager
def sync_context():
    """
    Marks the current thread as running an explicit Sync action.
    """
    prev = False
    try:
        prev = bool(getattr(_tls, "syncing", False))
    except Exception:
        prev = False
    try:
        _tls.syncing = True
        yield
    finally:
        try:
            _tls.syncing = prev
        except Exception:
            pass
