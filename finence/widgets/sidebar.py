from __future__ import annotations

from typing import Callable, List, Optional, Dict, Any

from ..qt import Qt, QVBoxLayout, QWidget, QTimer
from ..models.accounts import MoneyAccount
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore

from .sidebar_avatar import SidebarAvatar
from .sidebar_navigation import SidebarNavigation
from .collapsible_section import CollapsibleButtonList
from .sidebar_scroll_area import SidebarScrollArea
from .sidebar_state import SidebarState
from .sidebar_controller import SidebarController


class Sidebar(QWidget):
    def __init__(
        self,
        user: UserProfile,
        store: UserProfileStore,
        parent: Optional[QWidget] = None,
        app_context: Optional[Dict[str, Any]] = None,
        navigate: Optional[Callable[[str], None]] = None,
        current_route: Optional[str] = None,
        accounts: Optional[List[MoneyAccount]] = None,
        selected_savings_account: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._user = user
        self._store = store
        self._navigate = navigate
        self._current_route = current_route
        self._app_context = app_context
        self._accounts = accounts or []
        self._selected_savings_account = selected_savings_account
        self._setup_sidebar()
        self._state = SidebarState(self._app_context)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 16, 0, 16)
        root_layout.setSpacing(0)
        self._scroll = SidebarScrollArea(self)
        root_layout.addWidget(self._scroll.scroll, 1)
        layout = self._scroll.layout
        content_parent = self._scroll.content

        self._avatar = SidebarAvatar(content_parent, user, store, layout)
        self._navigation = SidebarNavigation(
            content_parent, layout, navigate, current_route
        )

        self._bank_section = CollapsibleButtonList(
            content_parent,
            title="חשבונות",
            header_object_name="SidebarNavButton",
            header_tooltip="חשבונות בנק",
        )
        self._bank_section.set_arrow_visible(False)
        self._bank_section.set_expanded(False)

        self._savings_section = CollapsibleButtonList(
            content_parent,
            title="חסכונות",
            header_object_name="SidebarNavButtonSavings",
            header_tooltip="חסכונות",
        )
        self._savings_section.set_arrow_visible(False)
        self._savings_section.set_expanded(False)

        bank_container = getattr(self._navigation, "get_bank_container", lambda: None)()
        savings_container = self._navigation.get_savings_container()

        if bank_container is not None:
            try:
                idx_bank = layout.indexOf(bank_container)
                if idx_bank != -1:
                    layout.insertWidget(idx_bank, self._bank_section)
                else:
                    layout.addWidget(self._bank_section)
            except Exception:
                layout.addWidget(self._bank_section)
            try:
                layout.removeWidget(bank_container)
                bank_container.setVisible(False)
                bank_container.setParent(None)
                bank_container.deleteLater()
            except Exception:
                pass
            try:
                bank_btn = getattr(self._navigation, "get_bank_button", lambda: None)()
                if bank_btn is not None:
                    bank_btn.setVisible(False)
                    bank_btn.setEnabled(False)
            except Exception:
                pass
        else:
            layout.addWidget(self._bank_section)

        if savings_container is not None:
            try:
                idx_sav = layout.indexOf(savings_container)
                if idx_sav != -1:
                    layout.insertWidget(idx_sav, self._savings_section)
                else:
                    layout.addWidget(self._savings_section)
            except Exception:
                layout.addWidget(self._savings_section)
            try:
                layout.removeWidget(savings_container)
                savings_container.setVisible(False)
                savings_container.setParent(None)
                savings_container.deleteLater()
            except Exception:
                pass
            try:
                savings_btn = getattr(
                    self._navigation, "get_savings_button", lambda: None
                )()
                if savings_btn is not None:
                    savings_btn.setVisible(False)
                    savings_btn.setEnabled(False)
            except Exception:
                pass
        else:
            layout.addWidget(self._savings_section)

        self._yearly_summary_section = CollapsibleButtonList(
            content_parent,
            title="סיכום שנתי",
            header_object_name="SidebarNavButton",
            header_tooltip="סיכום שנתי",
        )
        self._yearly_summary_section.set_arrow_visible(False)
        self._yearly_summary_section.set_expanded(False)
        try:
            nav = self._navigate
            if nav is not None:
                self._yearly_summary_section.set_items(
                    [
                        ("סיכום ע״פ קטגוריות", lambda: nav("yearly_category_trends")),
                        ("פירוט שנה", lambda: nav("yearly_data")),
                    ]
                )
        except Exception:
            pass

        yearly_container = (
            self._navigation.get_yearly_summary_container()
            if hasattr(self._navigation, "get_yearly_summary_container")
            else None
        )
        if yearly_container is not None:
            try:
                idx_yearly = layout.indexOf(yearly_container)
                if idx_yearly != -1:
                    layout.insertWidget(idx_yearly, self._yearly_summary_section)
                else:
                    layout.addWidget(self._yearly_summary_section)
            except Exception:
                layout.addWidget(self._yearly_summary_section)
            try:
                layout.removeWidget(yearly_container)
                yearly_container.setVisible(False)
                yearly_container.setParent(None)
                yearly_container.deleteLater()
            except Exception:
                pass
            try:
                yearly_btn = getattr(
                    self._navigation, "get_yearly_summary_button", lambda: None
                )()
                if yearly_btn is not None:
                    yearly_btn.setVisible(False)
                    yearly_btn.setEnabled(False)
            except Exception:
                pass
        else:
            layout.addWidget(self._yearly_summary_section)

        layout.addStretch(1)

        self._controller = SidebarController(
            widget=self,
            state=self._state,
            scroll=self._scroll,
            navigation=self._navigation,
            bank_section=self._bank_section,
            savings_section=self._savings_section,
            yearly_section=self._yearly_summary_section,
            navigate=self._navigate,
            current_route=self._current_route,
            accounts=self._accounts,
        )
        self._controller.update_accounts(self._accounts)
        self._controller.update_route(current_route)
        try:
            QTimer.singleShot(0, self._update_button_width)
        except Exception:
            self._update_button_width()

    def _setup_sidebar(self) -> None:
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        self._controller.on_resize()

    def showEvent(self, event) -> None:
        try:
            super().showEvent(event)
        except Exception:
            pass
        self._controller.on_show()

    def changeEvent(self, event) -> None:
        try:
            super().changeEvent(event)
        except Exception:
            pass
        self._controller.on_style_change(event)

    def _update_button_width(self) -> None:
        self._controller.on_resize()

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._controller.update_accounts(accounts)

    def update_route(self, route: Optional[str]) -> None:
        self._controller.update_route(route)

    def refresh_profile(self) -> None:
        self._avatar.refresh()
