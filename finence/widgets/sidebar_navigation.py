from __future__ import annotations

from typing import Optional, Callable

from ..qt import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, Qt


class SidebarNavigation:
    """Handles navigation buttons (dashboard and savings) for the sidebar."""

    def __init__(
        self,
        parent: QWidget,
        layout: QVBoxLayout,
        navigate: Optional[Callable[[str], None]],
        current_route: Optional[str],
    ) -> None:
        self._parent = parent
        self._layout = layout
        self._navigate = navigate
        self._current_route = current_route

        self._dashboard_btn: Optional[QPushButton] = None
        self._button_container: Optional[QWidget] = None
        self._savings_btn: Optional[QPushButton] = None
        self._savings_toggle_btn: Optional[QPushButton] = None
        self._savings_button_container: Optional[QWidget] = None

        self._setup_dashboard_button()
        self._setup_savings_button()

    def _setup_dashboard_button(self) -> None:
        """Setup the dashboard navigation button."""
        button_container = QWidget(self._parent)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        self._dashboard_btn = QPushButton("לוח בקרה", self._parent)
        self._dashboard_btn.setObjectName("SidebarNavButton")
        self._dashboard_btn.setCheckable(True)
        try:
            self._dashboard_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        if self._navigate is not None:
            self._dashboard_btn.clicked.connect(lambda: self._navigate("home"))  # type: ignore[arg-type]

        # Placeholder to reserve space
        placeholder = QWidget(button_container)
        placeholder.setMinimumHeight(40)
        button_container_layout.addWidget(placeholder)

        self._button_container = button_container
        self._layout.addWidget(button_container)

    def _setup_savings_button(self) -> None:
        """Setup the savings navigation button with expand/collapse toggle."""
        savings_button_container = QWidget(self._parent)
        try:
            savings_button_container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        except Exception:
            pass

        savings_button_layout = QHBoxLayout(savings_button_container)
        savings_button_layout.setContentsMargins(0, 0, 0, 0)
        savings_button_layout.setSpacing(0)

        # Main savings button
        is_savings = self._current_route == "savings"
        self._savings_btn = QPushButton("חסכונות", self._parent)
        # Use a dedicated object name so we can style it differently from the home button.
        self._savings_btn.setObjectName("SidebarNavButtonSavings")
        self._savings_btn.setCheckable(True)
        self._savings_btn.setChecked(is_savings)
        self._savings_btn.setEnabled(not is_savings)
        try:
            self._savings_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        # Toggle button (arrow)
        self._savings_toggle_btn = QPushButton("▼", self._parent)
        self._savings_toggle_btn.setObjectName("SidebarNavToggle")
        self._savings_toggle_btn.setFixedWidth(32)
        self._savings_toggle_btn.setCheckable(True)
        self._savings_toggle_btn.setChecked(False)
        self._savings_toggle_btn.setVisible(is_savings)
        try:
            self._savings_toggle_btn.raise_()
        except Exception:
            pass

        # Placeholder to reserve space
        placeholder = QWidget(savings_button_container)
        placeholder.setMinimumHeight(40)
        savings_button_layout.addWidget(placeholder)

        self._savings_button_container = savings_button_container
        self._layout.addWidget(savings_button_container)

    def get_dashboard_button(self) -> Optional[QPushButton]:
        """Get the dashboard button."""
        return self._dashboard_btn

    def get_dashboard_container(self) -> Optional[QWidget]:
        """Get the dashboard button container."""
        return self._button_container

    def get_savings_button(self) -> Optional[QPushButton]:
        """Get the savings button."""
        return self._savings_btn

    def get_savings_toggle_button(self) -> Optional[QPushButton]:
        """Get the savings toggle button."""
        return self._savings_toggle_btn

    def get_savings_container(self) -> Optional[QWidget]:
        """Get the savings button container."""
        return self._savings_button_container

    def connect_savings_handlers(
        self,
        on_toggle: Callable[[], None],
        on_savings_click: Callable[[], None],
        on_toggle_style: Callable[[], None],
    ) -> None:
        """Connect handlers for savings button interactions."""
        if self._savings_toggle_btn:
            self._savings_toggle_btn.clicked.connect(on_toggle)  # type: ignore[arg-type]
        if self._savings_btn:
            self._savings_btn.clicked.connect(on_savings_click)  # type: ignore[arg-type]
            self._savings_btn.toggled.connect(lambda checked: on_toggle_style())  # type: ignore[arg-type]

