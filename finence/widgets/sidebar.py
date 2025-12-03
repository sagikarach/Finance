from __future__ import annotations

from typing import Optional, Callable, List

from ..qt import QWidget, QVBoxLayout, Qt
from ..models.user import UserProfile
from ..models.accounts import MoneyAccount
from ..data.user_profile_store import UserProfileStore

from .sidebar_avatar import SidebarAvatar
from .sidebar_navigation import SidebarNavigation
from .sidebar_savings_list import SidebarSavingsList
from .sidebar_styling import apply_toggle_button_style
from .sidebar_positioning import (
    update_dashboard_button_width,
    update_savings_button_width,
    update_savings_accounts_container_width,
)


class Sidebar(QWidget):

    def __init__(
        self,
        user: UserProfile,
        store: UserProfileStore,
        parent: Optional[QWidget] = None,
        navigate: Optional[Callable[[str], None]] = None,
        current_route: Optional[str] = None,
        accounts: Optional[List[MoneyAccount]] = None,
    ) -> None:
        super().__init__(parent)
        self._user = user
        self._store = store
        self._navigate = navigate
        self._current_route = current_route
        self._accounts = accounts or []
        self._setup_sidebar()
        layout = self._create_layout()
        self._avatar = SidebarAvatar(self, user, store, layout)
        self._navigation = SidebarNavigation(self, layout, navigate, current_route)
        self._savings_list = SidebarSavingsList(self, layout, accounts or [], navigate)
        self._connect_handlers()
        self._setup_event_handlers()
        self.update_route(current_route)

    def _setup_sidebar(self) -> None:
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

    def _create_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)
        return layout

    def _connect_handlers(self) -> None:
        self._navigation.connect_savings_handlers(
            on_toggle=self._on_toggle_savings_list,
            on_savings_click=self._on_savings_clicked,
            on_toggle_style=self._apply_toggle_button_style,
        )

    def _on_toggle_savings_list(self) -> None:
        was_expanded = self._savings_list.is_expanded()

        is_expanded = self._savings_list.toggle()
        toggle_btn = self._navigation.get_savings_toggle_button()
        if toggle_btn:
            toggle_btn.setChecked(is_expanded)
            toggle_btn.setText("▲" if is_expanded else "▼")

        if is_expanded:
            self._apply_toggle_button_style()
        else:
            if was_expanded:
                pass

            try:
                from PySide6.QtCore import QTimer  # type: ignore
                QTimer.singleShot(320, self._apply_toggle_button_style)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore
                    QTimer.singleShot(320, self._apply_toggle_button_style)
                except Exception:
                    self._apply_toggle_button_style()

        # Update geometry
        self._update_button_width()

    def _on_savings_clicked(self) -> None:
        if self._navigate is not None:
            self._navigate("savings")  # type: ignore[arg-type]

    def _apply_toggle_button_style(self) -> None:
        toggle_btn = self._navigation.get_savings_toggle_button()
        savings_btn = self._navigation.get_savings_button()
        if toggle_btn and savings_btn:
            apply_toggle_button_style(
                toggle_btn,
                savings_btn,
                self._savings_list.is_expanded(),
            )

    def _setup_event_handlers(self) -> None:
        self._setup_resize_handler()
        self._setup_show_handler()
        self._setup_change_handler()

    def _setup_resize_handler(self) -> None:
        original_resize = self.resizeEvent

        def resizeEvent(event):  # type: ignore
            if original_resize is not None:
                try:
                    original_resize(event)
                except Exception:
                    pass
            try:
                from PySide6.QtCore import QTimer  # type: ignore
                QTimer.singleShot(10, self._update_button_width)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore
                    QTimer.singleShot(10, self._update_button_width)
                except Exception:
                    self._update_button_width()

        self.resizeEvent = resizeEvent  # type: ignore[assignment]

    def _setup_show_handler(self) -> None:
        original_show = self.showEvent

        def showEvent(event):  # type: ignore
            if original_show is not None:
                try:
                    original_show(event)
                except Exception:
                    pass
            if hasattr(self, "_current_route"):
                self.update_route(self._current_route)
            try:
                from PySide6.QtCore import QTimer  # type: ignore
                QTimer.singleShot(10, self._update_button_width)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore
                    QTimer.singleShot(10, self._update_button_width)
                except Exception:
                    self._update_button_width()

        self.showEvent = showEvent  # type: ignore[assignment]

    def _setup_change_handler(self) -> None:
        original_change = self.changeEvent

        def changeEvent(event):  # type: ignore
            if original_change is not None:
                try:
                    original_change(event)
                except Exception:
                    pass
            try:
                from PySide6.QtCore import QEvent, QTimer  # type: ignore
                if event.type() == QEvent.Type.StyleChange:  # type: ignore
                    QTimer.singleShot(50, self._update_button_width)
                    self._apply_toggle_button_style()
            except Exception:
                try:
                    from PyQt6.QtCore import QEvent, QTimer  # type: ignore
                    if event.type() == QEvent.Type.StyleChange:  # type: ignore
                        QTimer.singleShot(50, self._update_button_width)
                        self._apply_toggle_button_style()
                except Exception:
                    pass

        self.changeEvent = changeEvent  # type: ignore[assignment]

    def _update_button_width(self) -> None:
        sidebar_width = self.width()

        update_dashboard_button_width(
            self,
            sidebar_width,
            self._navigation.get_dashboard_container(),
            self._navigation.get_dashboard_button(),
        )

        update_savings_button_width(
            self,
            sidebar_width,
            self._navigation.get_savings_container(),
            self._navigation.get_savings_button(),
            self._navigation.get_savings_toggle_button(),
        )

        update_savings_accounts_container_width(
            self,
            sidebar_width,
            self._savings_list.get_container(),
        )

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        self._savings_list.update_accounts(accounts)

    def refresh_profile(self) -> None:
        self._avatar.refresh()

    def update_route(self, route: Optional[str]) -> None:
        dashboard_btn = self._navigation.get_dashboard_button()
        if not dashboard_btn:
            return

        is_home = route == "home"
        is_savings = route == "savings"

        dashboard_btn.blockSignals(True)
        dashboard_btn.setChecked(is_home)
        dashboard_btn.setEnabled(not is_home)
        dashboard_btn.blockSignals(False)

        savings_btn = self._navigation.get_savings_button()
        if savings_btn:
            savings_btn.blockSignals(True)
            savings_btn.setChecked(is_savings)
            savings_btn.setEnabled(not is_savings)
            savings_btn.blockSignals(False)
            self._update_button_width()

        toggle_btn = self._navigation.get_savings_toggle_button()
        if toggle_btn:
            toggle_btn.setVisible(is_savings)
            if not is_savings:
                self._savings_list.set_expanded(False)
                toggle_btn.setChecked(False)
                toggle_btn.setText("▼")
                self._savings_list.update_visibility()
            self._apply_toggle_button_style()

            if is_savings:
                def position_toggle() -> None:
                    savings_container = self._navigation.get_savings_container()
                    if savings_container and savings_container.isVisible():
                        savings_rect = savings_container.geometry()
                        if savings_rect.height() > 0:
                            toggle_btn.setGeometry(
                                0, savings_rect.y(), 32, savings_rect.height()
                            )
                            try:
                                toggle_btn.raise_()
                            except Exception:
                                pass

                try:
                    from PySide6.QtCore import QTimer  # type: ignore
                    QTimer.singleShot(10, position_toggle)
                except Exception:
                    try:
                        from PyQt6.QtCore import QTimer  # type: ignore
                        QTimer.singleShot(10, position_toggle)
                    except Exception:
                        pass

        self._current_route = route
