from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import Qt, QVBoxLayout, QWidget
from ..models.accounts import BankAccount, MoneyAccount, SavingsAccount
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore

from .sidebar_avatar import SidebarAvatar
from .sidebar_navigation import SidebarNavigation
from .collapsible_section import CollapsibleButtonList
from .sidebar_styling import apply_toggle_button_style
from .sidebar_positioning import (
    update_bank_button_width,
    update_dashboard_button_width,
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

        # Collapsible section for bank accounts between 'חשבונות' and 'חסכונות'.
        self._bank_section = CollapsibleButtonList(
            self,
            title="חשבונות",
            header_object_name="SidebarNavButton",
            header_tooltip="חשבונות בנק",
        )
        # Hide the internal header; only rows are used. Then force a collapsed
        # recompute so this widget takes zero space when closed.
        try:
            self._bank_section.set_header_visible(False)  # type: ignore[attr-defined]
            # Ensure initial state is collapsed with no header, so there is no
            # visual gap between 'חשבונות' and 'חסכונות'.
            self._bank_section.set_expanded(False)  # type: ignore[attr-defined]
        except Exception:
            pass

        # Collapsible section for savings accounts list under 'חסכונות'.
        self._savings_section = CollapsibleButtonList(
            self,
            title="חסכונות",
            header_object_name="SidebarNavButtonSavings",
            header_tooltip="חסכונות",
        )
        try:
            # Use external header from SidebarNavigation; hide internal header.
            self._savings_section.set_header_visible(False)  # type: ignore[attr-defined]
        except Exception:
            pass

        # Insert bank section below bank button, and savings section below
        # savings button, so lists live directly under their headers.
        bank_container = getattr(self._navigation, "get_bank_container", lambda: None)()
        savings_container = self._navigation.get_savings_container()

        # Insert bank section after bank button container
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

        # Insert savings section after savings button container
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

        # Keep a single stretch at the bottom of the sidebar so the nav buttons
        # keep their original fixed height and extra space is pushed below the
        # lists, matching the old SidebarSavingsList behaviour.
        layout.addStretch(1)

        # Populate collapsible sections from initial accounts.
        self._rebuild_bank_items()
        self._rebuild_savings_items()

        self._connect_handlers()
        self._setup_event_handlers()
        self.update_route(current_route)

        # For all "savings" section pages (main savings page and per-account
        # page), start with the savings accounts list expanded so that moving
        # between them does not look like the list closes on first click.
        if current_route in ("savings", "savings_account"):
            try:
                self._savings_section.set_expanded(True)  # type: ignore[attr-defined]
                toggle_btn = self._navigation.get_savings_toggle_button()
                if toggle_btn:
                    toggle_btn.setChecked(True)
                    toggle_btn.setText("▲")
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
        # Bank accounts list toggle.
        if hasattr(self._navigation, "connect_bank_handlers"):
            try:
                self._navigation.connect_bank_handlers(self._on_toggle_bank_list)  # type: ignore[attr-defined]
            except Exception:
                pass

    def _on_toggle_savings_list(self) -> None:
        if not hasattr(self, "_savings_section"):
            return

        toggle_btn = self._navigation.get_savings_toggle_button()

        # Toggle the collapsible savings section and query its new state.
        is_expanded = False
        try:
            currently = self._savings_section.is_expanded()  # type: ignore[attr-defined]
            self._savings_section.set_expanded(not currently)  # type: ignore[attr-defined]
            is_expanded = self._savings_section.is_expanded()  # type: ignore[attr-defined]
        except Exception:
            return

        if toggle_btn:
            toggle_btn.setChecked(is_expanded)
            toggle_btn.setText("▲" if is_expanded else "▼")

        # Apply style and update geometry.
        self._apply_toggle_button_style()
        self._update_button_width()

    def _on_savings_clicked(self) -> None:
        if self._navigate is not None:
            self._navigate("savings")  # type: ignore[arg-type]

    def _on_toggle_bank_list(self) -> None:
        """Expand/collapse the bank accounts list under the 'חשבונות' button."""
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

        # Toggle the collapsible section and query its new state.
        is_expanded = False
        try:
            currently = self._bank_section.is_expanded()  # type: ignore[attr-defined]
            self._bank_section.set_expanded(not currently)  # type: ignore[attr-defined]
            is_expanded = self._bank_section.is_expanded()  # type: ignore[attr-defined]
        except Exception:
            return

        if is_expanded:
            # Keep pressed-style button when the list is open.
            if bank_btn:
                bank_btn.setStyleSheet("border-bottom-color: transparent;")
        else:
            if bank_btn:
                bank_btn.setStyleSheet("")

        if toggle_btn:
            toggle_btn.setChecked(is_expanded)
            toggle_btn.setText("▲" if is_expanded else "▼")

        self._update_button_width()

    def _on_savings_account_clicked(self, account: SavingsAccount) -> None:
        """Handle click on a specific savings account button in the sidebar."""
        if self._navigate is None:
            return

        # Propagate selected account name up to the closest BasePage so it can
        # be read by the savings-account detail page via the shared app_context.
        parent = self.parent()
        while parent is not None and not hasattr(
            parent, "set_selected_savings_account"
        ):
            parent = parent.parent()

        if parent is not None and hasattr(parent, "set_selected_savings_account"):
            try:
                parent.set_selected_savings_account(account.name)  # type: ignore[attr-defined]
            except Exception:
                pass

        # Navigate to the savings-account detail page.
        self._navigate("savings_account")  # type: ignore[arg-type]

    def _on_bank_account_clicked(self, account: BankAccount) -> None:
        """Handle click on a specific bank account button in the sidebar."""
        if self._navigate is None:
            return

        # Propagate selected account name up to the closest BasePage so it can
        # be read by the bank-account detail page via the shared app_context.
        parent = self.parent()
        while parent is not None and not hasattr(parent, "set_selected_bank_account"):
            parent = parent.parent()

        if parent is not None and hasattr(parent, "set_selected_bank_account"):
            try:
                parent.set_selected_bank_account(account.name)  # type: ignore[attr-defined]
            except Exception:
                pass

        # Navigate to the bank-account detail page.
        self._navigate("bank_account")  # type: ignore[arg-type]

    def _apply_toggle_button_style(self) -> None:
        toggle_btn = self._navigation.get_savings_toggle_button()
        savings_btn = self._navigation.get_savings_button()
        if toggle_btn and savings_btn:
            apply_toggle_button_style(
                toggle_btn,
                savings_btn,
                bool(
                    hasattr(self, "_savings_section")
                    and self._savings_section.is_expanded()  # type: ignore[attr-defined]
                ),
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
                    # Refresh collapsible sections styling
                    self._refresh_collapsible_sections()
            except Exception:
                try:
                    from PyQt6.QtCore import QEvent, QTimer  # type: ignore

                    if event.type() == QEvent.Type.StyleChange:  # type: ignore
                        QTimer.singleShot(50, self._update_button_width)
                        self._apply_toggle_button_style()
                        # Refresh collapsible sections styling
                        self._refresh_collapsible_sections()
                except Exception:
                    pass

        self.changeEvent = changeEvent  # type: ignore[assignment]

    def _refresh_collapsible_sections(self) -> None:
        """Refresh styling of collapsible sections when theme changes."""
        if hasattr(self, "_savings_section"):
            try:
                self._savings_section.refresh_theme()  # type: ignore[attr-defined]
            except Exception:
                pass
        if hasattr(self, "_bank_section"):
            try:
                self._bank_section.refresh_theme()  # type: ignore[attr-defined]
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

        update_savings_accounts_container_width(
            self,
            sidebar_width,
            # Use the internal content widget of the collapsible savings section.
            getattr(self._savings_section, "_content", None),
        )

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        # Rebuild collapsible sections from the updated accounts list.
        self._rebuild_bank_items()
        self._rebuild_savings_items()

    def refresh_profile(self) -> None:
        self._avatar.refresh()

    def update_route(self, route: Optional[str]) -> None:
        dashboard_btn = self._navigation.get_dashboard_button()
        if not dashboard_btn:
            return

        is_home = route == "home"
        is_bank = route == "bank_accounts"
        is_bank_section = route in ("bank_accounts", "bank_account")
        # Distinguish between the main savings page (where the savings button
        # itself should be disabled, like the dashboard button on home) and the
        # per-account page, which should still allow clicking the savings
        # button to return to the overview. For styling, we still treat both as
        # part of the "savings" section so the button and list remain pressed.
        is_savings = route == "savings"
        is_savings_section = route in ("savings", "savings_account")

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
            # Disable only on the main bank-accounts page; keep it enabled on the
            # per-account page so clicking it navigates back to the overview.
            bank_btn.setEnabled(not is_bank)
            bank_btn.blockSignals(False)

        # Show bank accounts list + its toggle on bank-related pages.
        bank_toggle_btn = (
            self._navigation.get_bank_toggle_button()
            if hasattr(self._navigation, "get_bank_toggle_button")
            else None
        )
        if hasattr(self, "_bank_section"):
            if is_bank_section:
                # On the bank-accounts page, respect the current expanded state;
                # just ensure the toggle is visible and reflects it.
                is_expanded = False
                try:
                    is_expanded = self._bank_section.is_expanded()  # type: ignore[attr-defined]
                except Exception:
                    is_expanded = False

                # When the list is expanded (arrow pressed), hide the bottom border.
                # When collapsed (arrow not pressed), show the bottom border.
                if bank_btn:
                    if is_expanded:
                        bank_btn.setStyleSheet("border-bottom-color: transparent;")
                    else:
                        bank_btn.setStyleSheet(
                            ""
                        )  # Use default CSS which shows bottom border when checked
                if bank_toggle_btn:
                    bank_toggle_btn.setVisible(True)
                    bank_toggle_btn.setChecked(is_expanded)
                    bank_toggle_btn.setText("▲" if is_expanded else "▼")
            else:
                # Collapse when leaving the bank-accounts page.
                try:
                    self._bank_section.set_expanded(False)  # type: ignore[attr-defined]
                except Exception:
                    pass
                if bank_toggle_btn:
                    bank_toggle_btn.setVisible(False)
                    bank_toggle_btn.setChecked(False)
                    bank_toggle_btn.setText("▼")

        savings_btn = self._navigation.get_savings_button()
        if savings_btn:
            savings_btn.blockSignals(True)
            savings_btn.setChecked(is_savings_section)
            # Disable only on the main savings page; keep it enabled on the
            # per-account page so clicking it navigates back to the overview.
            savings_btn.setEnabled(not is_savings)
            savings_btn.blockSignals(False)
            self._update_button_width()

        toggle_btn = self._navigation.get_savings_toggle_button()
        if toggle_btn:
            toggle_btn.setVisible(is_savings_section)
            if not is_savings_section:
                if hasattr(self, "_savings_section"):
                    try:
                        self._savings_section.set_expanded(False)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                toggle_btn.setChecked(False)
                toggle_btn.setText("▼")
            self._apply_toggle_button_style()

        # Control visibility of the entire savings section widget.
        if hasattr(self, "_savings_section"):
            try:
                self._savings_section.setVisible(is_savings_section)  # type: ignore[attr-defined]
            except Exception:
                pass

        self._current_route = route

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _rebuild_bank_items(self) -> None:
        """Populate the collapsible bank section with one row per BankAccount."""
        if not hasattr(self, "_bank_section"):
            return

        items: List[tuple[str, Callable[[], None]]] = []

        for acc in self._accounts:
            if not isinstance(acc, BankAccount):
                continue
            name = acc.name

            def make_cb(account: BankAccount) -> Callable[[], None]:
                def _cb() -> None:
                    # Reuse existing selection + navigation behaviour.
                    self._on_bank_account_clicked(account)

                return _cb

            items.append((name, make_cb(acc)))

        try:
            self._bank_section.set_items(items)  # type: ignore[attr-defined]
        except Exception:
            pass

    def _rebuild_savings_items(self) -> None:
        """Populate the collapsible savings section with one row per SavingsAccount."""
        if not hasattr(self, "_savings_section"):
            return

        items: List[tuple[str, Callable[[], None]]] = []

        for acc in self._accounts:
            if not isinstance(acc, SavingsAccount):
                continue
            name = acc.name

            def make_cb(account: SavingsAccount) -> Callable[[], None]:
                def _cb() -> None:
                    # Reuse existing selection + navigation behaviour.
                    self._on_savings_account_clicked(account)

                return _cb

            items.append((name, make_cb(acc)))

        try:
            self._savings_section.set_items(items)  # type: ignore[attr-defined]
        except Exception:
            pass
