from __future__ import annotations

from typing import Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
from ..models.google_drive_auth import GoogleDriveAuth
from ..models.google_oauth import OAuthError
from ..models.drive_inbox import DriveInboxState
from ..utils.safe import QT_ERRORS


def _field(parent: QDialog, label_text: str, *, password: bool = False) -> QLineEdit:
    edit = QLineEdit(parent)
    if password:
        try:
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        except QT_ERRORS:
            try:
                edit.setEchoMode(QLineEdit.Password)
            except QT_ERRORS:
                pass
    return edit


class GoogleDriveSettingsDialog(QDialog):
    """Configure the Google OAuth client + Drive inbox folder, and sign in.

    The user pastes the Client ID/secret from their Google Cloud OAuth "Desktop
    app" credential and the Drive folder id the Gmail rule saves statements to,
    then signs in with Google (loopback browser flow).
    """

    def __init__(self, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self._auth = GoogleDriveAuth()
        self._state = DriveInboxState.load()

        self.setWindowTitle("ייבוא מ‑Google Drive")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel("חיבור תיקיית Drive לייבוא אוטומטי של דפי בנק", self)
        title.setObjectName("HeaderTitle")
        layout.addWidget(title)

        hint = QLabel(
            "הדבק את פרטי לקוח ה‑OAuth (סוג Desktop app) מ‑Google Cloud, "
            "ואת מזהה תיקיית ה‑Drive שאליה כלל ה‑Gmail שומר את הקבצים.",
            self,
        )
        try:
            hint.setWordWrap(True)
        except QT_ERRORS:
            pass
        layout.addWidget(hint)

        self._client_id = _field(self, "Client ID")
        self._client_secret = _field(self, "Client secret", password=True)
        self._folder_id = _field(self, "Folder ID")

        for lbl, edit in (
            ("Client ID", self._client_id),
            ("Client secret", self._client_secret),
            ("Folder ID (מזהה התיקייה)", self._folder_id),
        ):
            layout.addWidget(QLabel(lbl, self))
            layout.addWidget(edit)

        # Prefill from stored config.
        try:
            self._client_id.setText(self._auth.client_id)
            self._client_secret.setText(self._auth.client_secret)
            self._folder_id.setText(self._state.folder_id)
        except QT_ERRORS:
            pass

        self._status = QLabel("", self)
        try:
            self._status.setWordWrap(True)
        except QT_ERRORS:
            pass
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        self._signin_btn = QPushButton("התחבר עם Google", self)
        self._signout_btn = QPushButton("התנתק", self)
        save_btn = QPushButton("שמור", self)
        close_btn = QPushButton("סגור", self)
        self._signin_btn.clicked.connect(self._on_sign_in)
        self._signout_btn.clicked.connect(self._on_sign_out)
        save_btn.clicked.connect(self._on_save)
        close_btn.clicked.connect(self.accept)
        for b in (self._signin_btn, self._signout_btn, save_btn, close_btn):
            buttons.addWidget(b)
        layout.addLayout(buttons)

        self._refresh_status()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _save_config(self) -> None:
        self._auth.set_credentials(
            client_id=self._client_id.text().strip(),
            client_secret=self._client_secret.text().strip(),
        )
        self._state.folder_id = self._folder_id.text().strip()
        self._state.save()

    def _refresh_status(self) -> None:
        signed = False
        try:
            signed = self._auth.is_signed_in()
        except QT_ERRORS:
            signed = False
        if signed:
            self._status.setText("מחובר ל‑Google ✓")
        elif self._auth.is_configured():
            self._status.setText("מוגדר — נותר להתחבר עם Google.")
        else:
            self._status.setText("הזן Client ID ו‑Client secret ולחץ שמור.")
        try:
            self._signout_btn.setEnabled(signed)
            self._signin_btn.setEnabled(self._client_id.text().strip() != "")
        except QT_ERRORS:
            pass

    # ── actions ──────────────────────────────────────────────────────────────
    def _on_save(self) -> None:
        self._save_config()
        self._refresh_status()

    def _on_sign_in(self) -> None:
        self._save_config()
        if not self._auth.is_configured():
            self._status.setText("חסר Client ID או Client secret.")
            return
        self._status.setText("נפתח דפדפן לאישור ההרשאה…")
        try:
            self._auth.sign_in()
        except OAuthError as exc:
            try:
                QMessageBox.warning(self, "ההתחברות נכשלה", str(exc))
            except QT_ERRORS:
                pass
            self._status.setText("ההתחברות נכשלה.")
            return
        except QT_ERRORS as exc:
            self._status.setText(f"שגיאה: {exc}")
            return
        self._refresh_status()

    def _on_sign_out(self) -> None:
        try:
            self._auth.sign_out()
        except QT_ERRORS:
            pass
        self._refresh_status()

    def folder_id(self) -> str:
        return self._folder_id.text().strip()
