from __future__ import annotations

from ...qt import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from ...models.firebase_session import FirebaseSessionStore
from ...models.firebase_workspace_profiles import FirebaseWorkspaceProfilesStore
from ...ui.firebase_account_dialogs import run_pull_sync_with_progress
from ...models.workspace_local_cache_reset import reset_workspace_local_cache
from ...utils.safe import QT_ERRORS


class FirebaseSyncCard(QWidget):
    def __init__(self, *, parent: object, store: FirebaseSessionStore) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except QT_ERRORS:
                pass
        self._store = store
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("שיתוף וסנכרון", self)
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except QT_ERRORS:
            pass
        layout.addWidget(title)
        layout.addSpacing(8)

        profiles_store = FirebaseWorkspaceProfilesStore()
        s = self._store.load()
        wid_now = str(getattr(s, "workspace_id", "") or "").strip()
        email_now = str(getattr(s, "email", "") or "").strip()
        logged_in = bool(getattr(s, "is_logged_in", False))

        current_name = ""
        try:
            for p in profiles_store.list_profiles():
                if (
                    str(getattr(p, "workspace_id", "") or "").strip() == wid_now
                    and wid_now
                    and str(getattr(p, "email", "") or "").strip().casefold()
                    == email_now.casefold()
                ):
                    current_name = str(getattr(p, "name", "") or "").strip()
                    break
        except QT_ERRORS:
            current_name = ""

        def _row(label: str, value: str) -> None:
            r = QHBoxLayout()
            r.setSpacing(8)
            lambda_layout = QLabel(label, self)
            lambda_layout.setObjectName("StatTitle")
            v = QLabel(value, self)
            v.setObjectName("StatValue")
            v.setWordWrap(True)
            r.addWidget(lambda_layout, 0)
            r.addWidget(QLabel("-", self), 0)
            r.addWidget(v, 1)
            layout.addLayout(r)

        _row("חשבון", current_name or (wid_now or "לא נבחר"))
        _row("אימייל", email_now or "—")
        if wid_now:
            # The share code: the only thing needed to share this budget.
            code_row = QHBoxLayout()
            code_row.setSpacing(8)
            code_title = QLabel("קוד שיתוף", self)
            code_title.setObjectName("StatTitle")
            code_val = QLabel(wid_now, self)
            code_val.setObjectName("StatValue")
            try:
                code_val.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
            except QT_ERRORS:
                pass
            copy_btn = QPushButton("העתק", self)
            copy_btn.setObjectName("SecondaryButton")

            def _copy_code() -> None:
                try:
                    from ...qt import QApplication

                    cb = QApplication.clipboard()
                    if cb is not None:
                        cb.setText(wid_now)
                    copy_btn.setText("הועתק ✓")
                except QT_ERRORS:
                    pass

            copy_btn.clicked.connect(_copy_code)
            code_row.addWidget(code_title, 0)
            code_row.addWidget(QLabel("-", self), 0)
            code_row.addWidget(code_val, 1)
            code_row.addWidget(copy_btn, 0)
            layout.addLayout(code_row)
            hint = QLabel(
                "רוצה לשתף את התקציב? שלח את הקוד לבן/בת הזוג. "
                "בהתחברות שלהם יבחרו \"יש לי קוד שיתוף\" ויזינו אותו.",
                self,
            )
            hint.setWordWrap(True)
            layout.addWidget(hint)
        _row("סטטוס", "מחובר" if logged_in else "לא מחובר")

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        connect_btn = QPushButton("החלף חשבון / הצטרף לתקציב משותף", self)
        connect_btn.setObjectName("SaveButton")
        btn_row.addWidget(connect_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        danger_row = QHBoxLayout()
        danger_row.setSpacing(12)
        reset_btn = QPushButton("אפס נתונים מקומיים", self)
        reset_btn.setObjectName("SecondaryButton")
        try:
            reset_btn.setToolTip("מוחק קבצי מטמון מקומיים עבור ה-Workspace הנוכחי")
        except QT_ERRORS:
            pass
        danger_row.addWidget(reset_btn)
        danger_row.addStretch(1)
        layout.addLayout(danger_row)

        def _open_current_dialog() -> None:
            parent = None
            try:
                parent = self.window()
            except QT_ERRORS:
                parent = None
            from ...ui.welcome_dialog import run_welcome

            if run_welcome(parent, allow_cancel=True, prefill_email=email_now) is not None:
                run_pull_sync_with_progress(parent=parent)

        connect_btn.clicked.connect(_open_current_dialog)

        def _confirm_and_reset() -> None:
            wid = str(getattr(self._store.load(), "workspace_id", "") or "").strip()
            if not wid:
                return
            parent = None
            try:
                parent = self.window()
            except QT_ERRORS:
                parent = None

            dlg = QDialog(parent)
            dlg.setWindowTitle("איפוס נתונים מקומיים")
            try:
                dlg.setModal(True)
            except QT_ERRORS:
                pass
            try:
                dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
            except QT_ERRORS:
                pass
            try:
                dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except QT_ERRORS:
                try:
                    dlg.setLayoutDirection(Qt.RightToLeft)
                except QT_ERRORS:
                    pass

            lambda_layout = QVBoxLayout(dlg)
            lambda_layout.setContentsMargins(28, 22, 28, 22)
            lambda_layout.setSpacing(12)
            msg = QLabel(
                "זה ימחק את קבצי המטמון המקומיים עבור ה-Workspace הזה בלבד.\n"
                "אחרי זה מומלץ לבצע סנכרון (Pull) כדי למשוך נתונים מהענן.\n\n"
                f"Workspace: {wid}",
                dlg,
            )
            msg.setWordWrap(True)
            lambda_layout.addWidget(msg)

            buttons = QHBoxLayout()
            buttons.setSpacing(12)
            ok = QPushButton("אפס", dlg)
            ok.setObjectName("SaveButton")
            cancel = QPushButton("ביטול", dlg)
            buttons.addWidget(ok)
            buttons.addStretch(1)
            buttons.addWidget(cancel)
            lambda_layout.addLayout(buttons)
            cancel.clicked.connect(dlg.reject)
            ok.clicked.connect(dlg.accept)

            if not dlg.exec():
                return

            try:
                reset_workspace_local_cache(workspace_id=wid)
            except QT_ERRORS:
                pass

            try:
                win = parent
                router = getattr(win, "router", None) if win is not None else None
                if router is not None:
                    if callable(getattr(router, "reset", None)):
                        router.reset()
                    if (
                        callable(getattr(router, "current_route", None))
                        and callable(getattr(router, "navigate", None))
                    ):
                        route = router.current_route() or "home"
                        router.navigate(route)
            except QT_ERRORS:
                pass

        reset_btn.clicked.connect(_confirm_and_reset)
