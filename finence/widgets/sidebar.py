from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..qt import QWidget, QVBoxLayout, QLabel, Qt
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore


class Sidebar(QWidget):
    """
    Right-hand sidebar showing the current user's avatar and name,
    and handling avatar upload/update.
    """

    def __init__(
        self,
        user: UserProfile,
        store: UserProfileStore,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._user = user
        self._store = store

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

        name_label = QLabel(self._user.full_name, self)
        name_label.setObjectName("UserName")
        try:
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        layout.addWidget(self._avatar_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(name_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

        # Make avatar clickable
        self._avatar_label.mousePressEvent = self._on_avatar_clicked  # type: ignore[assignment]

        # If we already have an avatar path stored, load it
        if self._user.avatar_path:
            self._set_avatar_from_path(self._user.avatar_path)

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
            getattr(Qt, "KeepAspectRatioByExpanding", Qt.AspectRatioMode.KeepAspectRatio),
            getattr(Qt, "SmoothTransformation", Qt.TransformationMode.SmoothTransformation),
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


