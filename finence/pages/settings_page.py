from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QHBoxLayout,
    QListWidget,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..data.provider import AccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts_service import AccountsService
from ..__version__ import __version__
from .base_page import BasePage
from ..models.firebase_session import FirebaseSessionStore
from .settings_sections import (
    BankAccountsCard,
    FirebaseSyncCard,
    NotificationsCard,
    UpdatesCard,
    UserDetailsCard,
)


class SettingsPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
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
        self._update_eye_icon: Optional[Callable[[], None]] = None
        self._user_card: Optional[UserDetailsCard] = None
        self._get_previous_route = get_previous_route
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons = []
        back_btn = QToolButton(self)
        back_btn.setObjectName("IconButton")
        back_btn.setText("←")
        back_btn.setToolTip("חזרה")
        if self._navigate is not None:

            def go_back():
                previous = "home"
                if self._get_previous_route is not None:
                    previous = self._get_previous_route()
                self._navigate(previous)

            back_btn.clicked.connect(go_back)
        buttons.append(back_btn)
        return buttons

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if self._update_eye_icon is not None:
            self._update_eye_icon()

    def _build_content(self, main_col: QVBoxLayout) -> None:
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
        self._update_eye_icon = self._user_card.update_eye_icon

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
        updates_card = UpdatesCard(parent=self, app_version=__version__)

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
        menu.addItem("עדכונים")

        stack = QStackedWidget(container)

        def _wrap_page(child: QWidget) -> QWidget:
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

        stack.addWidget(_wrap_page(self._user_card))
        stack.addWidget(_wrap_page(bank_accounts_card))
        stack.addWidget(_wrap_page(notifications_card))
        stack.addWidget(_wrap_page(firebase_card))
        stack.addWidget(_wrap_page(updates_card))

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
