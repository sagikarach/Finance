from __future__ import annotations

import os
import socket
import subprocess
import sys
from io import TextIOWrapper
from typing import Optional

from .qt import QApplication, QIcon
from .styles.theme import load_default_stylesheet
from .ui.main_window import MainWindow
from .ui.lock_dialog import LockDialog
from .data.user_profile_store import UserProfileStore
from .utils.defaults import load_defaults
from .utils.resources import find_first_existing


class FilteredStderr:
    def __init__(self, original_stderr: TextIOWrapper) -> None:
        self.original_stderr = original_stderr

    def write(self, message: str) -> None:
        if "TSMSendMessageToUIServer" not in message:
            self.original_stderr.write(message)

    def flush(self) -> None:
        self.original_stderr.flush()

    def __getattr__(self, name: str) -> object:
        return getattr(self.original_stderr, name)


def _ensure_ollama_running() -> None:
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.5):
            return
    except Exception:
        pass

    try:
        from shutil import which

        cmd: Optional[list[str]] = None
        bin_path = which("ollama")
        if bin_path:
            cmd = [bin_path, "serve"]
        elif sys.platform == "darwin":
            cmd = ["open", "-g", "-a", "Ollama"]

        if cmd is not None:
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
    except Exception:
        pass


def run_app(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        argv = sys.argv

    if sys.platform == "darwin":
        os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")
        if isinstance(sys.stderr, TextIOWrapper):
            sys.stderr = FilteredStderr(sys.stderr)

    app = QApplication(argv)
    app.setApplicationName("Finance")
    app.setOrganizationName("Finance")
    icon_path = None
    try:
        icon_path = find_first_existing(["app-icon.icns", "app-icon.ico"])
        if icon_path is not None:
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass

    defaults = load_defaults()

    app.setStyleSheet(load_default_stylesheet())
    try:
        app.setProperty("theme", defaults["default_theme"])
    except Exception:
        pass

    try:
        store = UserProfileStore()
        profile = store.load(
            default_full_name=defaults["default_full_name"], accounts=[]
        )
        expected_password = profile.password or ""
        lock_enabled = bool(getattr(profile, "lock_enabled", False))
    except Exception:
        expected_password = ""
        lock_enabled = False

    if lock_enabled and expected_password:
        lock = LockDialog(expected_password=expected_password)
        result = lock.exec()
        if not result:
            sys.exit(0)

    window = MainWindow()
    try:
        if icon_path is not None:
            window.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    window.show()

    sys.exit(app.exec())


