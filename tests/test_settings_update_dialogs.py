"""Settings → "בדיקת עדכונים": its dialogs belong to the main window.

Regression: they were parented to the settings page's own container. The
page rebuilds itself (e.g. when the startup sync finishes), deleting that
container — and with it a modal dialog that was still open — which aborted
the app ("pointer being freed was not allocated") during an update.
"""

from __future__ import annotations

import os
import socket
import sys
from typing import Any, List

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


@pytest.fixture
def window(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(socket.socket, "connect", lambda *a, **k: (_ for _ in ()).throw(OSError("net")))
    import finance.models.sync_gate as gate

    monkeypatch.setattr(gate, "allow_firebase_push", lambda *a, **k: False)
    from finance.qt import QApplication, QMainWindow, QStackedWidget

    app = QApplication.instance() or QApplication([])
    win = QMainWindow()
    stack = QStackedWidget(win)
    win.setCentralWidget(stack)
    yield app, win, stack
    win.close()


def test_update_dialogs_are_parented_to_the_main_window(window: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    app, win, stack = window
    import finance.pages.settings_page as sp
    import finance.qt as qt

    parents: List[Any] = []

    class Box:
        class StandardButton:
            Yes, No = 1, 2

        @staticmethod
        def _record(parent: Any, *a: Any, **k: Any) -> int:
            parents.append(parent)
            return 2  # "No" — stop before downloading

        information = warning = question = _record

    class Progress:
        def __init__(self, *a: Any) -> None:
            parents.append(a[-1])

        def __getattr__(self, _name: str) -> Any:
            return lambda *a, **k: None

    monkeypatch.setattr(sp, "QMessageBox", Box)
    monkeypatch.setattr(qt, "QProgressDialog", Progress, raising=False)
    monkeypatch.setattr(sp, "check_version_only", lambda: (True, "9.9.9", "url", None))
    monkeypatch.setattr(sys, "platform", "darwin")

    page = sp.SettingsPage(parent=stack)
    stack.addWidget(page)
    from finance.qt import QToolButton

    button = next(b for b in page.findChildren(QToolButton) if b.text() == "בדיקת עדכונים (macOS)")
    button.click()
    for _ in range(50):  # the check runs on a thread and reports back via the event loop
        app.processEvents()
        if len(parents) >= 2:
            break
    assert len(parents) >= 2, parents  # the progress dialog + "update available?"
    assert all(p is win for p in parents), [type(p).__name__ for p in parents]
