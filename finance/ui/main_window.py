from __future__ import annotations

from typing import Dict

from ..pages.home_page import HomePage
from ..pages.settings_page import SettingsPage
from ..pages.savings_page import SavingsPage
from ..pages.savings_account_page import SavingsAccountPage
from ..pages.bank_accounts_page import BankAccountsPage
from ..pages.bank_account_page import BankAccountPage
from ..pages.monthly_data_page import MonthlyDataPage
from ..pages.one_time_events_page import OneTimeEventsPage
from ..pages.installments_page import InstallmentsPage
from ..pages.yearly_summary_page import YearlySummaryPage
from ..pages.yearly_category_trends_page import YearlyCategoryTrendsPage
from ..pages.yearly_overview_page import YearlyOverviewPage
from ..qt import QAction, QMainWindow, QStackedWidget, QTimer
from .router import Router
from ..utils.app_paths import migrate_legacy_accounts_data
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_movements_sync import FirebaseMovementsSyncService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        try:
            migrate_legacy_accounts_data()
        except Exception:
            pass
        self.setWindowTitle("Finance")
        self.resize(1024, 720)

        self._app_context: Dict[str, str] = {"appName": "Finance"}

        self._stack = QStackedWidget(self)
        self.setCentralWidget(self._stack)

        self.router = Router(self._stack)
        self._register_pages()
        self._build_menu()

        self.router.navigate("home")
        self._startup_pull_sync_started = False
        try:
            QTimer.singleShot(250, self._maybe_start_startup_pull_sync)
        except Exception:
            try:
                self._maybe_start_startup_pull_sync()
            except Exception:
                pass

    def _maybe_start_startup_pull_sync(self) -> None:
        if bool(getattr(self, "_startup_pull_sync_started", False)):
            return
        self._startup_pull_sync_started = True

        try:
            s = FirebaseSessionStore().load()
            wid = str(getattr(s, "workspace_id", "") or "").strip()
            if not (bool(getattr(s, "is_logged_in", False)) and wid):
                return
        except Exception:
            return

        def _worker() -> None:
            try:
                FirebaseMovementsSyncService().sync_now(allow_push=False)
            except Exception:
                return

            def _ui_refresh() -> None:
                try:
                    if isinstance(self._app_context, dict):
                        self._app_context["_balances_dirty"] = "1"
                except Exception:
                    pass
                try:
                    current = self.router.current_route() or "home"
                    self.router.navigate(current)
                except Exception:
                    pass

            try:
                QTimer.singleShot(0, _ui_refresh)
            except Exception:
                _ui_refresh()

        try:
            import threading

            threading.Thread(target=_worker, daemon=True).start()
        except Exception:
            _worker()

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
            "one_time_events",
            lambda: OneTimeEventsPage(
                app_context=self._app_context,
                parent=self._stack,
                navigate=self.router.navigate,
            ),
        )
        self.router.register(
            "installments",
            lambda: InstallmentsPage(
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
        action_installments = QAction("תשלומים", self)
        action_installments.triggered.connect(
            lambda: self.router.navigate("installments")
        )
        nav_menu.addAction(action_installments)
