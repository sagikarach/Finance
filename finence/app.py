from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from .qt import QApplication
from .styles.theme import load_default_stylesheet
from .ui.main_window import MainWindow
from .ui.lock_dialog import LockDialog
from .data.user_profile_store import UserProfileStore


def _load_defaults() -> dict:
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
                    default_full_name = str(user_defaults.get("default_full_name", default_full_name))
                    default_theme = str(app_defaults.get("default_theme", default_theme))
        except Exception:
            pass

    return {
        "default_full_name": default_full_name,
        "default_theme": default_theme,
    }


def run_app(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("Finence")
    app.setOrganizationName("Finence")

    # Load defaults from JSON file
    defaults = _load_defaults()

    app.setStyleSheet(load_default_stylesheet())
    try:
        app.setProperty("theme", defaults["default_theme"])
    except Exception:
        pass

    # Optional lock screen: if a password is configured, ask for it before opening
    try:
        store = UserProfileStore()
        profile = store.load(default_full_name=defaults["default_full_name"], accounts=[])
        expected_password = profile.password or ""
        lock_enabled = bool(getattr(profile, "lock_enabled", False))
    except Exception:
        expected_password = ""
        lock_enabled = False

    if lock_enabled and expected_password:
        lock = LockDialog(expected_password=expected_password)
        # If dialog is rejected or password is wrong, exit without opening main window
        result = lock.exec()
        if not result:
            sys.exit(0)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
