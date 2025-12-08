from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional, Dict, List

from ..qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    Qt,
    QSizePolicy,
    QApplication,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..data.user_profile_store import UserProfileStore
from ..models.user import UserProfile
from ..widgets.sidebar import Sidebar
from ..styles.theme import load_default_stylesheet, load_dark_stylesheet


def _load_default_full_name() -> str:
    """Load default full name from defaults.json file."""
    defaults_path = Path.cwd() / "defaults.json"
    default_full_name = "אורח"

    if defaults_path.exists():
        try:
            with defaults_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    user_defaults = data.get("user", {})
                    default_full_name = str(
                        user_defaults.get("default_full_name", default_full_name)
                    )
        except Exception:
            pass

    return default_full_name


class BasePage(QWidget):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        page_title: str = "",
        current_route: str = "",
    ) -> None:
        super().__init__(parent)
        self._app_context = app_context or {}
        self._provider: AccountsProvider = provider or JsonFileAccountsProvider()
        self._accounts: List = self._provider.list_accounts()
        self._navigate = navigate
        self._user_store = UserProfileStore()
        # Load default name from JSON file, with app_context as fallback
        default_name = self._app_context.get("userName") or _load_default_full_name()
        self._user: UserProfile = self._user_store.load(
            default_full_name=default_name,
            accounts=self._accounts,
        )
        self._page_title = page_title
        self._current_route = current_route
        self._sidebar: Optional[Sidebar] = None
        self._theme_btn: Optional[QToolButton] = None
        self._content_col: Optional[QVBoxLayout] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        main_area = QWidget(self)
        main_col = QVBoxLayout(main_area)
        main_col.setContentsMargins(40, 40, 16, 40)
        main_col.setSpacing(16)

        header_container = self._build_header()
        try:
            header_container.setFixedHeight(56)  # Fixed height to match home page
            header_container.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        main_col.addWidget(header_container, 0)

        content_area = QWidget(self)
        content_col = QVBoxLayout(content_area)
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(16)

        self._content_col = content_col

        self._build_content(content_col)
        main_col.addWidget(content_area, 1)

        selected_name = None
        try:
            value = self._app_context.get("selected_savings_account")
            if isinstance(value, str) and value:
                selected_name = value
        except Exception:
            selected_name = None

        self._sidebar = Sidebar(
            self._user,
            self._user_store,
            self,
            navigate=self._navigate,
            current_route=self._current_route,
            accounts=self._accounts,
            selected_savings_account=selected_name,
        )

        try:
            self._sidebar.setFixedWidth(240)
            self._sidebar.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        sidebar_container = QWidget(self)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(
            0, 40, 16, 40
        )  # Larger top and bottom margins
        sidebar_layout.setSpacing(16)
        sidebar_layout.addWidget(self._sidebar, 1)  # Expand to fill available space

        layout.addWidget(main_area, 1)
        layout.addWidget(sidebar_container, 0)

        self.setLayout(layout)

    def _build_header(self) -> QWidget:
        header_container = QWidget(self)
        header_container.setObjectName("Sidebar")
        try:
            header_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(12)

        left_buttons = self._build_header_left_buttons()
        for btn in left_buttons:
            header_layout.addWidget(btn)

        bell_btn = QToolButton(self)
        bell_btn.setObjectName("IconButton")
        bell_btn.setText("🔔")
        bell_btn.setToolTip("התראות")
        header_layout.addWidget(bell_btn)

        self._theme_btn = self._build_theme_toggle_button()
        header_layout.addWidget(self._theme_btn)

        header_layout.addStretch(1)

        header_title = QLabel(self._page_title, self)
        header_title.setObjectName("HeaderTitle")
        header_layout.addWidget(header_title)

        return header_container

    def _build_header_left_buttons(self) -> List[QToolButton]:
        return []

    def _build_theme_toggle_button(self) -> QToolButton:
        theme_btn = QToolButton(self)
        theme_btn.setObjectName("IconButton")
        theme_btn.setCheckable(True)

        app = QApplication.instance()
        current_theme = "light"
        if app is not None:
            try:
                current_theme = str(app.property("theme") or "light")
            except Exception:
                current_theme = "light"
        is_dark = current_theme == "dark"
        theme_btn.setChecked(is_dark)
        theme_btn.setText("🌙" if is_dark else "☀")
        theme_btn.setToolTip("מצב כהה / מצב בהיר")

        def on_theme_toggled(checked: bool) -> None:
            app_ = QApplication.instance()
            if app_ is None:
                return
            try:
                if checked:
                    app_.setStyleSheet(load_dark_stylesheet())
                    app_.setProperty("theme", "dark")
                    theme_btn.setText("🌙")
                else:
                    app_.setStyleSheet(load_default_stylesheet())
                    app_.setProperty("theme", "light")
                    theme_btn.setText("☀")
                self._on_theme_changed(checked)
            except Exception:
                pass

        theme_btn.toggled.connect(on_theme_toggled)  # type: ignore[arg-type]
        return theme_btn

    def _on_theme_changed(self, is_dark: bool) -> None:
        if self._theme_btn is not None:
            self._theme_btn.setChecked(is_dark)
            self._theme_btn.setText("🌙" if is_dark else "☀")

        if self._sidebar is not None:
            # Re-run sidebar width logic so buttons/list fill correctly in the
            # new theme, and refresh the savings list background if present.
            if hasattr(self._sidebar, "_update_button_width"):
                try:
                    from PySide6.QtCore import QTimer  # type: ignore

                    QTimer.singleShot(100, self._sidebar._update_button_width)
                except Exception:
                    try:
                        from PyQt6.QtCore import QTimer  # type: ignore

                        QTimer.singleShot(100, self._sidebar._update_button_width)
                    except Exception:
                        pass

            # Ensure the toggle arrow background is recalculated for the new theme.
            if hasattr(self._sidebar, "_apply_toggle_button_style"):
                try:
                    self._sidebar._apply_toggle_button_style()  # type: ignore[attr-defined]
                except Exception:
                    pass

            # Refresh collapsible sections styling
            if hasattr(self._sidebar, "_savings_section"):
                try:
                    self._sidebar._savings_section.refresh_theme()  # type: ignore[attr-defined]
                except Exception:
                    pass
            if hasattr(self._sidebar, "_bank_section"):
                try:
                    self._sidebar._bank_section.refresh_theme()  # type: ignore[attr-defined]
                except Exception:
                    pass

        try:
            from ..widgets.action_history_table import ActionHistoryTable

            history_table = self.findChild(ActionHistoryTable)
            if history_table is not None and hasattr(
                history_table, "_update_table"
            ):
                history_table._update_table()  # type: ignore[attr-defined]
        except Exception:
            pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._theme_btn is not None:
            app = QApplication.instance()
            current_theme = "light"
            if app is not None:
                try:
                    current_theme = str(app.property("theme") or "light")
                except Exception:
                    current_theme = "light"
            is_dark = current_theme == "dark"
            self._theme_btn.blockSignals(True)
            self._theme_btn.setChecked(is_dark)
            self._theme_btn.setText("🌙" if is_dark else "☀")
            self._theme_btn.blockSignals(False)

    def _build_content(self, main_col: QVBoxLayout) -> None:
        raise NotImplementedError("Subclasses must implement _build_content()")

    def set_selected_savings_account(self, account_name: str) -> None:
        try:
            self._app_context["selected_savings_account"] = account_name
        except Exception:
            pass

    def set_selected_bank_account(self, account_name: str) -> None:
        try:
            self._app_context["selected_bank_account"] = account_name
        except Exception:
            pass
