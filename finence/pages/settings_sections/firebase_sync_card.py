from __future__ import annotations

import secrets
import string

from ...qt import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...models.firebase_session import FirebaseSessionStore
from ...models.firebase_login_service import FirebaseLoginService
from ...models.firebase_workspace_service import FirebaseWorkspaceService
from ...models.firebase_movements_sync import FirebaseMovementsSyncService


class FirebaseSyncCard(QWidget):
    def __init__(self, *, parent: QWidget, store: FirebaseSessionStore) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
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
        self._store = store
        self._build()

    def _random_workspace_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        raw = "".join(secrets.choice(alphabet) for _ in range(12))
        return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"

    def _build(self) -> None:
        fb_l = QVBoxLayout(self)
        fb_l.setContentsMargins(24, 24, 24, 24)
        fb_l.setSpacing(10)

        fb_title = QLabel("שיתוף וסנכרון", self)
        try:
            fb_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        fb_l.addWidget(fb_title)

        session = self._store.load()

        email_edit = QLineEdit(self)
        email_edit.setPlaceholderText("אימייל (Firebase)")
        email_edit.setText(session.email or "")

        password_edit = QLineEdit(self)
        password_edit.setPlaceholderText("סיסמה (Firebase)")
        try:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            try:
                password_edit.setEchoMode(QLineEdit.Password)
            except Exception:
                pass

        project_row = QHBoxLayout()
        project_row.setSpacing(10)
        project_lbl = QLabel("", self)
        project_lbl.setObjectName("Subtitle")
        change_project_btn = QPushButton("שנה פרויקט", self)
        project_row.addWidget(project_lbl, 1)
        project_row.addWidget(change_project_btn, 0)
        fb_l.addLayout(project_row)

        fb_l.addWidget(email_edit)
        fb_l.addWidget(password_edit)

        workspace_edit = QLineEdit(self)
        workspace_edit.setPlaceholderText("קוד שיתוף (Workspace)")
        try:
            workspace_edit.setText(str(getattr(session, "workspace_id", "") or ""))
        except Exception:
            workspace_edit.setText("")
        fb_l.addWidget(workspace_edit)

        fb_status = QLabel("", self)
        fb_status.setObjectName("Subtitle")
        fb_l.addWidget(fb_status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        login_btn = QPushButton("התחבר", self)
        login_btn.setObjectName("SaveButton")
        create_ws_btn = QPushButton("צור קוד", self)
        join_ws_btn = QPushButton("הצטרף", self)
        clear_ws_btn = QPushButton("נתק שיתוף", self)
        logout_btn = QPushButton("התנתק", self)
        btn_row.addWidget(login_btn)
        btn_row.addWidget(create_ws_btn)
        btn_row.addWidget(join_ws_btn)
        btn_row.addWidget(clear_ws_btn)
        btn_row.addWidget(logout_btn)
        btn_row.addStretch(1)
        fb_l.addLayout(btn_row)

        def refresh_status() -> None:
            s = self._store.load()
            try:
                pid = str(getattr(s, "project_id", "") or "").strip()
            except Exception:
                pid = ""
            project_lbl.setText(f"פרויקט: {pid}" if pid else "פרויקט: לא הוגדר")
            try:
                has_api = bool(str(getattr(s, "api_key", "") or "").strip())
                has_pid = bool(pid)
                change_project_btn.setEnabled(True)
                if not (has_api and has_pid):
                    change_project_btn.setText("הגדר פרויקט")
                else:
                    change_project_btn.setText("שנה פרויקט")
            except Exception:
                pass
            if s.is_logged_in:
                wid = str(getattr(s, "workspace_id", "") or "").strip()
                if wid:
                    fb_status.setText(f"מחובר: {s.email} | שיתוף: {wid}")
                else:
                    fb_status.setText(f"מחובר: {s.email} | ללא שיתוף")
            else:
                fb_status.setText("לא מחובר")

        def edit_project_settings() -> None:
            s = self._store.load()
            dlg = QDialog(self)
            dlg.setWindowTitle("הגדרת פרויקט Firebase")
            try:
                dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    dlg.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            lay = QVBoxLayout(dlg)
            lay.setContentsMargins(24, 20, 24, 20)
            lay.setSpacing(10)

            info = QLabel(
                "השדות האלו הם טכניים. בדרך כלל מגדירים אותם פעם אחת.\n"
                "אם תשנה אותם תצטרך להתחבר מחדש.",
                dlg,
            )
            info.setWordWrap(True)
            lay.addWidget(info)

            api_key_edit = QLineEdit(dlg)
            api_key_edit.setPlaceholderText("Firebase API Key")
            api_key_edit.setText(str(getattr(s, "api_key", "") or ""))
            project_id_edit = QLineEdit(dlg)
            project_id_edit.setPlaceholderText("Firebase Project ID")
            project_id_edit.setText(str(getattr(s, "project_id", "") or ""))
            lay.addWidget(api_key_edit)
            lay.addWidget(project_id_edit)

            row = QHBoxLayout()
            row.setSpacing(10)
            cancel_btn = QPushButton("ביטול", dlg)
            save_btn = QPushButton("שמור", dlg)
            save_btn.setObjectName("SaveButton")
            row.addWidget(cancel_btn)
            row.addStretch(1)
            row.addWidget(save_btn)
            lay.addLayout(row)

            cancel_btn.clicked.connect(dlg.reject)

            def _save_project() -> None:
                api_key = api_key_edit.text().strip()
                project_id = project_id_edit.text().strip()
                if not api_key or not project_id:
                    fb_status.setText("חובה למלא API key ו-project id")
                    return
                s.api_key = api_key
                s.project_id = project_id
                s.uid = ""
                s.id_token = ""
                s.refresh_token = ""
                s.expires_at = 0.0
                self._store.save(s)
                dlg.accept()
                refresh_status()

            save_btn.clicked.connect(_save_project)
            dlg.exec()

        def do_login() -> None:
            current = self._store.load()
            api_key = str(getattr(current, "api_key", "") or "").strip()
            project_id = str(getattr(current, "project_id", "") or "").strip()
            email = email_edit.text().strip()
            pw = password_edit.text()
            if not api_key or not project_id:
                fb_status.setText(
                    "חובה להגדיר פרויקט (API key + project id) לפני התחברות"
                )
                return
            if not email or not pw:
                fb_status.setText("חובה למלא אימייל וסיסמה")
                return
            fb_status.setText("מתחבר...")
            QApplication.processEvents()
            try:
                FirebaseLoginService(
                    session_store=self._store
                ).login_with_email_password(
                    email=email,
                    password=pw,
                    workspace_id=workspace_edit.text().strip(),
                )
            except Exception as e:
                fb_status.setText(f"שגיאת התחברות: {str(e)}")
                return
            refresh_status()

        def do_create_workspace() -> None:
            s = self._store.load()
            if not s.is_logged_in:
                fb_status.setText("יש להתחבר לפני יצירת שיתוף")
                return
            code = self._random_workspace_code()
            fb_status.setText("יוצר שיתוף...")
            QApplication.processEvents()
            try:
                FirebaseWorkspaceService(session_store=self._store).create_workspace(
                    workspace_id=code
                )
                workspace_edit.setText(code)
                fb_status.setText(f"שיתוף נוצר. קוד: {code}")
                try:
                    FirebaseMovementsSyncService().ensure_user_local_file(code)
                except Exception:
                    pass
            except Exception as e:
                fb_status.setText(f"שגיאת שיתוף: {str(e)}")
                return
            refresh_status()

        def do_join_workspace() -> None:
            s = self._store.load()
            if not s.is_logged_in:
                fb_status.setText("יש להתחבר לפני הצטרפות לשיתוף")
                return
            code = workspace_edit.text().strip()
            if not code:
                fb_status.setText("יש להזין קוד שיתוף")
                return
            fb_status.setText("מצטרף לשיתוף...")
            QApplication.processEvents()
            try:
                FirebaseWorkspaceService(session_store=self._store).join_workspace(
                    workspace_id=code, role="editor"
                )
                fb_status.setText(f"הצטרפת לשיתוף: {code}")
                try:
                    FirebaseMovementsSyncService().ensure_user_local_file(code)
                except Exception:
                    pass
            except Exception as e:
                fb_status.setText(f"שגיאת שיתוף: {str(e)}")
                return
            refresh_status()

        def do_clear_workspace() -> None:
            s = self._store.load()
            if not s.is_logged_in:
                workspace_edit.setText("")
                return
            try:
                FirebaseWorkspaceService(
                    session_store=self._store
                ).disconnect_workspace_local()
            except Exception:
                s.workspace_id = ""
                self._store.save(s)
            workspace_edit.setText("")
            fb_status.setText("שיתוף נותק (מקומי בלבד)")
            refresh_status()

        def do_logout() -> None:
            self._store.clear()
            refresh_status()

        login_btn.clicked.connect(do_login)
        create_ws_btn.clicked.connect(do_create_workspace)
        join_ws_btn.clicked.connect(do_join_workspace)
        clear_ws_btn.clicked.connect(do_clear_workspace)
        logout_btn.clicked.connect(do_logout)
        change_project_btn.clicked.connect(edit_project_settings)

        refresh_status()
