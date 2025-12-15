from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_defaults() -> Dict[str, str]:
    defaults_path = Path.cwd() / "defaults.json"
    default_theme = "light"
    default_full_name = "אורח"

    if defaults_path.exists():
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
