from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Optional

from .qt import QApplication
from .styles.theme import load_default_stylesheet
from .ui.main_window import MainWindow
from .ui.lock_dialog import LockDialog
from .data.user_profile_store import UserProfileStore


class FilteredStderr:
    """Filter stderr to suppress macOS TSMSendMessageToUIServer warnings."""

    def __init__(self, original_stderr: TextIOWrapper) -> None:
        self.original_stderr = original_stderr

    def write(self, message: str) -> None:
        # Filter out TSMSendMessageToUIServer warnings
        if "TSMSendMessageToUIServer" not in message:
            self.original_stderr.write(message)

    def flush(self) -> None:
        self.original_stderr.flush()

    def __getattr__(self, name: str) -> object:
        # Forward all other attributes to original stderr
        return getattr(self.original_stderr, name)


def _load_defaults() -> dict:
    """Load default theme and user name from defaults.json if present."""
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
            # If defaults.json is missing or invalid we just keep built-in defaults.
            pass

    return {
        "default_full_name": default_full_name,
        "default_theme": default_theme,
    }


def _ensure_ollama_running() -> None:
    """
    Best-effort helper to make sure a local Ollama server is running.

    - First, try to connect to http://127.0.0.1:11434; if it responds, do nothing.
    - If not running, try to start it in the background:
        * Prefer `ollama serve` if `ollama` is on PATH.
        * On macOS, fall back to `open -g -a Ollama` if available.

    All failures are ignored so the app still runs even if Ollama is not installed.
    """
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

    # Suppress macOS TSMSendMessageToUIServer warnings (harmless system messages)
    if sys.platform == "darwin":
        os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false")
        # Filter stderr to remove TSMSendMessageToUIServer messages
        if isinstance(sys.stderr, TextIOWrapper):
            sys.stderr = FilteredStderr(sys.stderr)

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
        # If dialog is rejected or password is wrong, exit without opening main window
        result = lock.exec()
        if not result:
            sys.exit(0)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
