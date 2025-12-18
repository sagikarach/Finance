from __future__ import annotations

from typing import Dict

from ..pages.home_page import HomePage
from ..pages.settings_page import SettingsPage
from ..pages.savings_page import SavingsPage
from ..pages.savings_account_page import SavingsAccountPage
from ..pages.bank_accounts_page import BankAccountsPage
from ..pages.bank_account_page import BankAccountPage
from ..pages.monthly_data_page import MonthlyDataPage
from ..pages.yearly_summary_page import YearlySummaryPage
from ..pages.yearly_category_trends_page import YearlyCategoryTrendsPage
from ..pages.yearly_overview_page import YearlyOverviewPage
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
            "home",
            lambda: HomePage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "settings",
            lambda: SettingsPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
                get_previous_route=lambda: self.router.previous_route(),
            ),
        )
        self.router.register(
            "savings",
            lambda: SavingsPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "savings_account",
            lambda: SavingsAccountPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "bank_accounts",
            lambda: BankAccountsPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "bank_account",
            lambda: BankAccountPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "monthly_data",
            lambda: MonthlyDataPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "yearly_overview",
            lambda: YearlyOverviewPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "yearly_data",
            lambda: YearlySummaryPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "yearly_category_trends",
            lambda: YearlyCategoryTrendsPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()

        nav_menu = menu_bar.addMenu("Navigate")
        action_home = QAction("Home", self)
        action_home.triggered.connect(lambda: self.router.navigate("home"))
        nav_menu.addAction(action_home)
        action_bank = QAction("חשבונות", self)
        action_bank.triggered.connect(lambda: self.router.navigate("bank_accounts"))
        nav_menu.addAction(action_bank)
