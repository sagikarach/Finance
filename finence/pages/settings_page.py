from __future__ import annotations

from typing import Callable, Dict, List, Optional
from pathlib import Path

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QApplication,
    QIcon,
    QPixmap,
    QToolButton,
    QToolTip,
    QCursor,
)
from ..data.provider import AccountsProvider
from .base_page import BasePage


class SettingsPage(BasePage):
    """Settings page for user configuration."""

    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        get_previous_route: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="הגדרות",
            current_route="settings",
        )
        self._update_eye_icon: Optional[Callable[[], None]] = None
        self._get_previous_route = get_previous_route

    def _build_header_left_buttons(self) -> List[QToolButton]:
        """Add back button to header."""
        buttons = []
        back_btn = QToolButton(self)
        back_btn.setObjectName("IconButton")
        back_btn.setText("←")
        back_btn.setToolTip("חזרה")
        if self._navigate is not None:
            def go_back():
                previous = "home"
                if self._get_previous_route is not None:
                    previous = self._get_previous_route()
                self._navigate(previous)
            back_btn.clicked.connect(go_back)
        buttons.append(back_btn)
        return buttons

    def _on_theme_changed(self, is_dark: bool) -> None:
        """Handle theme change - update eye icon and sidebar."""
        super()._on_theme_changed(is_dark)
        if self._update_eye_icon is not None:
            self._update_eye_icon()

    def _build_content(self, main_col: QVBoxLayout) -> None:
        """Build settings page specific content: user settings and grid layout."""
        # User settings card
        content_card = QWidget(self)
        content_card.setObjectName("Sidebar")
        try:
            content_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
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

        lock_checkbox = QCheckBox("הפעל נעילת אפליקציה", content_card)
        lock_checkbox.setChecked(bool(getattr(self._user, "lock_enabled", False)))

        password_label = QLabel("סיסמה", content_card)
        password_edit = QLineEdit(content_card)
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

        # Eye icon button
        eye_button = QToolButton(content_card)
        eye_button.setObjectName("PasswordEye")
        eye_button.setCheckable(True)
        eye_button.setToolTip("הצג / הסתר סיסמה")

        # Load eye icon based on theme
        app = QApplication.instance()
        current_theme = "light"
        if app is not None:
            try:
                current_theme = str(app.property("theme") or "light")
            except Exception:
                current_theme = "light"
        is_dark = current_theme == "dark"

        eye_icon_path = None
        if is_dark:
            for ext in [".png", ".jpg"]:
                test_path = (
                    Path.cwd() / "data" / "assets" / "icons" / f"eye_icon_dark{ext}"
                )
                if test_path.exists():
                    eye_icon_path = test_path
                    break
        else:
            for ext in [".png", ".jpg"]:
                test_path = Path.cwd() / "data" / "assets" / "icons" / f"eye_icon{ext}"
                if test_path.exists():
                    eye_icon_path = test_path
                    break

        if eye_icon_path and eye_icon_path.exists():
            pixmap = QPixmap(str(eye_icon_path))
            if not pixmap.isNull():
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

        # Function to update eye icon based on theme
        def update_eye_icon() -> None:
            app_ = QApplication.instance()
            current_theme_ = "light"
            if app_ is not None:
                try:
                    current_theme_ = str(app_.property("theme") or "light")
                except Exception:
                    current_theme_ = "light"
            is_dark_ = current_theme_ == "dark"

            eye_icon_path_ = None
            if is_dark_:
                for ext in [".png", ".jpg"]:
                    test_path = (
                        Path.cwd() / "data" / "assets" / "icons" / f"eye_icon_dark{ext}"
                    )
                    if test_path.exists():
                        eye_icon_path_ = test_path
                        break
            else:
                for ext in [".png", ".jpg"]:
                    test_path = (
                        Path.cwd() / "data" / "assets" / "icons" / f"eye_icon{ext}"
                    )
                    if test_path.exists():
                        eye_icon_path_ = test_path
                        break

            if eye_icon_path_ and eye_icon_path_.exists():
                pixmap_ = QPixmap(str(eye_icon_path_))
                if not pixmap_.isNull():
                    try:
                        from PySide6.QtCore import QSize  # type: ignore

                        scaled_pixmap_ = pixmap_.scaled(
                            QSize(24, 24),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        eye_button.setIconSize(QSize(24, 24))
                    except Exception:
                        try:
                            from PyQt6.QtCore import QSize  # type: ignore

                            scaled_pixmap_ = pixmap_.scaled(
                                QSize(24, 24),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            eye_button.setIconSize(QSize(24, 24))
                        except Exception:
                            scaled_pixmap_ = pixmap_.scaled(
                                24,
                                24,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                    icon_ = QIcon(scaled_pixmap_)
                    eye_button.setIcon(icon_)
                    eye_button.setText("")

        self._update_eye_icon = update_eye_icon

        # Password visibility toggle
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

        # Save button handler
        def on_save_clicked() -> None:
            self._user.full_name = name_edit.text() or self._user.full_name
            try:
                self._user.lock_enabled = lock_checkbox.isChecked()  # type: ignore[assignment]
            except Exception:
                pass
            try:
                self._user.password = (
                    password_edit.text() if self._user.lock_enabled else None
                )  # type: ignore[assignment]
            except Exception:
                pass
            try:
                self._user_store.save(self._user)
            except Exception:
                pass
            # Update sidebar
            try:
                if self._sidebar is not None:
                    self._sidebar.refresh_profile()
            except Exception:
                pass
            # Show confirmation
            try:
                QToolTip.showText(QCursor.pos(), "ההגדרות נשמרו")
            except Exception:
                pass

        save_button.clicked.connect(on_save_clicked)  # type: ignore[arg-type]

        # Layout user settings card
        content_layout.addWidget(title_label)
        content_layout.addSpacing(4)
        content_layout.addWidget(lock_checkbox)
        content_layout.addSpacing(8)

        # Name row
        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        dash1 = QLabel("-", content_card)
        name_row.addWidget(name_label)
        name_row.addWidget(dash1)
        name_row.addWidget(name_edit, 1)

        # Password row
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

        # Lock checkbox controls password visibility
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

        # First row: extra square + user settings square
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
