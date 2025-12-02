from __future__ import annotations

import sys
from typing import Optional

from .qt import QApplication
from .styles.theme import load_default_stylesheet
from .ui.main_window import MainWindow
from .ui.lock_dialog import LockDialog
from .data.user_profile_store import UserProfileStore


def run_app(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("Finence")
    app.setOrganizationName("Finence")

    app.setStyleSheet(load_default_stylesheet())
    try:
        app.setProperty("theme", "light")
    except Exception:
        pass

    # Optional lock screen: if a password is configured, ask for it before opening
    try:
        store = UserProfileStore()
        profile = store.load(default_full_name="אורח", accounts=[])
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
