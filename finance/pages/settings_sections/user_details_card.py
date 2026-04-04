from __future__ import annotations

from typing import Callable, Optional

from ...qt import (
    QCheckBox,
    QCursor,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from ...models.user import UserProfile
from ...data.user_profile_store import UserProfileStore
from ...models.firebase_session import FirebaseSessionStore
from ...models.firebase_workspace_profiles import FirebaseWorkspaceProfilesStore


class UserDetailsCard(QWidget):
    def __init__(
        self,
        *,
        parent: QWidget,
        user: UserProfile,
        user_store: UserProfileStore,
        on_profile_saved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._user = user
        self._user_store = user_store
        self._on_profile_saved = on_profile_saved
        self._eye_button: Optional[QToolButton] = None
        self._password_edit: Optional[QLineEdit] = None
        self._lock_checkbox: Optional[QCheckBox] = None
        self._password_row_widget: Optional[QWidget] = None
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("פרטי משתמש", self)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)

        lock_checkbox = QCheckBox("הפעל נעילת אפליקציה", self)
        lock_checkbox.setChecked(bool(getattr(self._user, "lock_enabled", False)))
        self._lock_checkbox = lock_checkbox
        layout.addSpacing(4)
        layout.addWidget(lock_checkbox)
        layout.addSpacing(8)

        name_label = QLabel("שם משתמש", self)
        name_edit = QLineEdit(self)
        name_edit.setText(self._user.full_name)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        dash1 = QLabel("-", self)
        name_row.addWidget(name_label)
        name_row.addWidget(dash1)
        name_row.addWidget(name_edit, 1)
        layout.addLayout(name_row)

        password_label = QLabel("סיסמה", self)
        password_edit = QLineEdit(self)
        self._password_edit = password_edit
        try:
            password_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                password_edit.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            password_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        try:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            try:
                password_edit.setEchoMode(QLineEdit.Password)
            except Exception:
                pass
        if getattr(self._user, "password", None):
            password_edit.setText(self._user.password or "")

        eye_button = QToolButton(self)
        eye_button.setObjectName("PasswordEye")
        eye_button.setCheckable(True)
        eye_button.setToolTip("הצג / הסתר סיסמה")
        self._eye_button = eye_button
        eye_button.setText("👁")

        password_row_widget = QWidget(self)
        self._password_row_widget = password_row_widget
        password_row = QHBoxLayout(password_row_widget)
        password_row.setSpacing(8)
        dash2 = QLabel("-", self)
        password_row.addWidget(password_label)
        password_row.addWidget(dash2)
        password_row.addWidget(password_edit, 1)
        password_row.addWidget(eye_button)
        layout.addWidget(password_row_widget)

        def on_toggle_show_password(checked: bool) -> None:
            try:
                mode = (
                    QLineEdit.EchoMode.Normal
                    if checked
                    else QLineEdit.EchoMode.Password
                )
                password_edit.setEchoMode(mode)
            except Exception:
                try:
                    mode = QLineEdit.Normal if checked else QLineEdit.Password
                    password_edit.setEchoMode(mode)
                except Exception:
                    pass

        eye_button.toggled.connect(on_toggle_show_password)

        def update_lock_ui(enabled: bool) -> None:
            password_row_widget.setVisible(enabled)
            password_edit.setEnabled(enabled)
            eye_button.setEnabled(enabled)
            if not enabled:
                password_edit.clear()

        def on_lock_toggled(checked: bool) -> None:
            update_lock_ui(checked)

        lock_checkbox.toggled.connect(on_lock_toggled)
        update_lock_ui(lock_checkbox.isChecked())

        save_button = QPushButton("שמור", self)
        save_button.setObjectName("SaveButton")

        def on_save_clicked() -> None:
            self._user.full_name = name_edit.text() or self._user.full_name
            try:
                self._user.lock_enabled = lock_checkbox.isChecked()
            except Exception:
                pass
            try:
                self._user.password = (
                    password_edit.text() if self._user.lock_enabled else None
                )
            except Exception:
                pass
            try:
                self._user_store.save(self._user)
            except Exception as _save_err:
                try:
                    QToolTip.showText(QCursor.pos(), f"שגיאה בשמירה: {_save_err}")
                except Exception:
                    pass
                return
            # If we're inside a Firebase workspace and that workspace has a saved profile,
            # store a per-workspace display name override. If it's not defined, UI falls back
            # to the global user profile.
            try:
                wid = str(FirebaseSessionStore().load().workspace_id or "").strip()
            except Exception:
                wid = ""
            if wid:
                try:
                    FirebaseWorkspaceProfilesStore().update_ui_prefs(
                        workspace_id=wid,
                        display_name=str(self._user.full_name or "").strip(),
                    )
                except Exception:
                    pass
            try:
                if self._on_profile_saved is not None:
                    self._on_profile_saved()
            except Exception:
                pass
            try:
                QToolTip.showText(QCursor.pos(), "ההגדרות נשמרו")
            except Exception:
                pass

        save_button.clicked.connect(on_save_clicked)
        layout.addStretch(1)
        try:
            layout.addWidget(
                save_button,
                0,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
        except Exception:
            layout.addWidget(save_button)
