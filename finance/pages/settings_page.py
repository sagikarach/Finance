from __future__ import annotations

from typing import Callable, Dict, List, Optional, Any

import sys
import threading
import pathlib

from ..qt import (
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
    QMessageBox,
    QTimer,
)
from ..data.provider import AccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts_service import AccountsService
from .base_page import BasePage
from ..models.firebase_session import FirebaseSessionStore
from .settings_sections import (
    BankAccountsCard,
    FirebaseSyncCard,
    NotificationsCard,
    UserDetailsCard,
)
from ..utils.defaults import load_defaults
from ..utils.updater import check_version_only, download_and_install_update, install_app_to_applications


class SettingsPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[Any] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        get_previous_route: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="הגדרות",
            current_route="settings",
        )
        self._user_card: Optional[UserDetailsCard] = None
        self._get_previous_route = get_previous_route
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[Any]:
        buttons = []
        back_btn = QToolButton(self)
        back_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(back_btn, "arrow_left", size=20, is_dark=self._is_dark_theme())
        except Exception:
            back_btn.setText("←")
        back_btn.setToolTip("חזרה")
        if self._navigate is not None:

            def go_back():
                previous = "home"
                nav = self._navigate
                prev_cb = self._get_previous_route
                if callable(prev_cb):
                    previous = prev_cb()
                if callable(nav):
                    nav(previous)

            back_btn.clicked.connect(go_back)
        buttons.append(back_btn)
        return buttons

    def on_route_activated(self) -> None:
        super().on_route_activated()
        # After switching Firebase users/workspaces, reload profile + accounts
        # from local caches that were just pulled from Firebase.
        try:
            self._accounts = self._provider.list_accounts()
        except Exception:
            pass
        try:
            defaults = load_defaults()
            default_name = self._app_context.get("userName") or defaults.get(
                "default_full_name", "אורח"
            )
            self._user = self._user_store.load(
                default_full_name=default_name, accounts=self._accounts
            )
        except Exception:
            pass
        try:
            if self._content_col is not None:
                self._build_content(self._content_col)
        except Exception:
            pass
        try:
            if self._sidebar is not None:
                self._sidebar.refresh_profile()
        except Exception:
            pass

    def _build_content(self, main_col: Any) -> None:
        self._clear_content_layout(main_col)

        def on_profile_saved() -> None:
            try:
                if self._sidebar is not None:
                    self._sidebar.refresh_profile()
            except Exception:
                pass

        self._user_card = UserDetailsCard(
            parent=self,
            user=self._user,
            user_store=self._user_store,
            on_profile_saved=on_profile_saved,
        )

        def on_accounts_saved() -> None:
            try:
                self._accounts = self._provider.list_accounts()
            except Exception:
                pass

        bank_accounts_card = BankAccountsCard(
            parent=self,
            provider=self._provider,
            accounts_service=self._accounts_service,
            on_after_save=on_accounts_saved,
            sidebar=self._sidebar,
        )
        notifications_card = NotificationsCard(
            parent=self,
            notifications_service=self._notifications_service,
            on_refreshed=getattr(self, "_refresh_notifications_badge", None),
        )
        firebase_card = FirebaseSyncCard(parent=self, store=FirebaseSessionStore())

        container = QWidget(self)
        try:
            container.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                container.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass

        container_l = QHBoxLayout(container)
        container_l.setContentsMargins(0, 0, 0, 0)
        container_l.setSpacing(16)

        menu = QListWidget(container)
        menu.setObjectName("SettingsMenu")
        try:
            menu.setFixedWidth(210)
        except Exception:
            pass
        try:
            menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                menu.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        menu.addItem("כללי")
        menu.addItem("חשבונות")
        menu.addItem("התראות")
        menu.addItem("שיתוף וסנכרון")

        stack = QStackedWidget(container)

        def _wrap_page(child: Any) -> Any:
            page = QWidget(stack)
            try:
                page.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    page.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            lay = QVBoxLayout(page)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(16)
            lay.addWidget(child, 0)
            lay.addStretch(1)
            return page

        def _build_general_page() -> Any:
            container = QWidget(stack)
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(8)

            update_btn = QToolButton(container)
            update_btn.setText("בדיקת עדכונים (macOS)")
            update_btn.setToolTip("בודק אם יש גרסה חדשה להורדה (macOS בלבד)")

            def _do_check() -> None:
                if sys.platform != "darwin":
                    QMessageBox.information(
                        container, "עדכונים",
                        "בדיקת עדכונים נתמכת רק ב-macOS.",
                    )
                    return

                from ..qt import QProgressDialog  # type: ignore[attr-defined]
                progress = QProgressDialog("בודק עדכונים...", None, 0, 0, container)
                progress.setWindowTitle("עדכון")
                progress.setMinimumDuration(0)
                progress.setWindowModality(2)
                progress.setValue(0)
                progress.show()

                def _check_worker() -> None:
                    is_newer, latest, zip_url_sig, error = False, "", None, None
                    try:
                        is_newer, latest, zip_url_sig, error = check_version_only()
                    except Exception as exc:
                        error = str(exc)

                    def _after_check() -> None:
                        try:
                            progress.close()
                        except Exception:
                            pass
                        if error:
                            QMessageBox.warning(container, "עדכון", f"בדיקת עדכון נכשלה:\n{error}")
                            return
                        from ..__version__ import __version__
                        if not is_newer:
                            QMessageBox.information(
                                container, "עדכון",
                                f"הגרסה הנוכחית ({__version__}) היא העדכנית ביותר." if latest
                                else "לא נמצאה גרסה חדשה יותר.",
                            )
                            return
                        answer = QMessageBox.question(
                            container, "עדכון זמין",
                            f"גרסה חדשה {latest} זמינה (הגרסה שלך: {__version__}).\n\n"
                            "האם להוריד ולהתקין עכשיו?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        )
                        if answer != QMessageBox.StandardButton.Yes:
                            return
                        if not zip_url_sig:
                            QMessageBox.warning(
                                container, "עדכון",
                                f"גרסה {latest} זמינה אך לא ניתן להוריד אוטומטית.\n"
                                "יש להוריד ידנית מ-GitHub.",
                            )
                            return
                        _start_download(latest, zip_url_sig)

                    try:
                        from ..qt import QApplication
                        QTimer.singleShot(0, QApplication.instance(), _after_check)
                    except Exception:
                        _after_check()

                def _start_download(version: str, zip_url_sig: str) -> None:
                    dl_progress = QProgressDialog(f"מוריד גרסה {version}...", None, 0, 0, container)
                    dl_progress.setWindowTitle("עדכון")
                    dl_progress.setMinimumDuration(0)
                    dl_progress.setWindowModality(2)
                    dl_progress.setValue(0)
                    dl_progress.show()

                    def _dl_worker() -> None:
                        app_path, dl_err = download_and_install_update(zip_url_sig)

                        def _after_dl() -> None:
                            try:
                                dl_progress.close()
                            except Exception:
                                pass
                            if dl_err or app_path is None:
                                QMessageBox.warning(
                                    container, "עדכון",
                                    f"הורדת העדכון נכשלה:\n{dl_err or 'Finance.app לא נמצא'}",
                                )
                                return
                            answer = QMessageBox.question(
                                container, "התקנת עדכון",
                                f"גרסה {version} הורדה בהצלחה.\n\n"
                                "להתקין ל-/Applications/Finance.app ולהפעיל מחדש?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                            )
                            if answer != QMessageBox.StandardButton.Yes:
                                QMessageBox.information(
                                    container, "עדכון",
                                    f"הקובץ נמצא ב:\n{app_path}\n\nגרור ל-/Applications/ ידנית.",
                                )
                                return
                            inst_err = install_app_to_applications(app_path)
                            if inst_err:
                                QMessageBox.warning(
                                    container, "עדכון",
                                    f"ההתקנה נכשלה:\n{inst_err}\n\nהעתק ידנית מ:\n{app_path}",
                                )
                                return
                            QMessageBox.information(
                                container, "עדכון הותקן",
                                f"גרסה {version} הותקנה.\nיש להפעיל מחדש את האפליקציה.",
                            )
                            try:
                                import subprocess
                                subprocess.Popen(["open", "-n", "/Applications/Finance.app"])
                            except Exception:
                                pass
                            try:
                                from ..qt import QApplication
                                QApplication.quit()
                            except Exception:
                                pass

                        try:
                            from ..qt import QApplication
                            QTimer.singleShot(0, QApplication.instance(), _after_dl)
                        except Exception:
                            _after_dl()

                    try:
                        threading.Thread(target=_dl_worker, daemon=True).start()
                    except Exception:
                        _dl_worker()

                try:
                    threading.Thread(target=_check_worker, daemon=True).start()
                except Exception:
                    _check_worker()

            update_btn.clicked.connect(_do_check)

            lay.addWidget(update_btn, 0)
            lay.addWidget(self._user_card, 0)
            lay.addStretch(1)
            return container

        stack.addWidget(_wrap_page(_build_general_page()))
        stack.addWidget(_wrap_page(bank_accounts_card))
        stack.addWidget(_wrap_page(notifications_card))
        stack.addWidget(_wrap_page(firebase_card))

        def _save_selected(idx: int) -> None:
            try:
                self._app_context["settings_section"] = str(int(idx))
            except Exception:
                pass

        menu.currentRowChanged.connect(stack.setCurrentIndex)
        menu.currentRowChanged.connect(_save_selected)

        initial = 0
        try:
            initial = int(str(self._app_context.get("settings_section", "0") or "0"))
        except Exception:
            initial = 0
        if initial < 0 or initial >= stack.count():
            initial = 0
        try:
            menu.setCurrentRow(initial)
        except Exception:
            pass

        container_l.addWidget(menu, 0)
        container_l.addWidget(stack, 1)

        main_col.addWidget(container, 1)
