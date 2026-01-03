from __future__ import annotations

from typing import Callable, List, Optional

from ..models.accounts import BankAccount, MoneyAccount, SavingsAccount
from ..models.sidebar import SidebarSectionState
from ..qt import QEvent, QTimer, QWidget
from .collapsible_section import CollapsibleButtonList
from .sidebar_navigation import SidebarNavigation
from .sidebar_state import SidebarState
from .sidebar_scroll_area import SidebarScrollArea


class SidebarController:
    def __init__(
        self,
        *,
        widget: QWidget,
        state: SidebarState,
        scroll: SidebarScrollArea,
        navigation: SidebarNavigation,
        bank_section: CollapsibleButtonList,
        savings_section: CollapsibleButtonList,
        yearly_section: CollapsibleButtonList,
        navigate: Optional[Callable[[str], None]],
        current_route: Optional[str],
        accounts: List[MoneyAccount],
    ) -> None:
        self._widget = widget
        self._state = state
        self._scroll = scroll
        self._navigation = navigation
        self._bank_section = bank_section
        self._savings_section = savings_section
        self._yearly_section = yearly_section
        self._navigate = navigate
        self._current_route = current_route
        self._accounts = accounts

        self._bank_section.set_header_click_handler(self._on_bank_clicked)
        self._savings_section.set_header_click_handler(self._on_savings_clicked)
        self._yearly_section.set_header_click_handler(self._on_yearly_clicked)

        self._scroll.schedule_style_update(
            self._scroll.apply_scrollbar_style, delay_ms=0
        )

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        self._rebuild_bank_items()
        self._rebuild_savings_items()
        try:
            QTimer.singleShot(10, self._update_button_width)
        except Exception:
            self._update_button_width()

    def update_route(self, route: Optional[str]) -> None:
        dashboard_btn = self._navigation.get_dashboard_button()
        if not dashboard_btn:
            return

        is_home = route == "home"
        is_bank_section = route in ("bank_accounts", "bank_account")
        is_savings_section = route in ("savings", "savings_account")
        is_monthly_data = route == "monthly_data"
        is_one_time_events = route == "one_time_events"
        is_installments = route == "installments"
        is_yearly_section = route in (
            "yearly_overview",
            "yearly_data",
            "yearly_category_trends",
        )

        dashboard_btn.blockSignals(True)
        dashboard_btn.setChecked(is_home)
        dashboard_btn.setEnabled(not is_home)
        dashboard_btn.blockSignals(False)

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

        one_time_events_btn = (
            self._navigation.get_one_time_events_button()
            if hasattr(self._navigation, "get_one_time_events_button")
            else None
        )
        if one_time_events_btn:
            one_time_events_btn.blockSignals(True)
            one_time_events_btn.setChecked(is_one_time_events)
            one_time_events_btn.setEnabled(not is_one_time_events)
            one_time_events_btn.blockSignals(False)

        installments_btn = (
            self._navigation.get_installments_button()
            if hasattr(self._navigation, "get_installments_button")
            else None
        )
        if installments_btn:
            installments_btn.blockSignals(True)
            installments_btn.setChecked(is_installments)
            installments_btn.setEnabled(not is_installments)
            installments_btn.blockSignals(False)

        self._bank_section.set_active(bool(is_bank_section))
        self._yearly_section.set_active(bool(is_yearly_section))
        self._savings_section.set_active(bool(is_savings_section))

        self._apply_section_expanded(
            section=self._bank_section,
            key=self._state.key_bank_expanded(),
            active=is_bank_section,
        )
        self._apply_section_expanded(
            section=self._yearly_section,
            key=self._state.key_yearly_expanded(),
            active=is_yearly_section,
        )
        self._apply_section_expanded(
            section=self._savings_section,
            key=self._state.key_savings_expanded(),
            active=is_savings_section,
        )

        self._current_route = route

    def on_resize(self) -> None:
        try:
            QTimer.singleShot(10, self._update_button_width)
        except Exception:
            self._update_button_width()

    def on_show(self) -> None:
        try:
            self.update_route(self._current_route)
        except Exception:
            pass
        try:
            QTimer.singleShot(10, self._update_button_width)
        except Exception:
            self._update_button_width()

    def on_style_change(self, event: QEvent) -> None:
        try:
            if event.type() == QEvent.Type.StyleChange:
                QTimer.singleShot(50, self._update_button_width)
                self._bank_section.refresh_theme()
                self._savings_section.refresh_theme()
                self._yearly_section.refresh_theme()
                QTimer.singleShot(0, self._scroll.apply_scrollbar_style)
        except Exception:
            pass

    def _update_button_width(self) -> None:
        try:
            self._widget.updateGeometry()
            self._widget.update()
        except Exception:
            pass

    def _clear_page_button_presses(self) -> None:
        dashboard_btn = self._navigation.get_dashboard_button()
        if dashboard_btn:
            dashboard_btn.blockSignals(True)
            dashboard_btn.setChecked(False)
            dashboard_btn.setEnabled(True)
            dashboard_btn.blockSignals(False)

        monthly_data_btn = (
            self._navigation.get_monthly_data_button()
            if hasattr(self._navigation, "get_monthly_data_button")
            else None
        )
        if monthly_data_btn:
            monthly_data_btn.blockSignals(True)
            monthly_data_btn.setChecked(False)
            monthly_data_btn.setEnabled(True)
            monthly_data_btn.blockSignals(False)

        one_time_events_btn = (
            self._navigation.get_one_time_events_button()
            if hasattr(self._navigation, "get_one_time_events_button")
            else None
        )
        if one_time_events_btn:
            one_time_events_btn.blockSignals(True)
            one_time_events_btn.setChecked(False)
            one_time_events_btn.setEnabled(True)
            one_time_events_btn.blockSignals(False)

        installments_btn = (
            self._navigation.get_installments_button()
            if hasattr(self._navigation, "get_installments_button")
            else None
        )
        if installments_btn:
            installments_btn.blockSignals(True)
            installments_btn.setChecked(False)
            installments_btn.setEnabled(True)
            installments_btn.blockSignals(False)

    def _on_yearly_clicked(self) -> None:
        self._clear_page_button_presses()
        is_yearly_section = bool(
            self._current_route
            in ("yearly_overview", "yearly_data", "yearly_category_trends")
        )
        if not is_yearly_section:
            if self._navigate is not None:
                self._navigate("yearly_overview")
            self._yearly_section.set_expanded(True)
            self._state.set_bool(self._state.key_yearly_expanded(), True)
            self._update_button_width()
            return

        if self._current_route != "yearly_overview":
            self._yearly_section.set_expanded(True)
            self._state.set_bool(self._state.key_yearly_expanded(), True)
            if self._navigate is not None:
                self._navigate("yearly_overview")
            self._update_button_width()
            return

        currently = bool(self._yearly_section.is_expanded())
        new_expanded = not currently
        self._yearly_section.set_expanded(new_expanded)
        self._state.set_bool(self._state.key_yearly_expanded(), bool(new_expanded))
        self._update_button_width()

    def _on_savings_clicked(self) -> None:
        self._clear_page_button_presses()
        is_savings_section = bool(self._current_route in ("savings", "savings_account"))
        if not is_savings_section:
            if self._navigate is not None:
                self._navigate("savings")
            self._savings_section.set_expanded(True)
            self._state.set_bool(self._state.key_savings_expanded(), True)
            self._update_button_width()
            return

        if self._current_route != "savings":
            self._savings_section.set_expanded(True)
            self._state.set_bool(self._state.key_savings_expanded(), True)
            if self._navigate is not None:
                self._navigate("savings")
            self._update_button_width()
            return

        currently = bool(self._savings_section.is_expanded())
        new_expanded = not currently
        self._savings_section.set_expanded(new_expanded)
        self._state.set_bool(self._state.key_savings_expanded(), bool(new_expanded))
        self._update_button_width()

    def _on_bank_clicked(self) -> None:
        self._clear_page_button_presses()
        is_bank_section = bool(self._current_route in ("bank_accounts", "bank_account"))
        if not is_bank_section:
            if self._navigate is not None:
                self._navigate("bank_accounts")
            self._bank_section.set_expanded(True)
            self._state.set_bool(self._state.key_bank_expanded(), True)
            self._update_button_width()
            return

        if self._current_route != "bank_accounts":
            self._bank_section.set_expanded(True)
            self._state.set_bool(self._state.key_bank_expanded(), True)
            if self._navigate is not None:
                self._navigate("bank_accounts")
            self._update_button_width()
            return

        currently = bool(self._bank_section.is_expanded())
        new_expanded = not currently
        self._bank_section.set_expanded(new_expanded)
        self._state.set_bool(self._state.key_bank_expanded(), bool(new_expanded))
        self._update_button_width()

    def _apply_section_expanded(
        self, *, section: CollapsibleButtonList, key: str, active: bool
    ) -> None:
        persisted = self._state.get_bool(key)
        if active:
            desired = True if persisted is None else bool(persisted)
        else:
            desired = False
            if persisted is True:
                self._state.set_bool(key, False)
        try:
            section.set_expanded(bool(desired))
        except Exception:
            pass

    def _build_section_state(
        self,
        *,
        section_id: str,
        title: str,
        account_type: type,
        expanded: bool,
        click_handler: Callable[[MoneyAccount], None],
        account_filter: Optional[Callable[[MoneyAccount], bool]] = None,
    ) -> SidebarSectionState:
        section = SidebarSectionState(
            section_id=section_id, title=title, expanded=expanded
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
        from ..models.accounts import BudgetAccount

        expanded = bool(self._bank_section.is_expanded())
        section = self._build_section_state(
            section_id="bank_accounts",
            title="חשבונות",
            account_type=MoneyAccount,
            expanded=expanded,
            click_handler=self._on_bank_account_clicked,
            account_filter=lambda a: (
                (isinstance(a, BankAccount) and bool(getattr(a, "active", False)))
                or (
                    isinstance(a, BudgetAccount)
                    and bool(getattr(a, "active", False))
                    and str(getattr(a, "name", "") or "").strip() != ""
                )
            ),
        )
        self._bank_section.set_items(section.as_collapsible_items())
        self._bank_section.set_expanded(section.expanded)

    def _rebuild_savings_items(self) -> None:
        expanded = bool(self._savings_section.is_expanded())
        section = self._build_section_state(
            section_id="savings_accounts",
            title="חסכונות",
            account_type=SavingsAccount,
            expanded=expanded,
            click_handler=self._on_savings_account_clicked,
        )
        self._savings_section.set_items(section.as_collapsible_items())
        self._savings_section.set_expanded(section.expanded)

    def _on_savings_account_clicked(self, account: MoneyAccount) -> None:
        if self._navigate is None:
            return
        parent: Optional[QWidget] = self._widget.parentWidget()
        while parent is not None and not hasattr(
            parent, "set_selected_savings_account"
        ):
            parent = parent.parentWidget()
        if parent is not None and hasattr(parent, "set_selected_savings_account"):
            try:
                parent.set_selected_savings_account(account.name)
            except Exception:
                pass
        self._navigate("savings_account")

    def _on_bank_account_clicked(self, account: MoneyAccount) -> None:
        if self._navigate is None:
            return
        parent: Optional[QWidget] = self._widget.parentWidget()
        while parent is not None and not hasattr(parent, "set_selected_bank_account"):
            parent = parent.parentWidget()
        if parent is not None and hasattr(parent, "set_selected_bank_account"):
            try:
                parent.set_selected_bank_account(account.name)
            except Exception:
                pass
        self._navigate("bank_account")
