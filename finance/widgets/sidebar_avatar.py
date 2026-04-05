from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..qt import (
    QWidget,
    QVBoxLayout,
    QLabel,
    Qt,
    QPixmap,
    QToolButton,
    QHBoxLayout,
)
from ..models.user import UserProfile
from ..data.user_profile_store import UserProfileStore
from ..utils.app_paths import avatars_data_dir
from ..models.firebase_session import FirebaseSessionStore
from ..models.firebase_login_service import FirebaseLoginService
from ..models.firebase_movements_sync import FirebaseMovementsSyncService
from ..models.firebase_workspace_profiles import (
    FirebaseWorkspaceProfilesStore,
    WorkspaceProfile,
)
from ..models.keychain_passwords import get_password
from ..ui.firebase_account_dialogs import (
    open_firebase_account_dialog,
    open_firebase_password_prompt,
    run_pull_sync_with_progress,
)
from .collapsible_section import CollapsibleButtonList


class SidebarAvatar:
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
        self._name_row: Optional[QWidget] = None
        self._firebase_menu_btn: Optional[QToolButton] = None
        self._firebase_accounts_list: Optional[CollapsibleButtonList] = None

        self._setup()

    def _setup(self) -> None:
        self._avatar_label = QLabel(self._parent)
        self._avatar_label.setObjectName("AvatarCircle")
        display_name = self._current_display_name() or self._user.full_name
        initial = (display_name or " ")[0]
        self._avatar_label.setText(initial)
        try:
            self._avatar_label.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass

        # Name row (label + account dropdown arrow)
        self._name_row = QWidget(self._parent)
        name_row_l = QHBoxLayout(self._name_row)
        name_row_l.setContentsMargins(0, 0, 0, 0)
        name_row_l.setSpacing(6)

        display_name = self._current_display_name() or self._user.full_name
        self._name_label = QLabel(f"שלום, {display_name}", self._name_row)
        self._name_label.setObjectName("UserName")
        try:
            self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        self._firebase_menu_btn = QToolButton(self._name_row)
        self._firebase_menu_btn.setObjectName("FirebaseAccountMenuButton")
        try:
            from ..utils.icons import make_icon
            from ..qt import QSize
            self._firebase_menu_btn.setIcon(make_icon("chevron_down", size=14))
            self._firebase_menu_btn.setIconSize(QSize(14, 14))
            self._firebase_menu_btn.setText("")
        except Exception:
            self._firebase_menu_btn.setText("▾")
        try:
            self._firebase_menu_btn.setToolTip("החלף חשבון שיתוף")
        except Exception:
            pass
        try:
            self._firebase_menu_btn.setCheckable(True)
            self._firebase_menu_btn.setChecked(False)
        except Exception:
            pass

        name_row_l.addStretch(1)
        name_row_l.addWidget(self._firebase_menu_btn, 0)
        name_row_l.addWidget(self._name_label, 0)
        name_row_l.addStretch(1)

        self._layout.addWidget(self._avatar_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._layout.addWidget(self._name_row, 0, Qt.AlignmentFlag.AlignHCenter)

        # In-sidebar expandable list of Firebase accounts (header hidden)
        self._firebase_accounts_list = CollapsibleButtonList(
            self._parent,
            title="",
            header_object_name="SidebarNavButton",
        )
        self._firebase_accounts_list.set_header_visible(False)
        self._firebase_accounts_list.set_arrow_visible(False)
        self._firebase_accounts_list.set_expanded(False)
        self._layout.addWidget(self._firebase_accounts_list)
        self._reload_firebase_accounts_list()

        self._layout.addSpacing(24)

        self._avatar_label.mousePressEvent = self._on_avatar_clicked
        if self._firebase_menu_btn is not None:
            self._firebase_menu_btn.clicked.connect(self._toggle_firebase_accounts_list)

        self._apply_current_avatar()

    def _toggle_firebase_accounts_list(self) -> None:
        lst = self._firebase_accounts_list
        btn = self._firebase_menu_btn
        if lst is None or btn is None:
            return
        new_expanded = not bool(lst.is_expanded())
        lst.set_expanded(bool(new_expanded))
        try:
            btn.setChecked(bool(new_expanded))
        except Exception:
            pass
        try:
            from ..utils.icons import make_icon
            from ..qt import QSize
            icon_name = "chevron_up" if new_expanded else "chevron_down"
            btn.setIcon(make_icon(icon_name, size=14))
            btn.setIconSize(QSize(14, 14))
            btn.setText("")
        except Exception:
            btn.setText("▴" if new_expanded else "▾")

    def _reload_firebase_accounts_list(self) -> None:
        lst = self._firebase_accounts_list
        if lst is None:
            return

        session_store = FirebaseSessionStore()
        profiles_store = FirebaseWorkspaceProfilesStore()
        s = session_store.load()
        wid_now = str(getattr(s, "workspace_id", "") or "").strip()
        email_now = str(getattr(s, "email", "") or "").strip()

        try:
            parent = self._parent.window()
        except Exception:
            parent = self._parent

        def _force_relogin_to_workspace(*, workspace_id: str, email: str = "") -> None:
            cur = session_store.load()
            cur.workspace_id = str(workspace_id or "").strip()
            if email:
                cur.email = str(email or "").strip()
            cur.uid = ""
            cur.id_token = ""
            cur.refresh_token = ""
            cur.expires_at = 0.0
            session_store.save(cur)
            try:
                FirebaseMovementsSyncService().ensure_user_local_file(
                    str(cur.workspace_id or "")
                )
            except Exception:
                pass

        def _connect_profile(p: WorkspaceProfile) -> None:
            _force_relogin_to_workspace(
                workspace_id=str(p.workspace_id or ""), email=str(p.email or "")
            )

            # If password is stored, auto-connect; otherwise open the dialog.
            try:
                if (
                    bool(getattr(p, "remember_password", False))
                    and str(getattr(p, "keychain_account", "") or "").strip()
                ):
                    acct = str(getattr(p, "keychain_account", "") or "").strip()
                    pw = get_password(account=acct) if acct else ""
                    email = str(getattr(p, "email", "") or "").strip()
                    wid = str(getattr(p, "workspace_id", "") or "").strip()
                    if email and wid and pw:
                        FirebaseLoginService(
                            session_store=session_store
                        ).login_with_email_password(
                            email=email, password=pw, workspace_id=wid
                        )
                        run_pull_sync_with_progress(parent=parent)
                        self._reload_firebase_accounts_list()
                        self._toggle_firebase_accounts_list()
                        return
            except Exception:
                pass

            ok = open_firebase_password_prompt(
                parent=parent,
                session_store=session_store,
                profiles_store=profiles_store,
                profile=p,
            )
            if ok:
                self._reload_firebase_accounts_list()
                self._toggle_firebase_accounts_list()

        def _add_account() -> None:
            ok = open_firebase_account_dialog(
                parent=parent,
                session_store=session_store,
                profiles_store=profiles_store,
                profile=None,
                prefill_email=email_now,
                prefill_workspace_id=wid_now,
            )
            if ok:
                self._reload_firebase_accounts_list()
                self._toggle_firebase_accounts_list()

        def _mk_connect_handler(prof: WorkspaceProfile):
            # Important for type-checking: return a true no-arg callable.
            return lambda: _connect_profile(prof)

        items = []
        try:
            profiles = profiles_store.list_profiles()
        except Exception:
            profiles = []

        for p in profiles:
            label = (
                str(p.name or "").strip()
                or str(p.workspace_id or "").strip()
                or "Workspace"
            )
            if wid_now and str(p.workspace_id).strip() == wid_now:
                label = f"✓ {label}"
            items.append((label, _mk_connect_handler(p)))

        items.append(("＋ הוסף חשבון…", _add_account))
        lst.set_items(items)

    def _current_workspace_id(self) -> str:
        try:
            wid = str(FirebaseSessionStore().load().workspace_id or "").strip()
            return wid
        except Exception:
            return ""

    def _current_display_name(self) -> str:
        wid = self._current_workspace_id()
        if not wid:
            return ""
        try:
            p = FirebaseWorkspaceProfilesStore().find_by_workspace_id(workspace_id=wid)
            if p is None:
                return ""
            return str(getattr(p, "display_name", "") or "").strip()
        except Exception:
            return ""

    def _current_avatar_path(self) -> str:
        wid = self._current_workspace_id()
        if not wid:
            return ""
        try:
            p = FirebaseWorkspaceProfilesStore().find_by_workspace_id(workspace_id=wid)
            if p is None:
                return ""
            ap = str(getattr(p, "avatar_path", "") or "").strip()
            return ap
        except Exception:
            return ""

    def _apply_current_avatar(self) -> None:
        path = self._current_avatar_path()
        if path:
            if self.set_avatar_from_path(path, save_as_workspace_avatar=False):
                return
        if self._user.avatar_path:
            self.set_avatar_from_path(
                self._user.avatar_path, save_as_workspace_avatar=False
            )

    def _on_avatar_clicked(self, event) -> None:
        QFileDialogCls = None
        try:
            import importlib

            QtWidgets = importlib.import_module("PySide6.QtWidgets")
            QFileDialogCls = getattr(QtWidgets, "QFileDialog", None)
        except Exception:
            try:
                import importlib

                QtWidgets = importlib.import_module("PyQt6.QtWidgets")
                QFileDialogCls = getattr(QtWidgets, "QFileDialog", None)
            except Exception:
                QFileDialogCls = None
        if QFileDialogCls is None:
            return

        file_name, _ = QFileDialogCls.getOpenFileName(
            self._parent,
            "בחר תמונת פרופיל",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)",
        )
        if not file_name:
            return

        wid = self._current_workspace_id()
        if wid:
            if self.set_avatar_from_path(file_name, save_as_workspace_avatar=True):
                try:
                    FirebaseWorkspaceProfilesStore().update_ui_prefs(
                        workspace_id=wid,
                        avatar_path=str(avatars_data_dir() / f"user_avatar_{wid}.png"),
                    )
                except Exception:
                    pass
            return

        if self.set_avatar_from_path(file_name, save_as_workspace_avatar=False):
            try:
                self._store.save(self._user)
            except Exception:
                pass

    def set_avatar_from_path(
        self, file_name: Optional[str], *, save_as_workspace_avatar: bool = False
    ) -> bool:
        if not file_name or not self._avatar_label:
            return False

        src_path = Path(file_name)
        if not src_path.exists():
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

        try:
            if save_as_workspace_avatar:
                wid = self._current_workspace_id()
                target_path = avatars_data_dir() / f"user_avatar_{wid}.png"
                pix.save(str(target_path), "PNG")
            else:
                target_path = avatars_data_dir() / "user_avatar.png"
                pix.save(str(target_path), "PNG")
                self._user.avatar_path = str(target_path)
        except Exception:
            target_path = src_path

        url = Path(str(target_path)).as_posix()
        radius = size // 2
        self._avatar_label.setFixedSize(size, size)
        self._avatar_label.setPixmap(QPixmap())
        self._avatar_label.setStyleSheet(
            f"""
            QLabel {{
                width: {size}px;
                height: {size}px;
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
        if not self._name_label or not self._avatar_label:
            return

        display_name = self._current_display_name() or self._user.full_name
        self._name_label.setText(f"שלום, {display_name}")

        self._apply_current_avatar()

        if not self._current_avatar_path() and not self._user.avatar_path:
            initial = (display_name or " ")[0]
            self._avatar_label.setText(initial)
        try:
            self._reload_firebase_accounts_list()
        except Exception:
            pass
