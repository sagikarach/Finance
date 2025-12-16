from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import Qt, QVBoxLayout, QWidget
from ..models.accounts import BankAccount, MoneyAccount, SavingsAccount
from ..models.sidebar import SidebarSectionState
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore

from .sidebar_avatar import SidebarAvatar
from .sidebar_navigation import SidebarNavigation
from .collapsible_section import CollapsibleButtonList
from .sidebar_styling import apply_toggle_button_style
from .sidebar_positioning import (
    update_bank_button_width,
    update_dashboard_button_width,
    update_monthly_data_button_width,
    update_savings_accounts_container_width,
    update_savings_button_width,
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
        selected_savings_account: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._user = user
        self._store = store
        self._navigate = navigate
        self._current_route = current_route
        self._accounts = accounts or []
        self._selected_savings_account = selected_savings_account
        self._setup_sidebar()
        layout = self._create_layout()
        self._avatar = SidebarAvatar(self, user, store, layout)
        self._navigation = SidebarNavigation(self, layout, navigate, current_route)

        self._bank_section = CollapsibleButtonList(
            self,
            title="חשבונות",
            header_object_name="SidebarNavButton",
            header_tooltip="חשבונות בנק",
        )
        try:
            self._bank_section.set_header_visible(False)
            self._bank_section.set_expanded(False)
        except Exception:
            pass

        self._savings_section = CollapsibleButtonList(
            self,
            title="חסכונות",
            header_object_name="SidebarNavButtonSavings",
            header_tooltip="חסכונות",
        )
        try:
            self._savings_section.set_header_visible(False)
        except Exception:
            pass

        bank_container = getattr(self._navigation, "get_bank_container", lambda: None)()
        savings_container = self._navigation.get_savings_container()

        if bank_container is not None:
            try:
                idx_bank = layout.indexOf(bank_container)
                if idx_bank != -1:
                    layout.insertWidget(idx_bank + 1, self._bank_section)
                else:
                    layout.addWidget(self._bank_section)
            except Exception:
                layout.addWidget(self._bank_section)
        else:
            layout.addWidget(self._bank_section)

        if savings_container is not None:
            try:
                idx_sav = layout.indexOf(savings_container)
                if idx_sav != -1:
                    layout.insertWidget(idx_sav + 1, self._savings_section)
                else:
                    layout.addWidget(self._savings_section)
            except Exception:
                layout.addWidget(self._savings_section)
        else:
            layout.addWidget(self._savings_section)

        layout.addStretch(1)

        self._rebuild_bank_items()
        self._rebuild_savings_items()

        self._connect_handlers()
        self._setup_event_handlers()
        self.update_route(current_route)

        if current_route in ("savings", "savings_account"):
            try:
                self._savings_section.set_expanded(True)
                toggle_btn = self._navigation.get_savings_toggle_button()
                if toggle_btn:
                    toggle_btn.setChecked(True)
                    toggle_btn.setText("▲")
            except Exception:
                pass

        if current_route in ("bank_accounts", "bank_account"):
            try:
                self._bank_section.set_expanded(True)
                toggle_btn = self._navigation.get_bank_toggle_button()
                if toggle_btn:
                    toggle_btn.setChecked(True)
                    toggle_btn.setText("▲")
                bank_btn = self._navigation.get_bank_button()
                if bank_btn:
                    bank_btn.setStyleSheet("border-bottom-color: transparent;")
            except Exception:
                pass

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
        if hasattr(self._navigation, "connect_bank_handlers"):
            try:
                self._navigation.connect_bank_handlers(
                    on_toggle=self._on_toggle_bank_list,
                    on_bank_click=self._on_bank_clicked,
                )
            except Exception:
                pass

    def _on_toggle_savings_list(self) -> None:
        if not hasattr(self, "_savings_section"):
            return

        toggle_btn = self._navigation.get_savings_toggle_button()

        is_expanded = False
        try:
            currently = self._savings_section.is_expanded()
            self._savings_section.set_expanded(not currently)
            is_expanded = self._savings_section.is_expanded()
        except Exception:
            return

        if toggle_btn:
            toggle_btn.setChecked(is_expanded)
            toggle_btn.setText("▲" if is_expanded else "▼")

        self._apply_toggle_button_style()
        self._update_button_width()

    def _on_savings_clicked(self) -> None:
        if self._navigate is not None:
            self._navigate("savings")

    def _on_bank_clicked(self) -> None:
        if self._navigate is not None:
            self._navigate("bank_accounts")
        try:
            if not self._bank_section.is_expanded():
                self._on_toggle_bank_list()
        except Exception:
            pass

    def _on_toggle_bank_list(self) -> None:
        if not hasattr(self, "_bank_section"):
            return

        toggle_btn = (
            self._navigation.get_bank_toggle_button()
            if hasattr(self._navigation, "get_bank_toggle_button")
            else None
        )
        bank_btn = (
            self._navigation.get_bank_button()
            if hasattr(self._navigation, "get_bank_button")
            else None
        )

        is_expanded = False
        try:
            currently = self._bank_section.is_expanded()
            self._bank_section.set_expanded(not currently)
            is_expanded = self._bank_section.is_expanded()
        except Exception:
            return

        if bank_btn:
            bank_btn.setStyleSheet(
                "border-bottom-color: transparent;" if is_expanded else ""
            )

        if toggle_btn:
            toggle_btn.setChecked(is_expanded)
            toggle_btn.setText("▲" if is_expanded else "▼")

        self._update_button_width()

    def _on_savings_account_clicked(self, account: MoneyAccount) -> None:
        if self._navigate is None:
            return

        parent = self.parent()
        while parent is not None and not hasattr(
            parent, "set_selected_savings_account"
        ):
            parent = parent.parent()

        if parent is not None and hasattr(parent, "set_selected_savings_account"):
            try:
                parent.set_selected_savings_account(account.name)
            except Exception:
                pass

        self._navigate("savings_account")

    def _on_bank_account_clicked(self, account: MoneyAccount) -> None:
        if self._navigate is None:
            return

        parent = self.parent()
        while parent is not None and not hasattr(parent, "set_selected_bank_account"):
            parent = parent.parent()

        if parent is not None and hasattr(parent, "set_selected_bank_account"):
            try:
                parent.set_selected_bank_account(account.name)
            except Exception:
                pass

        self._navigate("bank_account")

    def _apply_toggle_button_style(self) -> None:
        toggle_btn = self._navigation.get_savings_toggle_button()
        savings_btn = self._navigation.get_savings_button()
        if toggle_btn and savings_btn:
            apply_toggle_button_style(
                toggle_btn,
                savings_btn,
                bool(
                    hasattr(self, "_savings_section")
                    and self._savings_section.is_expanded()
                ),
            )

    def _setup_event_handlers(self) -> None:
        self._setup_resize_handler()
        self._setup_show_handler()
        self._setup_change_handler()

    def _setup_resize_handler(self) -> None:
        original_resize = self.resizeEvent

        def resizeEvent(event):
            if original_resize is not None:
                try:
                    original_resize(event)
                except Exception:
                    pass
            try:
                from PySide6.QtCore import QTimer

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

        def showEvent(event):
            if original_show is not None:
                try:
                    original_show(event)
                except Exception:
                    pass
            if hasattr(self, "_current_route"):
                self.update_route(self._current_route)
            try:
                from PySide6.QtCore import QTimer

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

        def changeEvent(event):
            if original_change is not None:
                try:
                    original_change(event)
                except Exception:
                    pass
            try:
                from PySide6.QtCore import QEvent, QTimer

                if event.type() == QEvent.Type.StyleChange:
                    QTimer.singleShot(50, self._update_button_width)
                    self._apply_toggle_button_style()
                    self._refresh_collapsible_sections()
            except Exception:
                try:
                    from PyQt6.QtCore import QEvent, QTimer  # type: ignore

                    if event.type() == QEvent.Type.StyleChange:
                        QTimer.singleShot(50, self._update_button_width)
                        self._apply_toggle_button_style()
                        self._refresh_collapsible_sections()
                except Exception:
                    pass

        self.changeEvent = changeEvent  # type: ignore[assignment]

    def _refresh_collapsible_sections(self) -> None:
        if hasattr(self, "_savings_section"):
            try:
                self._savings_section.refresh_theme()
            except Exception:
                pass
        if hasattr(self, "_bank_section"):
            try:
                self._bank_section.refresh_theme()
            except Exception:
                pass

    def _update_button_width(self) -> None:
        sidebar_width = self.width()

        update_dashboard_button_width(
            self,
            sidebar_width,
            self._navigation.get_dashboard_container(),
            self._navigation.get_dashboard_button(),
        )

        update_bank_button_width(
            self,
            sidebar_width,
            getattr(self._navigation, "get_bank_container", lambda: None)(),
            getattr(self._navigation, "get_bank_button", lambda: None)(),
            getattr(self._navigation, "get_bank_toggle_button", lambda: None)(),
        )

        update_savings_button_width(
            self,
            sidebar_width,
            self._navigation.get_savings_container(),
            self._navigation.get_savings_button(),
            self._navigation.get_savings_toggle_button(),
        )

        update_monthly_data_button_width(
            self,
            sidebar_width,
            getattr(self._navigation, "get_monthly_data_container", lambda: None)(),
            getattr(self._navigation, "get_monthly_data_button", lambda: None)(),
        )

        update_savings_accounts_container_width(
            self,
            sidebar_width,
            getattr(self._savings_section, "_content", None),
        )

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        self._rebuild_bank_items()
        self._rebuild_savings_items()
        try:
            from PySide6.QtCore import QTimer

            QTimer.singleShot(10, self._update_button_width)
        except Exception:
            try:
                from PyQt6.QtCore import QTimer  # type: ignore

                QTimer.singleShot(10, self._update_button_width)
            except Exception:
                self._update_button_width()
        try:
            self.updateGeometry()
            self.update()
            self.repaint()
        except Exception:
            pass

    def refresh_profile(self) -> None:
        self._avatar.refresh()

    def update_route(self, route: Optional[str]) -> None:
        dashboard_btn = self._navigation.get_dashboard_button()
        if not dashboard_btn:
            return

        is_home = route == "home"
        is_bank = route == "bank_accounts"
        is_bank_section = route in ("bank_accounts", "bank_account")
        is_savings = route == "savings"
        is_savings_section = route in ("savings", "savings_account")
        is_monthly_data = route == "monthly_data"

        dashboard_btn.blockSignals(True)
        dashboard_btn.setChecked(is_home)
        dashboard_btn.setEnabled(not is_home)
        dashboard_btn.blockSignals(False)

        bank_btn = (
            self._navigation.get_bank_button()
            if hasattr(self._navigation, "get_bank_button")
            else None
        )
        if bank_btn:
            bank_btn.blockSignals(True)
            bank_btn.setChecked(is_bank_section)
            bank_btn.setEnabled(not is_bank)
            bank_btn.blockSignals(False)

        bank_toggle_btn = (
            self._navigation.get_bank_toggle_button()
            if hasattr(self._navigation, "get_bank_toggle_button")
            else None
        )
        if hasattr(self, "_bank_section"):
            if is_bank_section:
                is_expanded = False
                try:
                    is_expanded = self._bank_section.is_expanded()
                except Exception:
                    is_expanded = False

                if bank_btn:
                    if is_expanded:
                        bank_btn.setStyleSheet("border-bottom-color: transparent;")
                    else:
                        bank_btn.setStyleSheet("")
                if bank_toggle_btn:
                    bank_toggle_btn.setVisible(True)
                    bank_toggle_btn.setChecked(is_expanded)
                    bank_toggle_btn.setText("▲" if is_expanded else "▼")
            else:
                try:
                    self._bank_section.set_expanded(False)
                except Exception:
                    pass
                if bank_toggle_btn:
                    bank_toggle_btn.setVisible(False)
                    bank_toggle_btn.setChecked(False)
                    bank_toggle_btn.setText("▼")

        monthly_data_btn = (
            self._navigation.get_monthly_data_button()
            if hasattr(self._navigation, "get_monthly_data_button")
            else None
        )
        if monthly_data_btn:
            monthly_data_btn.blockSignals(True)
            monthly_data_btn.setChecked(is_monthly_data)
            monthly_data_btn.setEnabled(not is_monthly_data)
            monthly_data_btn.blockSignals(False)

        savings_btn = self._navigation.get_savings_button()
        if savings_btn:
            savings_btn.blockSignals(True)
            savings_btn.setChecked(is_savings_section)
            savings_btn.setEnabled(not is_savings)
            savings_btn.blockSignals(False)
            self._update_button_width()

        toggle_btn = self._navigation.get_savings_toggle_button()
        if toggle_btn:
            toggle_btn.setVisible(is_savings_section)
            if not is_savings_section:
                if hasattr(self, "_savings_section"):
                    try:
                        self._savings_section.set_expanded(False)
                    except Exception:
                        pass
                toggle_btn.setChecked(False)
                toggle_btn.setText("▼")
            self._apply_toggle_button_style()

        if hasattr(self, "_savings_section"):
            try:
                self._savings_section.setVisible(is_savings_section)
            except Exception:
                pass

        self._current_route = route

    def _build_section_state(
        self,
        section_id: str,
        title: str,
        account_type: type,
        expanded: bool,
        click_handler: Callable[[MoneyAccount], None],
        account_filter: Optional[Callable[[MoneyAccount], bool]] = None,
    ) -> SidebarSectionState:
        section = SidebarSectionState(
            section_id=section_id,
            title=title,
            expanded=expanded,
        )

        for acc in self._accounts:
            if not isinstance(acc, account_type):
                continue
            if account_filter is not None and not account_filter(acc):
                continue

            def make_cb(account: MoneyAccount) -> Callable[[], None]:
                def _cb() -> None:
                    click_handler(account)

                return _cb

            section.add_item(label=acc.name, on_click=make_cb(acc))

        return section

    def _rebuild_bank_items(self) -> None:
        if not hasattr(self, "_bank_section"):
            return

        expanded = False
        try:
            expanded = bool(self._bank_section.is_expanded())
        except Exception:
            expanded = False

        section = self._build_section_state(
            section_id="bank_accounts",
            title="חשבונות",
            account_type=BankAccount,
            expanded=expanded,
            click_handler=self._on_bank_account_clicked,
            account_filter=lambda a: isinstance(a, BankAccount) and a.active,
        )

        try:
            layout = self.layout()
            bank_container = getattr(
                self._navigation, "get_bank_container", lambda: None
            )()
            if (
                layout is not None
                and isinstance(layout, QVBoxLayout)
                and bank_container is not None
            ):
                try:
                    idx_bank = layout.indexOf(bank_container)
                    if idx_bank != -1:
                        idx_current = layout.indexOf(self._bank_section)
                    else:
                        idx_current = -1
                except Exception:
                    idx_current = -1

                if idx_current == -1 and idx_bank != -1:
                    layout.insertWidget(idx_bank + 1, self._bank_section)
                    if hasattr(self._bank_section, "_layout_index"):
                        self._bank_section._layout_index = idx_bank + 1
        except Exception:
            pass

        try:
            self._bank_section.set_items(section.as_collapsible_items())
            self._bank_section.set_expanded(section.expanded)
        except Exception:
            pass

    def _rebuild_savings_items(self) -> None:
        if not hasattr(self, "_savings_section"):
            return

        expanded = False
        try:
            expanded = bool(self._savings_section.is_expanded())
        except Exception:
            expanded = False

        section = self._build_section_state(
            section_id="savings_accounts",
            title="חסכונות",
            account_type=SavingsAccount,
            expanded=expanded,
            click_handler=self._on_savings_account_clicked,
        )

        try:
            self._savings_section.set_items(section.as_collapsible_items())
            self._savings_section.set_expanded(section.expanded)
        except Exception:
            pass
