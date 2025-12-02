from __future__ import annotations

import sys
from typing import Optional

from .qt import QApplication
from .styles.theme import load_default_stylesheet
from .ui.main_window import MainWindow


def run_app(argv: Optional[list[str]] = None) -> None:
    if argv is None:
        argv = sys.argv

    app = QApplication(argv)
    app.setApplicationName("Finence")
    app.setOrganizationName("Finence")

    app.setStyleSheet(load_default_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
