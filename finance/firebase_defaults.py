from __future__ import annotations
import os

# Load from environment variable or local config file (never hardcode here).
# Set FINANCE_FIREBASE_API_KEY and FINANCE_FIREBASE_PROJECT_ID in your environment,
# or create a local file  finance/firebase_defaults_local.py  (git-ignored) with:
#   API_KEY = "AIza..."
#   PROJECT_ID = "your-project-id"
def _load_local() -> tuple[str, str]:
    try:
        from .firebase_defaults_local import API_KEY as k, PROJECT_ID as p  # type: ignore[import]
        return k, p
    except Exception:
        pass
    return (
        os.environ.get("FINANCE_FIREBASE_API_KEY", ""),
        os.environ.get("FINANCE_FIREBASE_PROJECT_ID", ""),
    )

API_KEY, PROJECT_ID = _load_local()


