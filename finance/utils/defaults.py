from __future__ import annotations

import json
from typing import Dict

from .resources import _candidate_roots


def load_defaults() -> Dict[str, str]:
    defaults_path = None
    for root in _candidate_roots():
        candidate = root / "defaults.json"
        if candidate.exists():
            defaults_path = candidate
            break

    default_theme = "light"
    default_full_name = "אורח"

    if defaults_path is not None:
        try:
            with defaults_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    user_defaults = data.get("user", {})
                    app_defaults = data.get("app", {})
                    default_full_name = str(
                        user_defaults.get("default_full_name", default_full_name)
                    )
                    default_theme = str(
                        app_defaults.get("default_theme", default_theme)
                    )
        except Exception:
            pass

    return {
        "default_full_name": default_full_name,
        "default_theme": default_theme,
    }
