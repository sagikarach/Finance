from __future__ import annotations

from typing import Dict

from ..pages.home_page import HomePage
from ..qt import QAction, QMainWindow, QStackedWidget
from .router import Router


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Finence")
        self.resize(1024, 720)

        self._app_context: Dict[str, str] = {"appName": "Finence"}

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self.router = Router(self._stack)
        self._register_pages()
        self._build_menu()

        self.router.navigate("home")

    def _register_pages(self) -> None:
        self.router.register(
            "home", lambda: HomePage(app_context=self._app_context, parent=self._stack)
        )

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        nav_menu = menu_bar.addMenu("Navigate")
        action_home = QAction("Home", self)
        action_home.triggered.connect(lambda: self.router.navigate("home"))
        nav_menu.addAction(action_home)
