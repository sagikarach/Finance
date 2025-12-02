from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QApplication,
    QIcon,
    QPixmap,
)
from ..styles.theme import load_default_stylesheet, load_dark_stylesheet
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..data.user_profile_store import UserProfileStore
from ..models.accounts import MoneyAccount
from ..models.user import UserProfile
from ..widgets.sidebar import Sidebar


class SettingsPage(QWidget):
    """
    Settings view that reuses the same sidebar and header row layout
    but replaces the settings button with a back/return button.
    """

    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._app_context = app_context or {}
        self._provider: AccountsProvider = provider or JsonFileAccountsProvider()
        self._accounts: List[MoneyAccount] = self._provider.list_accounts()
        self._user_store = UserProfileStore()
        self._user: UserProfile = self._user_store.load(
            default_full_name=self._app_context.get("userName", "אורח"),
            accounts=self._accounts,
        )
        self._navigate = navigate
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 16, 40)
        layout.setSpacing(12)

        # Header row with title and a "back" button, with blue background like Home
        from ..qt import QToolButton  # local import to avoid circular at top

        header_title = QLabel("הגדרות", self)
        header_title.setObjectName("HeaderTitle")

        back_btn = QToolButton(self)
        back_btn.setObjectName("IconButton")
        back_btn.setText("←")
        back_btn.setToolTip("חזרה ללוח הבקרה")
        if self._navigate is not None:
            back_btn.clicked.connect(lambda: self._navigate("home"))  # type: ignore[arg-type]

        bell_btn = QToolButton(self)
        bell_btn.setObjectName("IconButton")
        bell_btn.setText("🔔")
        bell_btn.setToolTip("התראות")

        # Theme toggle button (sun/moon)
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
                # Update sidebar button width after theme change
                if hasattr(self, "_sidebar") and hasattr(
                    self._sidebar, "_update_button_width"
                ):
                    try:
                        from PySide6.QtCore import QTimer  # type: ignore

                        QTimer.singleShot(100, self._sidebar._update_button_width)
                    except Exception:
                        try:
                            from PyQt6.QtCore import QTimer  # type: ignore

                            QTimer.singleShot(100, self._sidebar._update_button_width)
                        except Exception:
                            pass
            except Exception:
                pass

        theme_btn.toggled.connect(on_theme_toggled)  # type: ignore[arg-type]

        header_container = QWidget(self)
        header_container.setObjectName("Sidebar")
        try:
            header_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_container_layout = QHBoxLayout(header_container)
        header_container_layout.setContentsMargins(12, 8, 12, 8)
        header_container_layout.setSpacing(12)
        header_container_layout.addWidget(back_btn)
        header_container_layout.addWidget(bell_btn)
        header_container_layout.addWidget(theme_btn)
        header_container_layout.addStretch(1)
        header_container_layout.addWidget(header_title)

        # User settings card (background square) for editing name & password
        content_card = QWidget(self)
        # Use same blue square style as other rectangles
        content_card.setObjectName("Sidebar")
        try:
            content_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        # Make inner layout right-to-left so Hebrew labels appear on the right
        try:
            content_card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # type: ignore[attr-defined]
        except Exception:
            try:
                content_card.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(12)

        title_label = QLabel("פרטי משתמש", content_card)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        name_label = QLabel("שם משתמש", content_card)
        name_edit = QLineEdit(content_card)
        name_edit.setText(self._user.full_name)

        # Lock toggle
        lock_checkbox = QCheckBox("הפעל נעילת אפליקציה", content_card)
        lock_checkbox.setChecked(bool(getattr(self._user, "lock_enabled", False)))

        password_label = QLabel("סיסמה", content_card)
        password_edit = QLineEdit(content_card)
        # Right-to-left typing and alignment for password
        try:
            password_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)  # type: ignore[attr-defined]
        except Exception:
            try:
                password_edit.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass
        try:
            password_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        try:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)  # type: ignore[attr-defined]
        except Exception:
            try:
                password_edit.setEchoMode(QLineEdit.Password)  # type: ignore[attr-defined]
            except Exception:
                pass
        if getattr(self._user, "password", None):
            password_edit.setText(self._user.password or "")

        save_button = QPushButton("שמור", content_card)
        save_button.setObjectName("SaveButton")

        # Eye icon button to toggle password visibility (in-line with password field)
        eye_button = QToolButton(content_card)
        eye_button.setObjectName("PasswordEye")
        eye_button.setCheckable(True)
        eye_button.setToolTip("הצג / הסתר סיסמה")

        # Load eye icon from image file (PNG with transparency)
        from pathlib import Path

        eye_icon_path = None
        # Try PNG first (has transparency), then JPG as fallback
        for ext in [".png", ".jpg"]:
            test_path = Path.cwd() / "data" / "assets" / f"eye_icon{ext}"
            if test_path.exists():
                eye_icon_path = test_path
                break

        if eye_icon_path and eye_icon_path.exists():
            pixmap = QPixmap(str(eye_icon_path))
            if not pixmap.isNull():
                # Scale to icon size
                try:
                    from PySide6.QtCore import QSize  # type: ignore

                    scaled_pixmap = pixmap.scaled(
                        QSize(24, 24),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    eye_button.setIconSize(QSize(24, 24))
                except Exception:
                    try:
                        from PyQt6.QtCore import QSize  # type: ignore

                        scaled_pixmap = pixmap.scaled(
                            QSize(24, 24),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        eye_button.setIconSize(QSize(24, 24))
                    except Exception:
                        scaled_pixmap = pixmap.scaled(
                            24,
                            24,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                icon = QIcon(scaled_pixmap)
                eye_button.setIcon(icon)
                eye_button.setText("")
        else:
            eye_button.setText("👁")

        from ..qt import QToolTip, QCursor  # type: ignore

        def on_toggle_show_password(checked: bool) -> None:
            try:
                mode = (
                    QLineEdit.EchoMode.Normal
                    if checked
                    else QLineEdit.EchoMode.Password
                )  # type: ignore[attr-defined]
                password_edit.setEchoMode(mode)
            except Exception:
                try:
                    mode = QLineEdit.Normal if checked else QLineEdit.Password  # type: ignore[attr-defined]
                    password_edit.setEchoMode(mode)
                except Exception:
                    pass

        eye_button.toggled.connect(on_toggle_show_password)  # type: ignore[arg-type]

        def on_save_clicked() -> None:
            self._user.full_name = name_edit.text() or self._user.full_name
            # Update lock settings & password
            try:
                self._user.lock_enabled = lock_checkbox.isChecked()  # type: ignore[assignment]
            except Exception:
                pass
            try:
                # type: ignore[assignment]
                self._user.password = (
                    password_edit.text() if self._user.lock_enabled else None
                )
            except Exception:
                pass
            try:
                self._user_store.save(self._user)
            except Exception:
                pass
            # Update sidebar widgets to reflect new name immediately
            try:
                if hasattr(self, "_sidebar") and self._sidebar is not None:  # type: ignore[truthy-function]
                    self._sidebar.refresh_profile()  # type: ignore[union-attr]
            except Exception:
                pass
            # Show small confirmation hint near cursor
            try:
                QToolTip.showText(QCursor.pos(), "ההגדרות נשמרו")
            except Exception:
                pass

        save_button.clicked.connect(on_save_clicked)  # type: ignore[arg-type]

        content_layout.addWidget(title_label)
        content_layout.addSpacing(4)
        content_layout.addWidget(lock_checkbox)
        content_layout.addSpacing(8)

        # Single-line rows: "שם משתמש - .....", "סיסמה - ....."
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        dash1 = QLabel("-", content_card)
        name_row.addWidget(name_label)
        name_row.addWidget(dash1)
        name_row.addWidget(name_edit, 1)

        password_row_widget = QWidget(content_card)
        password_row = QHBoxLayout(password_row_widget)
        password_row.setSpacing(8)
        dash2 = QLabel("-", content_card)
        password_row.addWidget(password_label)
        password_row.addWidget(dash2)
        password_row.addWidget(password_edit, 1)
        password_row.addWidget(eye_button)

        content_layout.addLayout(name_row)
        content_layout.addWidget(password_row_widget)

        # Lock checkbox controls visibility/usage of the password row
        def update_lock_ui(enabled: bool) -> None:
            password_row_widget.setVisible(enabled)
            password_edit.setEnabled(enabled)
            eye_button.setEnabled(enabled)
            if not enabled:
                password_edit.clear()

        def on_lock_toggled(checked: bool) -> None:
            update_lock_ui(checked)

        lock_checkbox.toggled.connect(on_lock_toggled)  # type: ignore[arg-type]
        update_lock_ui(lock_checkbox.isChecked())
        content_layout.addStretch(1)
        # Place save button at the bottom-right of the square
        try:
            content_layout.addWidget(
                save_button,
                0,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
        except Exception:
            content_layout.addWidget(save_button)

        # Helper to create additional empty squares
        def _make_extra_card(title: str) -> QWidget:
            card = QWidget(self)
            card.setObjectName("Sidebar")
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            layout_card = QVBoxLayout(card)
            layout_card.setContentsMargins(24, 24, 24, 24)
            layout_card.setSpacing(12)
            lbl = QLabel(title, card)
            try:
                lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            except Exception:
                pass
            layout_card.addWidget(lbl)
            layout_card.addStretch(1)
            return card

        extra_card_top_right = _make_extra_card("הגדרות נוספות")
        extra_card_bottom_left = _make_extra_card("הגדרה פנויה")
        extra_card_bottom_right = _make_extra_card("הגדרה פנויה")

        # Main column for header + two rows of squares (2x2 grid)
        main_area = QWidget(self)
        main_col = QVBoxLayout(main_area)
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(16)
        main_col.addWidget(header_container, 0)

        # First row: extra square + user settings square (user settings on the right)
        row1 = QHBoxLayout()
        row1.setSpacing(16)
        row1.addWidget(extra_card_top_right, 1)
        row1.addWidget(content_card, 1)

        # Second row: two extra squares
        row2 = QHBoxLayout()
        row2.setSpacing(16)
        row2.addWidget(extra_card_bottom_left, 1)
        row2.addWidget(extra_card_bottom_right, 1)

        main_col.addLayout(row1, 1)
        main_col.addLayout(row2, 1)

        # Sidebar with user info
        self._sidebar = Sidebar(
            self._user,
            self._user_store,
            self,
            navigate=self._navigate,
            current_route="settings",
        )

        # Set fixed width for sidebar to ensure consistent sizing across pages
        try:
            self._sidebar.setFixedWidth(240)
            self._sidebar.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        split_row = QHBoxLayout()
        split_row.setSpacing(16)
        split_row.addWidget(main_area, 1)  # Let main area take remaining space
        split_row.addWidget(self._sidebar, 0)  # No stretch for fixed-width sidebar

        layout.addLayout(split_row)
        self.setLayout(layout)
