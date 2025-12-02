from __future__ import annotations

from pathlib import Path
from typing import Optional, Callable

from ..qt import QWidget, QVBoxLayout, QHBoxLayout, QLabel, Qt, QPushButton, QSizePolicy
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore


class Sidebar(QWidget):
    """
    Right-hand sidebar showing the current user's avatar and name,
    navigation buttons, and handling avatar upload/update.
    """

    def __init__(
        self,
        user: UserProfile,
        store: UserProfileStore,
        parent: Optional[QWidget] = None,
        navigate: Optional[Callable[[str], None]] = None,
        current_route: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self._user = user
        self._store = store
        self._navigate = navigate
        self._current_route = current_route

        self.setObjectName("Sidebar")
        # Ensure background style for Sidebar is actually painted
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._avatar_label = QLabel(self)
        self._avatar_label.setObjectName("AvatarCircle")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Initial placeholder (first letter of the user's name)
        initial = (self._user.full_name or " ")[0]
        self._avatar_label.setText(initial)
        try:
            self._avatar_label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass

        self._name_label = QLabel(f"שלום, {self._user.full_name}", self)
        self._name_label.setObjectName("UserName")
        try:
            self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        layout.addWidget(self._avatar_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._name_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(24)  # More space between name and button

        # Navigation button: "לוח בקרה" (Dashboard) - full width of sidebar
        # Create container that will extend to sidebar edges
        button_container = QWidget(self)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        self._dashboard_btn = QPushButton("לוח בקרה", button_container)
        self._dashboard_btn.setObjectName("SidebarNavButton")
        self._dashboard_btn.setCheckable(True)
        # Always connect the click handler first (before setting state)
        if self._navigate is not None:
            # Connect the click handler (button is new, so no need to disconnect)
            self._dashboard_btn.clicked.connect(lambda: self._navigate("home"))  # type: ignore[arg-type]
        # Explicitly set initial state based on current route
        self.update_route(current_route)
        # Make button full width
        try:
            self._dashboard_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass
        button_container_layout.addWidget(self._dashboard_btn)

        # Store container reference
        self._button_container = button_container

        # Add container to main layout (will be positioned by layout initially)
        layout.addWidget(button_container)

        # Function to update container to span full sidebar width
        def update_container_width():
            if (
                hasattr(self, "_button_container")
                and self._button_container.isVisible()
            ):
                sidebar_width = self.width()
                # Get current position from layout
                container_rect = self._button_container.geometry()
                if container_rect.height() > 0:  # Only if container has been laid out
                    # Set container to full sidebar width, positioned at x=0
                    self._button_container.setGeometry(
                        0, container_rect.y(), sidebar_width, container_rect.height()
                    )

        # Store update function so it can be called externally
        self._update_button_width = update_container_width

        # Override resizeEvent to update container width
        original_resize = self.resizeEvent

        def resizeEvent(event):  # type: ignore
            if original_resize is not None:
                try:
                    original_resize(event)
                except Exception:
                    pass
            # Small delay to let layout complete, then update
            try:
                from PySide6.QtCore import QTimer  # type: ignore

                QTimer.singleShot(10, update_container_width)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore

                    QTimer.singleShot(10, update_container_width)
                except Exception:
                    update_container_width()

        self.resizeEvent = resizeEvent  # type: ignore[assignment]

        # Update on show as well
        original_show = self.showEvent

        def showEvent(event):  # type: ignore
            if original_show is not None:
                try:
                    original_show(event)
                except Exception:
                    pass
            # Ensure button state is correct when sidebar becomes visible
            if hasattr(self, "_dashboard_btn") and hasattr(self, "_current_route"):
                self.update_route(self._current_route)
            try:
                from PySide6.QtCore import QTimer  # type: ignore

                QTimer.singleShot(10, update_container_width)
            except Exception:
                try:
                    from PyQt6.QtCore import QTimer  # type: ignore

                    QTimer.singleShot(10, update_container_width)
                except Exception:
                    update_container_width()

        self.showEvent = showEvent  # type: ignore[assignment]

        # Override changeEvent to detect style changes (theme changes)
        original_change = self.changeEvent

        def changeEvent(event):  # type: ignore
            if original_change is not None:
                try:
                    original_change(event)
                except Exception:
                    pass
            # When style changes (theme toggle), update button width
            try:
                from PySide6.QtCore import QEvent  # type: ignore

                if event.type() == QEvent.Type.StyleChange:  # type: ignore
                    try:
                        from PySide6.QtCore import QTimer  # type: ignore

                        QTimer.singleShot(50, update_container_width)
                    except Exception:
                        try:
                            from PyQt6.QtCore import QTimer  # type: ignore

                            QTimer.singleShot(50, update_container_width)
                        except Exception:
                            update_container_width()
            except Exception:
                try:
                    from PyQt6.QtCore import QEvent  # type: ignore

                    if event.type() == QEvent.Type.StyleChange:  # type: ignore
                        try:
                            from PyQt6.QtCore import QTimer  # type: ignore

                            QTimer.singleShot(50, update_container_width)
                        except Exception:
                            update_container_width()
                except Exception:
                    pass

        self.changeEvent = changeEvent  # type: ignore[assignment]

        layout.addStretch(1)

        # Make avatar clickable
        self._avatar_label.mousePressEvent = self._on_avatar_clicked  # type: ignore[assignment]

        # If we already have an avatar path stored, load it
        if self._user.avatar_path:
            self._set_avatar_from_path(self._user.avatar_path)

    def refresh_profile(self) -> None:
        """Refresh displayed name (and placeholder avatar if no image) from the user object."""
        self._name_label.setText(f"שלום, {self._user.full_name}")
        if not self._user.avatar_path:
            # Update initial letter if user changed their name
            initial = (self._user.full_name or " ")[0]
            self._avatar_label.setText(initial)

    def update_route(self, route: Optional[str]) -> None:
        """Update the button state based on the current route."""
        if not hasattr(self, "_dashboard_btn"):
            return
        is_home = route == "home"
        # Block signals temporarily to avoid triggering navigation
        self._dashboard_btn.blockSignals(True)
        self._dashboard_btn.setChecked(is_home)
        self._dashboard_btn.setEnabled(not is_home)
        self._dashboard_btn.blockSignals(False)
        self._current_route = route

    def _on_avatar_clicked(self, event) -> None:  # type: ignore[override]
        """Open a file dialog and update the avatar image, saving a copy."""
        try:
            from PySide6.QtWidgets import QFileDialog  # type: ignore
        except Exception:
            try:
                from PyQt6.QtWidgets import QFileDialog  # type: ignore
            except Exception:
                return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "בחר תמונת פרופיל",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if not file_name:
            return

        if self._set_avatar_from_path(file_name):
            try:
                self._store.save(self._user)
            except Exception:
                pass

    def _set_avatar_from_path(self, file_name: Optional[str]) -> bool:
        """Load avatar from disk and apply it as background inside the circle."""
        if not file_name:
            return False

        src_path = Path(file_name)
        if not src_path.exists():
            return False

        try:
            from PySide6.QtGui import QPixmap  # type: ignore
        except Exception:
            try:
                from PyQt6.QtGui import QPixmap  # type: ignore
            except Exception:
                return False

        pix = QPixmap(str(src_path))
        if pix.isNull():
            return False

        size = max(self._avatar_label.width(), self._avatar_label.height(), 72)
        pix = pix.scaled(
            size,
            size,
            getattr(
                Qt, "KeepAspectRatioByExpanding", Qt.AspectRatioMode.KeepAspectRatio
            ),
            getattr(
                Qt, "SmoothTransformation", Qt.TransformationMode.SmoothTransformation
            ),
        )

        # Save a copy inside the app; the PNG will be shown as circular via CSS
        try:
            data_dir = Path.cwd() / "data" / "avatars"
            data_dir.mkdir(parents=True, exist_ok=True)
            target_path = data_dir / "user_avatar.png"
            pix.save(str(target_path), "PNG")
            self._user.avatar_path = str(target_path)
        except Exception:
            target_path = src_path

        url = Path(self._user.avatar_path or str(target_path)).as_posix()
        radius = size // 2
        self._avatar_label.setFixedSize(size, size)
        self._avatar_label.setPixmap(QPixmap())  # ensure no old pixmap border
        self._avatar_label.setStyleSheet(
            f"""
            QLabel#AvatarCircle {{
                min-width: {size}px;
                min-height: {size}px;
                max-width: {size}px;
                max-height: {size}px;
                border-radius: {radius}px;
                background-color: transparent;
                background-image: url('{url}');
                background-position: center;
                background-repeat: no-repeat;
            }}
            """
        )
        return True
