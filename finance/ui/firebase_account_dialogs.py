from __future__ import annotations

from typing import Optional, Callable

from ..qt import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    Qt,
    QTimer,
    QVBoxLayout,
    QWidget,
)
from ..models.firebase_login_service import FirebaseLoginService
from ..models.firebase_movements_sync import FirebaseMovementsSyncService
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_workspace_profiles import (
    FirebaseWorkspaceProfilesStore,
    WorkspaceProfile,
)
from ..models.keychain_passwords import get_password, set_password


def _refresh_current_route(parent: Optional[QWidget]) -> None:
    try:
        win = parent.window() if parent is not None else None
    except Exception:
        win = None
    if win is None:
        try:
            win = QApplication.activeWindow()
        except Exception:
            win = None
    if win is None:
        return
    try:
        router = getattr(win, "router", None)
        if router is None:
            return
        current = getattr(router, "current_route", None)
        nav = getattr(router, "navigate", None)
        if not callable(current) or not callable(nav):
            return
        route = current() or "home"
        # Reset all cached page widgets so every page is rebuilt with the
        # new workspace's data after a user/workspace switch.
        try:
            reset_fn = getattr(router, "reset", None)
            if callable(reset_fn):
                reset_fn()
        except Exception:
            pass
        nav(route)
    except Exception:
        return


def run_pull_sync_with_progress(
    *, parent: Optional[QWidget], on_done: Optional[Callable[[], None]] = None
) -> None:
    progress = QDialog(parent)
    progress.setWindowTitle("מסנכרן…")
    try:
        progress.setModal(True)
    except Exception:
        pass
    try:
        progress.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    except Exception:
        pass
    try:
        progress.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            progress.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

    pl = QVBoxLayout(progress)
    pl.setContentsMargins(32, 24, 32, 24)
    pl.setSpacing(12)
    lbl = QLabel("מושך נתונים מהענן…", progress)
    lbl.setWordWrap(True)
    pl.addWidget(lbl)
    bar = QProgressBar(progress)
    try:
        bar.setRange(0, 0)
    except Exception:
        pass
    pl.addWidget(bar)

    done = {"finished": False, "pulled": 0, "err": ""}

    def _worker() -> None:
        try:
            pulled, _ = FirebaseMovementsSyncService().sync_now(allow_push=False)
            done["finished"] = True
            done["pulled"] = int(pulled)
        except Exception as e:
            done["finished"] = True
            done["err"] = str(e)

    try:
        import threading

        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        _worker()

    def _poll() -> None:
        if bool(done.get("finished")):
            err = str(done.get("err") or "").strip()
            try:
                progress.accept()
            except Exception:
                try:
                    progress.close()
                except Exception:
                    pass
            if err:
                try:
                    from ..qt import QMessageBox
                    QMessageBox.warning(
                        parent,
                        "שגיאת סנכרון",
                        f"הסנכרון נכשל: {err}",
                    )
                except Exception:
                    pass
            else:
                try:
                    _refresh_current_route(parent)
                except Exception:
                    pass
                if on_done is not None:
                    try:
                        _ctx = parent if parent is not None else progress
                        QTimer.singleShot(0, _ctx, on_done)
                    except Exception:
                        try:
                            on_done()
                        except Exception:
                            pass
            return
        try:
            QTimer.singleShot(120, _poll)
        except Exception:
            _poll()

    try:
        QTimer.singleShot(120, _poll)
    except Exception:
        pass
    progress.exec()


def open_firebase_account_dialog(
    *,
    parent: Optional[QWidget],
    session_store: FirebaseSessionStore,
    profiles_store: FirebaseWorkspaceProfilesStore,
    profile: Optional[WorkspaceProfile] = None,
    prefill_email: str = "",
    prefill_workspace_id: str = "",
) -> bool:
    dlg = QDialog(parent)
    dlg.setWindowTitle("פרטי חשבון")
    try:
        dlg.setModal(True)
    except Exception:
        pass
    try:
        dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    except Exception:
        pass
    try:
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            dlg.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(32, 24, 32, 24)
    lay.setSpacing(16)

    header = QLabel("פרטי חשבון", dlg)
    header.setObjectName("HeaderTitle")
    try:
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    except Exception:
        pass
    lay.addWidget(header)

    def _make_row(label_text: str):
        row = QHBoxLayout()
        row.setSpacing(8)
        lbl = QLabel(label_text, dlg)
        lbl.setObjectName("StatTitle")
        lbl.setMinimumWidth(90)
        edit = QLineEdit(dlg)
        edit.setObjectName("SettingsInput")
        try:
            edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                edit.setLayoutDirection(Qt.LeftToRight)
            except Exception:
                pass
        row.addWidget(lbl, 0)
        row.addWidget(edit, 1)
        return row, edit

    name_row, profile_name_edit = _make_row("שם:")
    email_row, email_edit = _make_row("אימייל:")
    pw_row, password_edit = _make_row("סיסמה:")
    try:
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
    except Exception:
        try:
            password_edit.setEchoMode(QLineEdit.Password)
        except Exception:
            pass
    ws_row, workspace_edit = _make_row("Workspace:")

    remember_pw_cb = QCheckBox("זכור סיסמה (Keychain)", dlg)
    remember_pw_cb.setChecked(False)

    status = QLabel("", dlg)
    status.setObjectName("ErrorLabel")
    status.setWordWrap(True)
    status.setMinimumHeight(0)
    status.setMaximumHeight(80)
    status.hide()

    lay.addLayout(name_row)
    lay.addLayout(email_row)
    lay.addLayout(pw_row)
    lay.addWidget(remember_pw_cb)
    lay.addLayout(ws_row)
    lay.addWidget(status)

    if profile is not None:
        profile_name_edit.setText(str(profile.name or ""))
        email_edit.setText(str(profile.email or prefill_email or ""))
        workspace_edit.setText(str(profile.workspace_id or prefill_workspace_id or ""))
        remember_pw_cb.setChecked(bool(getattr(profile, "remember_password", False)))
        try:
            acct = str(getattr(profile, "keychain_account", "") or "").strip()
            if acct and bool(getattr(profile, "remember_password", False)):
                pw = get_password(account=acct)
                if pw:
                    password_edit.setText(pw)
        except Exception:
            pass
    else:
        email_edit.setText(str(prefill_email or ""))
        workspace_edit.setText(str(prefill_workspace_id or ""))

    btns = QHBoxLayout()
    btns.setSpacing(12)
    connect_btn = QPushButton("התחבר", dlg)
    connect_btn.setObjectName("SaveButton")
    try:
        connect_btn.setDefault(True)
    except Exception:
        pass
    cancel_btn = QPushButton("ביטול", dlg)
    btns.addWidget(connect_btn)
    btns.addStretch(1)
    btns.addWidget(cancel_btn)
    lay.addLayout(btns)

    cancel_btn.clicked.connect(dlg.reject)

    result = {"ok": False}

    def _set_status(text: str) -> None:
        try:
            status.setText(text)
            status.setMinimumHeight(40)
            status.show()
        except Exception:
            pass

    def do_connect() -> None:
        current = session_store.load()
        api_key = str(getattr(current, "api_key", "") or "").strip()
        project_id = str(getattr(current, "project_id", "") or "").strip()
        email = email_edit.text().strip()
        pw = password_edit.text()
        wid = workspace_edit.text().strip()

        if not api_key or not project_id:
            _set_status("חובה להגדיר פרויקט (API key + project id) לפני התחברות")
            return
        if not email or not pw:
            _set_status("חובה למלא אימייל וסיסמה")
            return
        if not wid:
            _set_status("חובה למלא Workspace")
            return

        _set_status("מתחבר…")
        try:
            QApplication.processEvents()
        except Exception:
            pass

        try:
            FirebaseLoginService(session_store=session_store).login_with_email_password(
                email=email,
                password=pw,
                workspace_id=wid,
            )
        except Exception as e:
            _set_status(f"שגיאת התחברות: {str(e)}")
            return

        try:
            remember = bool(remember_pw_cb.isChecked())
            keychain_account = f"{email}|{wid}"
            if remember:
                set_password(account=keychain_account, password=pw)

            name = profile_name_edit.text().strip()
            if name:
                profiles_store.upsert(
                    name=name,
                    workspace_id=wid,
                    email=email,
                    remember_password=remember,
                    keychain_account=keychain_account if remember else "",
                )
            else:
                profiles_store.upsert_recent(
                    workspace_id=wid,
                    email=email,
                    remember_password=remember,
                    keychain_account=keychain_account if remember else "",
                )
        except Exception:
            pass

        try:
            FirebaseMovementsSyncService().ensure_user_local_file(str(wid or ""))
        except Exception:
            pass

        run_pull_sync_with_progress(parent=parent)
        result["ok"] = True
        try:
            dlg.accept()
        except Exception:
            pass

    connect_btn.clicked.connect(do_connect)
    dlg.exec()
    return bool(result.get("ok"))


def open_firebase_password_prompt(
    *,
    parent: Optional[QWidget],
    session_store: FirebaseSessionStore,
    profiles_store: FirebaseWorkspaceProfilesStore,
    profile: WorkspaceProfile,
) -> bool:
    email = str(getattr(profile, "email", "") or "").strip()
    wid = str(getattr(profile, "workspace_id", "") or "").strip()
    if not email or not wid:
        return False

    dlg = QDialog(parent)
    dlg.setWindowTitle("התחברות")
    try:
        dlg.setModal(True)
    except Exception:
        pass
    try:
        dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
    except Exception:
        pass
    try:
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except Exception:
        try:
            dlg.setLayoutDirection(Qt.RightToLeft)
        except Exception:
            pass

    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(32, 24, 32, 24)
    lay.setSpacing(12)

    header = QLabel("התחברות לחשבון", dlg)
    header.setObjectName("HeaderTitle")
    try:
        header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    except Exception:
        pass
    lay.addWidget(header)

    info = QLabel(
        f"{str(getattr(profile, 'name', '') or '').strip() or email}\n{wid}", dlg
    )
    info.setWordWrap(True)
    try:
        info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    except Exception:
        pass
    lay.addWidget(info)

    pw_row = QHBoxLayout()
    pw_row.setSpacing(8)
    pw_lbl = QLabel("סיסמה:", dlg)
    pw_lbl.setObjectName("StatTitle")
    pw = QLineEdit(dlg)
    pw.setObjectName("SettingsInput")
    try:
        pw.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    except Exception:
        try:
            pw.setLayoutDirection(Qt.LeftToRight)
        except Exception:
            pass
    try:
        pw.setEchoMode(QLineEdit.EchoMode.Password)
    except Exception:
        try:
            pw.setEchoMode(QLineEdit.Password)
        except Exception:
            pass
    pw_row.addWidget(pw_lbl, 0)
    pw_row.addWidget(pw, 1)
    lay.addLayout(pw_row)

    remember = QCheckBox("זכור סיסמה (Keychain)", dlg)
    remember.setChecked(True)
    lay.addWidget(remember)

    status = QLabel("", dlg)
    status.setObjectName("ErrorLabel")
    status.setWordWrap(True)
    status.hide()
    lay.addWidget(status)

    btns = QHBoxLayout()
    btns.setSpacing(12)
    connect_btn = QPushButton("התחבר", dlg)
    connect_btn.setObjectName("SaveButton")
    try:
        connect_btn.setDefault(True)
    except Exception:
        pass
    cancel_btn = QPushButton("ביטול", dlg)
    btns.addWidget(connect_btn)
    btns.addStretch(1)
    btns.addWidget(cancel_btn)
    lay.addLayout(btns)

    cancel_btn.clicked.connect(dlg.reject)

    result = {"ok": False}

    def _set_status(text: str) -> None:
        try:
            status.setText(text)
            status.show()
        except Exception:
            pass

    def _do_connect() -> None:
        current = session_store.load()
        api_key = str(getattr(current, "api_key", "") or "").strip()
        project_id = str(getattr(current, "project_id", "") or "").strip()
        password = pw.text()
        if not api_key or not project_id:
            _set_status("חובה להגדיר פרויקט (API key + project id) לפני התחברות")
            return
        if not password:
            _set_status("חובה למלא סיסמה")
            return

        _set_status("מתחבר…")
        try:
            QApplication.processEvents()
        except Exception:
            pass

        try:
            FirebaseLoginService(session_store=session_store).login_with_email_password(
                email=email,
                password=password,
                workspace_id=wid,
            )
        except Exception as e:
            _set_status(f"שגיאת התחברות: {str(e)}")
            return

        try:
            keychain_account = f"{email}|{wid}"
            if bool(remember.isChecked()):
                set_password(account=keychain_account, password=password)
                profiles_store.upsert(
                    name=str(getattr(profile, "name", "") or "").strip() or email,
                    workspace_id=wid,
                    email=email,
                    remember_password=True,
                    keychain_account=keychain_account,
                )
            else:
                profiles_store.touch(
                    name=str(getattr(profile, "name", "") or "").strip() or email
                )
        except Exception:
            pass

        try:
            FirebaseMovementsSyncService().ensure_user_local_file(str(wid or ""))
        except Exception:
            pass

        run_pull_sync_with_progress(parent=parent)
        result["ok"] = True
        try:
            dlg.accept()
        except Exception:
            pass

    connect_btn.clicked.connect(_do_connect)
    dlg.exec()
    return bool(result.get("ok"))
