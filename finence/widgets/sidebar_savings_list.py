from __future__ import annotations

from typing import Optional, Callable, List, Any

from ..qt import QWidget, QVBoxLayout, QPushButton, QSizePolicy, Qt
from ..models.accounts import MoneyAccount, SavingsAccount


class SidebarSavingsList:

    def __init__(
        self,
        parent: QWidget,
        layout: QVBoxLayout,
        accounts: List[MoneyAccount],
        navigate: Optional[Callable[[str], None]],
    ) -> None:
        self._parent = parent
        self._layout = layout
        self._accounts = accounts
        self._navigate = navigate

        self._savings_expanded = False
        self._savings_animation: Optional[Any] = None  # type: ignore[type-arg]
        self._savings_accounts_container: Optional[QWidget] = None
        self._savings_accounts_layout: Optional[QVBoxLayout] = None
        self._savings_account_buttons: List[QPushButton] = []

        self._setup_container()
        self._load_accounts()

    def _setup_container(self) -> None:
        self._savings_accounts_container = QWidget(self._parent)
        self._savings_accounts_container.setObjectName("SidebarSavingsList")
        try:
            self._savings_accounts_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
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

        savings_accounts = [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]

        for account in savings_accounts:
            btn = QPushButton(account.name, self._savings_accounts_container)
            btn.setObjectName("SidebarNavSubButton")
            btn.setCheckable(False)
            try:
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
                )
            except Exception:
                pass
            if self._navigate is not None:
                btn.clicked.connect(lambda checked, acc=account: self._navigate("savings"))  # type: ignore[arg-type]
            self._savings_accounts_layout.addWidget(btn)
            self._savings_account_buttons.append(btn)

        self.update_visibility()

    def toggle(self) -> bool:
        self._savings_expanded = not self._savings_expanded
        self.update_visibility()
        return self._savings_expanded

    def is_expanded(self) -> bool:
        return self._savings_expanded

    def set_expanded(self, expanded: bool) -> None:
        self._savings_expanded = expanded
        self.update_visibility()

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
            from PySide6.QtCore import QPropertyAnimation, QEasingCurve  # type: ignore
            AnimationClass = QPropertyAnimation
        except Exception:
            try:
                from PyQt6.QtCore import QPropertyAnimation, QEasingCurve  # type: ignore
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
        container.setGeometry(-16, container_rect.y(), sidebar_width + 32, natural_height)

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
            f"QWidget#SidebarSavingsList {{ "
            f"background: {container_bg}; "
            f"{border_css}"
            f"}}"
        )

    def get_container(self) -> Optional[QWidget]:
        return self._savings_accounts_container

    def update_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._accounts = accounts
        self._load_accounts()

