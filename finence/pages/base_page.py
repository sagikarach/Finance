from __future__ import annotations

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
        self._user: UserProfile = self._user_store.load(
            default_full_name=self._app_context.get("userName", "אורח"),
            accounts=self._accounts,
        )
        self._page_title = page_title
        self._current_route = current_route
        self._sidebar: Optional[Sidebar] = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 16, 40)
        layout.setSpacing(12)

        header_container = self._build_header()

        main_area = QWidget(self)
        main_col = QVBoxLayout(main_area)
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(16)
        main_col.addWidget(header_container, 0)

        self._build_content(main_col)

        self._sidebar = Sidebar(
            self._user,
            self._user_store,
            self,
            navigate=self._navigate,
            current_route=self._current_route,
        )

        try:
            self._sidebar.setFixedWidth(240)
            self._sidebar.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        split_row = QHBoxLayout()
        split_row.setSpacing(16)
        split_row.addWidget(main_area, 1)
        split_row.addWidget(self._sidebar, 0)

        layout.addLayout(split_row)
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

        theme_btn = self._build_theme_toggle_button()
        header_layout.addWidget(theme_btn)

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
        if self._sidebar is not None and hasattr(self._sidebar, "_update_button_width"):
            try:
                from PySide6.QtCore import QTimer  # type: ignore

                QTimer.singleShot(100, self._sidebar._update_button_width)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore

                    QTimer.singleShot(100, self._sidebar._update_button_width)
                except Exception:
                    pass

    def _build_content(self, main_col: QVBoxLayout) -> None:
        raise NotImplementedError("Subclasses must implement _build_content()")
