"""Welcome / sign-in screen — the only thing a new user has to do.

Email + password, then one button: "log in" or "create account". Everything
else is automatic (see ``FirebaseLoginService.sign_in_or_up``): a private budget
is created, remembered for desktop and mobile, data typed before signing up is
imported, and the app opens. Joining a partner's budget is the one optional
step, behind "I have a share code".
"""

from __future__ import annotations

from typing import Optional

from ..qt import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ..models.firebase_auth_errors import auth_error_message
from ..models.firebase_login_service import FirebaseLoginService, OnboardingResult
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_workspace_profiles import FirebaseWorkspaceProfilesStore
from ..models.keychain_passwords import set_password
from ..utils.safe import QT_ERRORS


class WelcomeDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        allow_cancel: bool = False,
        prefill_email: str = "",
    ) -> None:
        super().__init__(parent)
        self.result_info: Optional[OnboardingResult] = None
        self.imported_files = 0
        self._store = FirebaseSessionStore()
        self._profiles = FirebaseWorkspaceProfilesStore()

        self.setWindowTitle("Finance")
        try:
            self.setModal(True)
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.setMinimumWidth(420)
        except QT_ERRORS:
            pass

        lay = QVBoxLayout(self)
        lay.setContentsMargins(36, 28, 36, 28)
        lay.setSpacing(12)

        title = QLabel("ברוכים הבאים ל-Finance", self)
        title.setObjectName("HeaderTitle")
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except QT_ERRORS:
            pass
        lay.addWidget(title)

        sub = QLabel(
            "התחבר, או צור חשבון חדש בלחיצה אחת.\n"
            "כל השאר מוגדר אוטומטית, והנתונים שלך מסונכרנים גם לאפליקציה בנייד.",
            self,
        )
        sub.setWordWrap(True)
        try:
            sub.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except QT_ERRORS:
            pass
        lay.addWidget(sub)

        self._email = self._ltr_input("אימייל")
        self._email.setText(prefill_email)
        self._password = self._ltr_input("סיסמה (לפחות 6 תווים)")
        try:
            self._password.setEchoMode(QLineEdit.EchoMode.Password)
        except QT_ERRORS:
            pass
        lay.addWidget(self._email)
        lay.addWidget(self._password)

        self._remember = QCheckBox("זכור אותי במחשב הזה", self)
        self._remember.setChecked(True)
        lay.addWidget(self._remember)

        # Optional: join a partner's budget.
        self._code_toggle = QPushButton("יש לי קוד שיתוף מבן/בת הזוג", self)
        self._code_toggle.setFlat(True)
        self._code = self._ltr_input("קוד שיתוף, לדוגמה AB12-CD34-EF56")
        self._code.hide()
        self._code_toggle.clicked.connect(self._toggle_code)
        lay.addWidget(self._code_toggle)
        lay.addWidget(self._code)

        self._status = QLabel("", self)
        self._status.setObjectName("ErrorLabel")
        self._status.setWordWrap(True)
        self._status.hide()
        lay.addWidget(self._status)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        self._login_btn = QPushButton("התחבר", self)
        self._login_btn.setObjectName("SaveButton")
        try:
            self._login_btn.setDefault(True)
        except QT_ERRORS:
            pass
        self._signup_btn = QPushButton("צור חשבון חדש", self)
        self._signup_btn.setObjectName("SecondaryButton")
        btns.addWidget(self._login_btn, 1)
        btns.addWidget(self._signup_btn, 1)
        lay.addLayout(btns)

        bottom = QHBoxLayout()
        forgot = QPushButton("שכחתי סיסמה", self)
        forgot.setFlat(True)
        bottom.addWidget(forgot)
        bottom.addStretch(1)
        close_btn = QPushButton("ביטול" if allow_cancel else "יציאה", self)
        close_btn.setFlat(True)
        bottom.addWidget(close_btn)
        lay.addLayout(bottom)

        self._login_btn.clicked.connect(lambda: self._submit(create_account=False))
        self._signup_btn.clicked.connect(lambda: self._submit(create_account=True))
        forgot.clicked.connect(self._forgot)
        close_btn.clicked.connect(self.reject)

    # ---- helpers ------------------------------------------------------------

    def _ltr_input(self, placeholder: str) -> QLineEdit:
        e = QLineEdit(self)
        e.setObjectName("SettingsInput")
        e.setPlaceholderText(placeholder)
        try:
            e.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except QT_ERRORS:
            pass
        return e

    def _toggle_code(self) -> None:
        try:
            self._code.setVisible(not self._code.isVisible())
            if self._code.isVisible():
                self._code.setFocus()
        except QT_ERRORS:
            pass

    def _set_status(self, text: str, *, error: bool = True) -> None:
        try:
            self._status.setObjectName("ErrorLabel" if error else "StatTitle")
            self._status.style().unpolish(self._status)
            self._status.style().polish(self._status)
            self._status.setText(text)
            self._status.show()
            QApplication.processEvents()
        except QT_ERRORS:
            pass

    def _set_busy(self, busy: bool) -> None:
        for b in (self._login_btn, self._signup_btn):
            try:
                b.setEnabled(not busy)
            except QT_ERRORS:
                pass

    # ---- actions ------------------------------------------------------------

    def _forgot(self) -> None:
        email = self._email.text().strip()
        try:
            FirebaseLoginService(session_store=self._store).send_password_reset(email=email)
        except RuntimeError as exc:
            self._set_status(auth_error_message(exc))
            return
        self._set_status(f"שלחנו קישור לאיפוס סיסמה אל {email}", error=False)

    def _submit(self, *, create_account: bool) -> None:
        email = self._email.text().strip()
        pw = self._password.text()
        code = self._code.text().strip() if self._code.isVisible() else ""
        if not email or not pw:
            self._set_status("חובה למלא אימייל וסיסמה")
            return

        self._set_busy(True)
        self._set_status(
            "יוצר את החשבון ומכין את התקציב שלך…" if create_account else "מתחבר…",
            error=False,
        )
        try:
            res = FirebaseLoginService(session_store=self._store).sign_in_or_up(
                email=email, password=pw, create_account=create_account, share_code=code
            )
        except RuntimeError as exc:
            self._set_busy(False)
            self._set_status(auth_error_message(exc))
            return

        wid = res.session.workspace_id
        # Before saving the profile: only the first account on this computer
        # inherits data typed while logged out.
        if res.created_workspace:
            try:
                from ..utils.app_paths import import_logged_out_data

                self.imported_files = import_logged_out_data(workspace_id=wid)
            except (OSError, *QT_ERRORS):
                self.imported_files = 0

        try:
            remember = bool(self._remember.isChecked())
            keychain_account = f"{email}|{wid}"
            if remember:
                set_password(account=keychain_account, password=pw)
            self._profiles.upsert_recent(
                workspace_id=wid,
                email=email,
                remember_password=remember,
                keychain_account=keychain_account if remember else "",
            )
        except QT_ERRORS:
            pass

        try:
            from ..models.firebase_movements_sync import FirebaseMovementsSyncService

            FirebaseMovementsSyncService().ensure_user_local_file(wid)
        except QT_ERRORS:
            pass

        self.result_info = res
        self.accept()


def run_welcome(
    parent: Optional[QWidget] = None, *, allow_cancel: bool = False, prefill_email: str = ""
) -> Optional[WelcomeDialog]:
    """Show the welcome screen; returns the accepted dialog, or None if closed."""
    dlg = WelcomeDialog(parent, allow_cancel=allow_cancel, prefill_email=prefill_email)
    if dlg.exec() and dlg.result_info is not None:
        return dlg
    return None
