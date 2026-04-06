from __future__ import annotations

from typing import Dict
import sys
import threading
import pathlib

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
from ..utils.updater import check_version_only, download_and_install_update, install_app_to_applications


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
        if not sys.platform.startswith("win"):
            self._build_menu()
        else:
            try:
                self.setMenuBar(None)
            except Exception:
                pass

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

        # Mark syncing globally so any active BasePage shows the hourglass icon.
        try:
            from ..pages.base_page import BasePage
            BasePage._GLOBAL_SYNCING = True
            self._startup_sync_update_current_page_btn(syncing=True)
        except Exception:
            pass

        def _worker() -> None:
            try:
                FirebaseMovementsSyncService().sync_now(allow_push=False)
            except Exception:
                pass

            def _ui_refresh() -> None:
                try:
                    from ..pages.base_page import BasePage
                    BasePage._GLOBAL_SYNCING = False
                except Exception:
                    pass
                self._startup_sync_update_current_page_btn(syncing=False)
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

            QTimer.singleShot(0, self, _ui_refresh)

        try:
            threading.Thread(target=_worker, daemon=True).start()
        except Exception:
            _worker()

    def _startup_sync_update_current_page_btn(self, *, syncing: bool) -> None:
        """Update the sync button on the currently visible page."""
        try:
            page = self._stack.currentWidget()
            if page is None:
                return
            from ..pages.base_page import BasePage
            if not isinstance(page, BasePage):
                return
            if syncing:
                try:
                    page._sync_in_progress = True
                    page._update_sync_icon()
                    if page._sync_btn is not None:
                        page._sync_btn.setEnabled(False)
                        page._sync_btn.setToolTip("מסנכרן...")
                except Exception:
                    pass
            else:
                try:
                    page._sync_in_progress = False
                    page._update_sync_icon()
                    page._refresh_sync_button_state()
                except Exception:
                    pass
        except Exception:
            pass

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

        help_menu = menu_bar.addMenu("Help")
        action_update = QAction("Check for Updates (macOS)", self)
        action_update.triggered.connect(self._check_for_updates_action)
        help_menu.addAction(action_update)

    def _check_for_updates_action(self) -> None:
        if sys.platform != "darwin":
            return

        from ..qt import QMessageBox, QProgressDialog  # type: ignore[attr-defined]

        # Show "checking…" dialog while querying GitHub (non-blocking via thread).
        progress = QProgressDialog("בודק עדכונים...", None, 0, 0, self)
        progress.setWindowTitle("עדכון")
        progress.setMinimumDuration(0)
        progress.setWindowModality(2)  # WindowModal
        progress.setValue(0)
        progress.show()

        # Safety: force-close after 25 seconds if the network call hangs.
        _deadline = QTimer(self)
        _deadline.setSingleShot(True)
        def _on_deadline() -> None:
            try:
                progress.close()
            except Exception:
                pass
            QMessageBox.warning(self, "עדכון", "בדיקת העדכון לקחה יותר מדי זמן. בדוק את החיבור לאינטרנט.")
        _deadline.timeout.connect(_on_deadline)
        _deadline.start(25000)

        def _check_worker() -> None:
            import socket
            socket.setdefaulttimeout(15)
            is_newer, latest, zip_url_sig, error = False, "", None, None
            try:
                is_newer, latest, zip_url_sig, error = check_version_only()
            except Exception as exc:
                error = str(exc)

            def _after_check() -> None:
                try:
                    _deadline.stop()
                except Exception:
                    pass
                try:
                    progress.close()
                except Exception:
                    pass

                if error:
                    from ..qt import QMessageBox
                    QMessageBox.warning(self, "עדכון", f"בדיקת עדכון נכשלה:\n{error}")
                    return

                from ..__version__ import __version__
                from ..qt import QMessageBox
                if not is_newer:
                    QMessageBox.information(
                        self,
                        "עדכון",
                        f"הגרסה הנוכחית ({__version__}) היא העדכנית ביותר." if latest
                        else "לא נמצאה גרסה חדשה יותר.",
                    )
                    return

                # Newer version found — ask user before downloading.
                answer = QMessageBox.question(
                    self,
                    "עדכון זמין",
                    f"גרסה חדשה {latest} זמינה (הגרסה שלך: {__version__}).\n\n"
                    "האם להוריד ולהתקין עכשיו?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return

                if not zip_url_sig:
                    QMessageBox.warning(
                        self, "עדכון",
                        f"גרסה {latest} זמינה אך לא ניתן להוריד אוטומטית.\n"
                        "יש להוריד ידנית מ-GitHub.",
                    )
                    return

                self._download_and_install_update(latest, zip_url_sig)

            QTimer.singleShot(0, self, _after_check)

        try:
            threading.Thread(target=_check_worker, daemon=True).start()
        except Exception:
            _check_worker()

    def _download_and_install_update(self, version: str, zip_url_sig: str) -> None:
        from ..qt import QMessageBox, QProgressDialog  # type: ignore[attr-defined]
        import subprocess

        progress = QProgressDialog(f"מוריד גרסה {version}...", None, 0, 0, self)
        progress.setWindowTitle("עדכון")
        progress.setMinimumDuration(0)
        progress.setWindowModality(2)
        progress.setValue(0)
        progress.show()

        def _dl_worker() -> None:
            app_path, error = download_and_install_update(zip_url_sig)

            def _after_dl() -> None:
                try:
                    progress.close()
                except Exception:
                    pass

                if error or app_path is None:
                    QMessageBox.warning(
                        self, "עדכון",
                        f"הורדת העדכון נכשלה:\n{error or 'Finance.app לא נמצא'}",
                    )
                    return

                # Ask whether to install to /Applications/ now.
                answer = QMessageBox.question(
                    self,
                    "התקנת עדכון",
                    f"גרסה {version} הורדה בהצלחה.\n\n"
                    "להתקין ל-/Applications/Finance.app ולהפעיל מחדש?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    QMessageBox.information(
                        self, "עדכון",
                        f"הקובץ נמצא ב:\n{app_path}\n\nגרור ל-/Applications/ ידנית.",
                    )
                    return

                inst_err = install_app_to_applications(app_path)
                if inst_err:
                    QMessageBox.warning(
                        self, "עדכון",
                        f"ההתקנה נכשלה:\n{inst_err}\n\n"
                        f"העתק ידנית מ:\n{app_path}",
                    )
                    return

                QMessageBox.information(
                    self, "עדכון הותקן",
                    f"גרסה {version} הותקנה ב-/Applications/Finance.app.\n\n"
                    "יש להפעיל מחדש את האפליקציה.",
                )
                try:
                    subprocess.Popen(["open", "-n", "/Applications/Finance.app"])
                except Exception:
                    pass
                try:
                    from ..qt import QApplication
                    QApplication.quit()
                except Exception:
                    pass

            QTimer.singleShot(0, self, _after_dl)

        try:
            threading.Thread(target=_dl_worker, daemon=True).start()
        except Exception:
            _dl_worker()
