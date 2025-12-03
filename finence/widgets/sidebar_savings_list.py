from __future__ import annotations

from typing import Optional, Callable, List, Any

from ..qt import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy, Qt
from ..models.accounts import MoneyAccount, SavingsAccount


class SidebarSavingsList:
    def __init__(
        self,
        parent: QWidget,
        layout: QVBoxLayout,
        accounts: List[MoneyAccount],
        on_account_clicked: Optional[Callable[[SavingsAccount], None]],
        selected_name: Optional[str] = None,
        selection_enabled: bool = False,
    ) -> None:
        self._parent = parent
        self._layout = layout
        self._accounts = accounts
        self._on_account_clicked = on_account_clicked
        self._selected_name: Optional[str] = selected_name
        # When False, we never show the arrow indicator or change selection
        # state. This lets the overview savings page behave differently from
        # the per-account detail page.
        self._selection_enabled: bool = selection_enabled

        self._savings_expanded = False
        self._savings_animation: Optional[Any] = None  # type: ignore[type-arg]
        self._savings_accounts_container: Optional[QWidget] = None
        self._savings_accounts_layout: Optional[QVBoxLayout] = None
        self._savings_account_buttons: List[QPushButton] = []
        self._savings_account_arrows: List[QLabel] = []
        self._savings_accounts: List[SavingsAccount] = []

        self._setup_container()
        self._load_accounts()

    def _setup_container(self) -> None:
        self._savings_accounts_container = QWidget(self._parent)
        self._savings_accounts_container.setObjectName("SidebarSavingsList")
        try:
            self._savings_accounts_container.setAttribute(
                Qt.WidgetAttribute.WA_StyledBackground, True
            )
        except Exception:
            pass

        self._savings_accounts_layout = QVBoxLayout(self._savings_accounts_container)
        self._savings_accounts_layout.setContentsMargins(0, 0, 0, 4)
        self._savings_accounts_layout.setSpacing(4)
        self._savings_accounts_container.hide()

        self._layout.addWidget(self._savings_accounts_container)
        self._layout.addStretch(1)

    def _load_accounts(self) -> None:
        if not self._savings_accounts_container or not self._savings_accounts_layout:
            return

        for btn in self._savings_account_buttons:
            btn.deleteLater()
        self._savings_account_buttons.clear()
        self._savings_account_arrows.clear()

        savings_accounts = [
            acc for acc in self._accounts if isinstance(acc, SavingsAccount)
        ]
        self._savings_accounts = savings_accounts

        for account in savings_accounts:
            # Row container so we can keep the arrow at a fixed position on the
            # right edge, but keep the name visually centered by adding a
            # symmetric spacer on the left.
            row = QWidget(self._savings_accounts_container)
            row_layout = QHBoxLayout(row)
            # Add a small right margin so the arrow is slightly inside the
            # visible sidebar area and never clipped by the edge.
            row_layout.setContentsMargins(0, 0, 8, 0)
            row_layout.setSpacing(0)

            left_spacer = QLabel("", row)
            left_spacer.setFixedWidth(24)

            btn = QPushButton(account.name, row)
            btn.setObjectName("SidebarNavSubButton")
            btn.setCheckable(False)
            try:
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
                )
            except Exception:
                pass

            arrow = QLabel("", row)
            arrow.setObjectName("SidebarNavSubArrow")
            arrow.setFixedWidth(20)
            arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if self._on_account_clicked is not None:

                def handle_click(
                    checked: bool = False, acc: SavingsAccount = account
                ) -> None:
                    # Only update visual selection/arrow when selection
                    # indicators are enabled (on the savings-account detail
                    # page). On the overview page we still navigate, but do
                    # not change the sidebar visuals here.
                    if self._selection_enabled:
                        self._selected_name = acc.name
                        self._refresh_selected_state()
                    callback = self._on_account_clicked
                    if callback is not None:
                        callback(acc)

                btn.clicked.connect(handle_click)  # type: ignore[arg-type]
            row_layout.addWidget(left_spacer, 0)
            row_layout.addWidget(btn, 1)
            row_layout.addWidget(arrow, 0)

            self._savings_accounts_layout.addWidget(row)
            self._savings_account_buttons.append(btn)
            self._savings_account_arrows.append(arrow)

        self._refresh_selected_state()
        self.update_visibility()

    def _format_button_text(self, name: str) -> str:
        """Return the label text for a savings account button."""
        return name

    def _refresh_selected_state(self) -> None:
        """Update all button labels to reflect which account is selected."""
        if (
            not self._savings_account_buttons
            or not self._savings_accounts
            or not self._savings_account_arrows
        ):
            return

        for btn, arrow, account in zip(
            self._savings_account_buttons,
            self._savings_account_arrows,
            self._savings_accounts,
        ):
            if not self._selection_enabled:
                arrow.setText("")
                continue

            is_selected = bool(
                self._selected_name and account.name == self._selected_name
            )
            # Keep the arrow label always present (fixed-width) so the layout
            # and text position never change; only the glyph changes between
            # selected / unselected states.
            arrow.setText("◀" if is_selected else "")

    def toggle(self) -> bool:
        self._savings_expanded = not self._savings_expanded
        self.update_visibility()
        return self._savings_expanded

    def is_expanded(self) -> bool:
        return self._savings_expanded

    def set_expanded(self, expanded: bool) -> None:
        if self._savings_expanded == expanded:
            return
        self._savings_expanded = expanded
        self.update_visibility()

    def expand_immediate(self) -> None:
        if not self._savings_accounts_container:
            return

        container = self._savings_accounts_container
        self._savings_expanded = True

        if self._savings_animation is not None:
            try:
                self._savings_animation.stop()  # type: ignore[attr-defined]
                self._savings_animation.deleteLater()  # type: ignore[attr-defined]
            except Exception:
                pass
            self._savings_animation = None

        container.show()
        container.setMaximumHeight(16777215)
        container.setMinimumHeight(0)

        self._apply_pressed_style(container)

        # Let the normal sidebar width-update path stretch this container,
        # but do it immediately so the first time it appears it already has
        # the same geometry as on subsequent interactions.
        container.adjustSize()
        parent = self._parent
        if parent is not None and hasattr(parent, "_update_button_width"):
            try:
                parent._update_button_width()  # type: ignore[attr-defined]
            except Exception:
                pass

    def update_visibility(self) -> None:
        if not self._savings_accounts_container:
            return

        if not self._savings_account_buttons:
            if self._savings_expanded:
                self._savings_accounts_container.show()
            else:
                self._savings_accounts_container.hide()
            return

        try:
            from PySide6.QtCore import QPropertyAnimation  # type: ignore

            AnimationClass = QPropertyAnimation
        except Exception:
            try:
                from PyQt6.QtCore import QPropertyAnimation  # type: ignore

                AnimationClass = QPropertyAnimation
            except Exception:
                if self._savings_expanded:
                    self._savings_accounts_container.show()
                else:
                    self._savings_accounts_container.hide()
                return

        if self._savings_animation is not None:
            try:
                self._savings_animation.stop()  # type: ignore[attr-defined]
                self._savings_animation.deleteLater()  # type: ignore[attr-defined]
            except Exception:
                pass

        container = self._savings_accounts_container

        if self._savings_expanded:
            self._expand(container, AnimationClass)
        else:
            self._collapse(container, AnimationClass)

    def refresh_theme(self) -> None:
        """Re-apply background/border styling based on current theme.

        Called when the application style/theme changes while the savings list
        is already expanded, so the blue background updates between light and
        dark modes without needing to collapse/re-open the list.
        """
        if not self._savings_accounts_container or not self._savings_expanded:
            return
        self._apply_pressed_style(self._savings_accounts_container)

    def _expand(self, container: QWidget, AnimationClass: type) -> None:
        container.show()
        container.setMaximumHeight(0)
        container.setMinimumHeight(0)

        self._apply_pressed_style(container)

        container.setMaximumHeight(16777215)
        container.setMinimumHeight(0)
        container.adjustSize()
        natural_height = container.height()
        container.setMaximumHeight(0)

        sidebar_width = self._parent.width()
        container_rect = container.geometry()
        container.setGeometry(
            -16, container_rect.y(), sidebar_width + 32, natural_height
        )

        self._savings_animation = AnimationClass(container, b"maximumHeight")  # type: ignore[assignment]
        if self._savings_animation is not None:
            try:
                from PySide6.QtCore import QEasingCurve  # type: ignore
            except Exception:
                try:
                    from PyQt6.QtCore import QEasingCurve  # type: ignore
                except Exception:
                    QEasingCurve = None  # type: ignore[assignment, misc]

            if QEasingCurve is not None:
                self._savings_animation.setDuration(300)  # type: ignore[attr-defined]
                self._savings_animation.setStartValue(0)  # type: ignore[attr-defined]
                self._savings_animation.setEndValue(natural_height)  # type: ignore[attr-defined]
                self._savings_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # type: ignore[attr-defined]

                def on_finished() -> None:
                    container.setMaximumHeight(16777215)
                    container.setMinimumHeight(0)

                self._savings_animation.finished.connect(on_finished)  # type: ignore[attr-defined, arg-type]
                self._savings_animation.start()  # type: ignore[attr-defined]

    def _collapse(self, container: QWidget, AnimationClass: type) -> None:
        current_height = container.height()

        self._savings_animation = AnimationClass(container, b"maximumHeight")  # type: ignore[assignment]
        if self._savings_animation is not None:
            try:
                from PySide6.QtCore import QEasingCurve  # type: ignore
            except Exception:
                try:
                    from PyQt6.QtCore import QEasingCurve  # type: ignore
                except Exception:
                    QEasingCurve = None  # type: ignore[assignment, misc]

            if QEasingCurve is not None:
                self._savings_animation.setDuration(300)  # type: ignore[attr-defined]
                self._savings_animation.setStartValue(current_height)  # type: ignore[attr-defined]
                self._savings_animation.setEndValue(0)  # type: ignore[attr-defined]
                self._savings_animation.setEasingCurve(QEasingCurve.Type.InCubic)  # type: ignore[attr-defined]

                def on_finished() -> None:
                    container.hide()
                    container.setMaximumHeight(16777215)
                    container.setMinimumHeight(0)
                    # Now remove the blue background/borders
                    container.setStyleSheet("")

                self._savings_animation.finished.connect(on_finished)  # type: ignore[attr-defined, arg-type]
                self._savings_animation.start()  # type: ignore[attr-defined]

    def _apply_pressed_style(self, container: QWidget) -> None:
        try:
            from PySide6.QtWidgets import QApplication  # type: ignore
        except Exception:
            try:
                from PyQt6.QtWidgets import QApplication  # type: ignore
            except Exception:
                return

        app = QApplication.instance()
        if app is None:
            return

        theme = app.property("theme")
        is_dark = theme == "dark"
        if is_dark:
            container_bg = "#020617"
            border_css = (
                "border-top: none; "
                "border-bottom: none; "
                "border-left: none; "
                "border-right: none; "
            )
        else:
            container_bg = "#dcecff"
            border_color = "#a0bce2"
            border_css = (
                f"border-top: none; "
                f"border-bottom: 2px solid {border_color}; "
                f"border-left: none; "
                f"border-right: none; "
            )

        container.setStyleSheet(
            f"QWidget#SidebarSavingsList {{ background: {container_bg}; {border_css}}}"
        )

    def get_container(self) -> Optional[QWidget]:
        return self._savings_accounts_container

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        self._load_accounts()
