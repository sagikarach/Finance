from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..qt import QWidget, QVBoxLayout, QLabel, Qt
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore


class SidebarAvatar:
    """Handles avatar display and upload functionality for the sidebar."""

    def __init__(
        self,
        parent: QWidget,
        user: UserProfile,
        store: UserProfileStore,
        layout: QVBoxLayout,
    ) -> None:
        self._parent = parent
        self._user = user
        self._store = store
        self._layout = layout

        self._avatar_label: Optional[QLabel] = None
        self._name_label: Optional[QLabel] = None

        self._setup()

    def _setup(self) -> None:
        """Setup avatar label and user name."""
        self._avatar_label = QLabel(self._parent)
        self._avatar_label.setObjectName("AvatarCircle")
        initial = (self._user.full_name or " ")[0]
        self._avatar_label.setText(initial)
        try:
            self._avatar_label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass

        self._name_label = QLabel(f"שלום, {self._user.full_name}", self._parent)
        self._name_label.setObjectName("UserName")
        try:
            self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        self._layout.addWidget(self._avatar_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._name_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._layout.addSpacing(24)

        # Make avatar clickable
        self._avatar_label.mousePressEvent = self._on_avatar_clicked  # type: ignore[assignment]

        # Load avatar if already set
        if self._user.avatar_path:
            self.set_avatar_from_path(self._user.avatar_path)

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
            self._parent,
            "בחר תמונת פרופיל",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if not file_name:
            return

        if self.set_avatar_from_path(file_name):
            try:
                self._store.save(self._user)
            except Exception:
                pass

    def set_avatar_from_path(self, file_name: Optional[str]) -> bool:
        """Load avatar from disk and apply it as background inside the circle."""
        if not file_name or not self._avatar_label:
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

        # Save a copy inside the app
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
        self._avatar_label.setPixmap(QPixmap())
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

    def refresh(self) -> None:
        """Refresh displayed name (and placeholder avatar if no image) from the user object."""
        if not self._name_label or not self._avatar_label:
            return

        self._name_label.setText(f"שלום, {self._user.full_name}")
        if not self._user.avatar_path:
            initial = (self._user.full_name or " ")[0]
            self._avatar_label.setText(initial)
