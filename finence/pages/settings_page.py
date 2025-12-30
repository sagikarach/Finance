from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QDialog,
    QListWidget,
    QStackedWidget,
    Qt,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QApplication,
    QIcon,
    QPixmap,
    QToolButton,
    QToolTip,
    QCursor,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts import BankAccount
from ..models.bank_settings import BankSettingsRowInput
from ..models.accounts_service import AccountsService
from ..models.notifications import RuleType
from ..models.update_service import UpdateService
from ..__version__ import __version__
from .base_page import BasePage
import os
import webbrowser
from ..models.firebase_session import FirebaseSessionStore, FirebaseSession
from ..models.firebase_client import FirebaseAuthClient, FirestoreClient
from ..models.firebase_movements_sync import FirebaseMovementsSyncService
import secrets
import string


class SettingsPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        get_previous_route: Optional[Callable[[], str]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="הגדרות",
            current_route="settings",
        )
        self._update_eye_icon: Optional[Callable[[], None]] = None
        self._get_previous_route = get_previous_route
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons = []
        back_btn = QToolButton(self)
        back_btn.setObjectName("IconButton")
        back_btn.setText("←")
        back_btn.setToolTip("חזרה")
        if self._navigate is not None:

            def go_back():
                previous = "home"
                if self._get_previous_route is not None:
                    previous = self._get_previous_route()
                self._navigate(previous)

            back_btn.clicked.connect(go_back)
        buttons.append(back_btn)
        return buttons

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if self._update_eye_icon is not None:
            self._update_eye_icon()

    def _build_bank_accounts_card(self) -> QWidget:
        card = QWidget(self)
        card.setObjectName("Sidebar")
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                card.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("ניהול חשבונות בנק", card)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)
        layout.addSpacing(8)

        default_account_names = ["בנק", "מזומן", "ביט", "פייבוקס"]

        bank_accounts: Dict[str, BankAccount] = {}
        if isinstance(self._provider, JsonFileAccountsProvider):
            try:
                all_accounts = self._provider.list_accounts()
                for acc in all_accounts:
                    if isinstance(acc, BankAccount):
                        bank_accounts[acc.name] = acc
            except Exception:
                pass

        account_widgets: Dict[str, Dict[str, Any]] = {}

        for account_name in default_account_names:
            account = bank_accounts.get(account_name)
            is_active = account.active if account else False
            current_amount = account.total_amount if account else 0.0

            account_row = QWidget(card)
            account_row_layout = QVBoxLayout(account_row)
            account_row_layout.setContentsMargins(0, 0, 0, 0)
            account_row_layout.setSpacing(4)

            active_checkbox = QCheckBox(account_name, account_row)
            active_checkbox.setChecked(is_active)

            amount_row = QHBoxLayout()
            amount_row.setSpacing(8)
            amount_label = QLabel("סכום התחלתי:", account_row)
            amount_edit = QLineEdit(account_row)
            try:
                amount_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    amount_edit.setLayoutDirection(Qt.RightToLeft)
                except Exception:
                    pass
            try:
                amount_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            except Exception:
                pass
            if account:
                amount_edit.setText(f"{current_amount:.2f}")
            amount_edit.setEnabled(is_active)
            amount_edit.setPlaceholderText("0.00")

            dash = QLabel("-", account_row)
            amount_row.addWidget(amount_label)
            amount_row.addWidget(dash)
            amount_row.addWidget(amount_edit, 1)

            def make_toggle_handler(edit: QLineEdit) -> Callable[[bool], None]:
                def handler(checked: bool) -> None:
                    edit.setEnabled(checked)
                    if not checked:
                        edit.clear()

                return handler

            active_checkbox.toggled.connect(make_toggle_handler(amount_edit))

            account_row_layout.addWidget(active_checkbox)
            account_row_layout.addLayout(amount_row)

            layout.addWidget(account_row)

            account_widgets[account_name] = {
                "checkbox": active_checkbox,
                "amount_edit": amount_edit,
                "current_account": account,
            }

        layout.addStretch(1)

        save_button = QPushButton("שמור חשבונות", card)
        save_button.setObjectName("SaveButton")

        def on_save_bank_accounts() -> None:
            try:
                rows: List[BankSettingsRowInput] = []
                for account_name, widgets in account_widgets.items():
                    checkbox = widgets["checkbox"]
                    amount_edit = widgets["amount_edit"]
                    current_account = widgets["current_account"]

                    rows.append(
                        BankSettingsRowInput(
                            name=account_name,
                            is_active=checkbox.isChecked(),
                            starter_amount_text=amount_edit.text(),
                            current_account=current_account,
                        )
                    )

                merged_accounts = self._accounts_service.apply_bank_settings_rows(rows)
                # IMPORTANT: Save through AccountsService so it also pushes account definitions
                # to Firebase (workspace) immediately.
                try:
                    self._accounts_service.save_all(merged_accounts)
                except Exception:
                    pass

                try:
                    self._accounts = self._provider.list_accounts()
                except Exception:
                    pass

                def update_sidebar() -> None:
                    if self._sidebar is not None and hasattr(
                        self._sidebar, "update_accounts"
                    ):
                        try:
                            try:
                                latest_accounts = self._provider.list_accounts()
                            except Exception:
                                latest_accounts = self._accounts
                            self._sidebar.update_accounts(latest_accounts)
                        except Exception:
                            pass

                try:
                    from ..qt import QTimer

                    QTimer.singleShot(50, update_sidebar)
                except Exception:
                    update_sidebar()

                saved_bank_by_name = {
                    acc.name: acc
                    for acc in merged_accounts
                    if isinstance(acc, BankAccount)
                }
                for account_name, widgets in account_widgets.items():
                    checkbox = widgets["checkbox"]
                    amount_edit = widgets["amount_edit"]
                    saved_account = saved_bank_by_name.get(account_name)
                    if saved_account:
                        checkbox.blockSignals(True)
                        checkbox.setChecked(saved_account.active)
                        checkbox.blockSignals(False)
                        if saved_account.active and saved_account.total_amount > 0:
                            amount_edit.setText(f"{saved_account.total_amount:.2f}")
                        amount_edit.setEnabled(saved_account.active)

                try:
                    QToolTip.showText(QCursor.pos(), "חשבונות הבנק נשמרו")
                except Exception:
                    pass

            except Exception as e:
                try:
                    QToolTip.showText(QCursor.pos(), f"שגיאה בשמירה: {str(e)}")
                except Exception:
                    pass

        save_button.clicked.connect(on_save_bank_accounts)

        try:
            layout.addWidget(
                save_button,
                0,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
        except Exception:
            layout.addWidget(save_button)

        return card

    def _build_notifications_card(self) -> QWidget:
        card = QWidget(self)
        card.setObjectName("Sidebar")
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                card.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("התראות", card)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)
        layout.addSpacing(8)

        try:
            self._notifications_service.ensure_defaults()
        except Exception:
            pass

        master_cb = QCheckBox("הפעל התראות", card)
        try:
            master_cb.setChecked(bool(self._notifications_service.is_enabled()))
        except Exception:
            master_cb.setChecked(True)
        layout.addWidget(master_cb)
        layout.addSpacing(6)

        rule_label_map: dict[RuleType, str] = {
            RuleType.UNEXPECTED_EXPENSE: "הוצאות חריגות / כפולות",
            RuleType.MISSING_MONTHLY_UPLOAD: "תזכורת העלאת קובץ הוצאות חודשי",
            RuleType.MISSING_SAVINGS_UPDATE: "תזכורת עדכון חסכונות",
            RuleType.EVENT_OVER_BUDGET: "חריגה מתקציב אירוע",
        }

        rules = []
        try:
            rules = self._notifications_service.list_rules()
        except Exception:
            rules = []

        rule_checkboxes: dict[str, QCheckBox] = {}
        for r in rules:
            label = rule_label_map.get(r.type, r.id)
            cb = QCheckBox(label, card)
            cb.setChecked(bool(r.enabled))
            rule_checkboxes[r.id] = cb
            layout.addWidget(cb)

            def make_rule_toggle(rule_id: str) -> Callable[[bool], None]:
                def _handler(checked: bool) -> None:
                    try:
                        self._notifications_service.set_rule_enabled(
                            rule_id, bool(checked)
                        )
                        self._notifications_service.refresh()
                        refresher = getattr(self, "_refresh_notifications_badge", None)
                        if callable(refresher):
                            refresher()
                        QToolTip.showText(QCursor.pos(), "הגדרות התראות נשמרו")
                    except Exception:
                        pass

                return _handler

            cb.toggled.connect(make_rule_toggle(r.id))

        def apply_enabled_state(enabled: bool) -> None:
            for cb in rule_checkboxes.values():
                cb.setEnabled(bool(enabled))

        def on_master_toggled(checked: bool) -> None:
            try:
                self._notifications_service.set_enabled(bool(checked))
                apply_enabled_state(bool(checked))
                self._notifications_service.refresh()
                refresher = getattr(self, "_refresh_notifications_badge", None)
                if callable(refresher):
                    refresher()
                QToolTip.showText(QCursor.pos(), "הגדרות התראות נשמרו")
            except Exception:
                pass

        master_cb.toggled.connect(on_master_toggled)
        apply_enabled_state(master_cb.isChecked())

        layout.addStretch(1)
        return card

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)
        content_card = QWidget(self)
        content_card.setObjectName("Sidebar")
        try:
            content_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            content_card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                content_card.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(12)

        title_label = QLabel("פרטי משתמש", content_card)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        name_label = QLabel("שם משתמש", content_card)
        name_edit = QLineEdit(content_card)
        name_edit.setText(self._user.full_name)

        lock_checkbox = QCheckBox("הפעל נעילת אפליקציה", content_card)
        lock_checkbox.setChecked(bool(getattr(self._user, "lock_enabled", False)))

        password_label = QLabel("סיסמה", content_card)
        password_edit = QLineEdit(content_card)
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

        save_button = QPushButton("שמור", content_card)
        save_button.setObjectName("SaveButton")

        eye_button = QToolButton(content_card)
        eye_button.setObjectName("PasswordEye")
        eye_button.setCheckable(True)
        eye_button.setToolTip("הצג / הסתר סיסמה")

        app = QApplication.instance()
        current_theme = "light"
        if app is not None:
            try:
                current_theme = str(app.property("theme") or "light")
            except Exception:
                current_theme = "light"
        is_dark = current_theme == "dark"

        eye_icon_path = None
        if is_dark:
            for ext in [".png", ".jpg"]:
                test_path = (
                    Path.cwd() / "data" / "assets" / "icons" / f"eye_icon_dark{ext}"
                )
                if test_path.exists():
                    eye_icon_path = test_path
                    break
        else:
            for ext in [".png", ".jpg"]:
                test_path = Path.cwd() / "data" / "assets" / "icons" / f"eye_icon{ext}"
                if test_path.exists():
                    eye_icon_path = test_path
                    break

        if eye_icon_path and eye_icon_path.exists():
            pixmap = QPixmap(str(eye_icon_path))
            if not pixmap.isNull():
                try:
                    from ..qt import QSize

                    scaled_pixmap = pixmap.scaled(
                        QSize(24, 24),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    eye_button.setIconSize(QSize(24, 24))
                except Exception:
                    scaled_pixmap = pixmap.scaled(
                        24,
                        24,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                icon = QIcon(scaled_pixmap)
                eye_button.setIcon(icon)
                eye_button.setText("")
        else:
            eye_button.setText("👁")

        def update_eye_icon() -> None:
            app_ = QApplication.instance()
            current_theme_ = "light"
            if app_ is not None:
                try:
                    current_theme_ = str(app_.property("theme") or "light")
                except Exception:
                    current_theme_ = "light"
            is_dark_ = current_theme_ == "dark"

            eye_icon_path_ = None
            if is_dark_:
                for ext in [".png", ".jpg"]:
                    test_path = (
                        Path.cwd() / "data" / "assets" / "icons" / f"eye_icon_dark{ext}"
                    )
                    if test_path.exists():
                        eye_icon_path_ = test_path
                        break
            else:
                for ext in [".png", ".jpg"]:
                    test_path = (
                        Path.cwd() / "data" / "assets" / "icons" / f"eye_icon{ext}"
                    )
                    if test_path.exists():
                        eye_icon_path_ = test_path
                        break

            if eye_icon_path_ and eye_icon_path_.exists():
                pixmap_ = QPixmap(str(eye_icon_path_))
                if not pixmap_.isNull():
                    try:
                        from ..qt import QSize

                        scaled_pixmap_ = pixmap_.scaled(
                            QSize(24, 24),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        eye_button.setIconSize(QSize(24, 24))
                    except Exception:
                        scaled_pixmap_ = pixmap_.scaled(
                            24,
                            24,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    icon_ = QIcon(scaled_pixmap_)
                    eye_button.setIcon(icon_)
                    eye_button.setText("")

        self._update_eye_icon = update_eye_icon

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
            except Exception:
                pass
            try:
                if self._sidebar is not None:
                    self._sidebar.refresh_profile()
            except Exception:
                pass
            try:
                QToolTip.showText(QCursor.pos(), "ההגדרות נשמרו")
            except Exception:
                pass

        save_button.clicked.connect(on_save_clicked)

        content_layout.addWidget(title_label)
        content_layout.addSpacing(4)
        content_layout.addWidget(lock_checkbox)
        content_layout.addSpacing(8)

        name_row = QHBoxLayout()
        name_row.setSpacing(8)
        dash1 = QLabel("-", content_card)
        name_row.addWidget(name_label)
        name_row.addWidget(dash1)
        name_row.addWidget(name_edit, 1)

        password_row_widget = QWidget(content_card)
        password_row = QHBoxLayout(password_row_widget)
        password_row.setSpacing(8)
        dash2 = QLabel("-", content_card)
        password_row.addWidget(password_label)
        password_row.addWidget(dash2)
        password_row.addWidget(password_edit, 1)
        password_row.addWidget(eye_button)

        content_layout.addLayout(name_row)
        content_layout.addWidget(password_row_widget)

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
        content_layout.addStretch(1)
        try:
            content_layout.addWidget(
                save_button,
                0,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            )
        except Exception:
            content_layout.addWidget(save_button)

        def _make_extra_card(title: str) -> QWidget:
            card = QWidget(self)
            card.setObjectName("Sidebar")
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            layout_card = QVBoxLayout(card)
            layout_card.setContentsMargins(24, 24, 24, 24)
            layout_card.setSpacing(12)
            lbl = QLabel(title, card)
            try:
                lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            except Exception:
                pass
            layout_card.addWidget(lbl)
            layout_card.addStretch(1)
            return card

        bank_accounts_card = self._build_bank_accounts_card()
        extra_card_bottom_left = self._build_notifications_card()
        updates_card = QWidget(self)
        updates_card.setObjectName("Sidebar")
        try:
            updates_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        updates_layout = QVBoxLayout(updates_card)
        updates_layout.setContentsMargins(24, 24, 24, 24)
        updates_layout.setSpacing(12)

        updates_title = QLabel("עדכונים", updates_card)
        try:
            updates_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        updates_layout.addWidget(updates_title)

        ver_lbl = QLabel(f"גרסה נוכחית: {__version__}", updates_card)
        updates_layout.addWidget(ver_lbl)

        repo = str(os.environ.get("FINENCE_UPDATE_REPO", "") or "").strip()
        repo_lbl = QLabel(
            f"מקור עדכון: {repo if repo else 'לא הוגדר (FINENCE_UPDATE_REPO)'}",
            updates_card,
        )
        repo_lbl.setObjectName("Subtitle")
        updates_layout.addWidget(repo_lbl)

        status_lbl = QLabel("", updates_card)
        status_lbl.setObjectName("Subtitle")
        updates_layout.addWidget(status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        check_btn = QPushButton("בדוק עדכונים", updates_card)
        check_btn.setObjectName("SaveButton")
        open_btn = QPushButton("פתח דף הורדה", updates_card)
        btn_row.addWidget(check_btn)
        btn_row.addWidget(open_btn)
        btn_row.addStretch(1)
        updates_layout.addLayout(btn_row)

        def open_download_page() -> None:
            if repo:
                webbrowser.open(f"https://github.com/{repo}/releases")
            else:
                webbrowser.open("https://github.com/")

        def check_updates() -> None:
            status_lbl.setText("בודק עדכונים...")
            QApplication.processEvents()
            if not repo:
                status_lbl.setText("כדי לאפשר בדיקת עדכונים, הגדר FINENCE_UPDATE_REPO.")
                return
            svc = UpdateService(repo=repo)
            latest = svc.latest_release()
            if latest is None:
                status_lbl.setText("לא ניתן לבדוק עדכונים כרגע.")
                return
            if svc.is_newer(current=__version__, latest=latest.version):
                status_lbl.setText(f"גרסה חדשה זמינה: {latest.version}")
                webbrowser.open(latest.html_url)
            else:
                status_lbl.setText("אתה על הגרסה העדכנית.")

        open_btn.clicked.connect(open_download_page)
        check_btn.clicked.connect(check_updates)

        updates_layout.addStretch(1)
        extra_card_bottom_right = updates_card

        firebase_card = QWidget(self)
        firebase_card.setObjectName("Sidebar")
        try:
            firebase_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            firebase_card.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                firebase_card.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        fb_l = QVBoxLayout(firebase_card)
        fb_l.setContentsMargins(24, 24, 24, 24)
        fb_l.setSpacing(10)

        fb_title = QLabel("שיתוף וסנכרון", firebase_card)
        try:
            fb_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        fb_l.addWidget(fb_title)

        store = FirebaseSessionStore()
        session = store.load()

        email_edit = QLineEdit(firebase_card)
        email_edit.setPlaceholderText("אימייל (Firebase)")
        email_edit.setText(session.email or "")

        password_edit = QLineEdit(firebase_card)
        password_edit.setPlaceholderText("סיסמה (Firebase)")
        try:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            try:
                password_edit.setEchoMode(QLineEdit.Password)
            except Exception:
                pass

        # Project config is advanced; show as read-only + "change" dialog.
        project_row = QHBoxLayout()
        project_row.setSpacing(10)
        project_lbl = QLabel("", firebase_card)
        project_lbl.setObjectName("Subtitle")
        change_project_btn = QPushButton("שנה פרויקט", firebase_card)
        project_row.addWidget(project_lbl, 1)
        project_row.addWidget(change_project_btn, 0)
        fb_l.addLayout(project_row)

        fb_l.addWidget(email_edit)
        fb_l.addWidget(password_edit)

        workspace_edit = QLineEdit(firebase_card)
        workspace_edit.setPlaceholderText("קוד שיתוף (Workspace)")
        try:
            workspace_edit.setText(str(getattr(session, "workspace_id", "") or ""))
        except Exception:
            workspace_edit.setText("")
        fb_l.addWidget(workspace_edit)

        fb_status = QLabel("", firebase_card)
        fb_status.setObjectName("Subtitle")
        fb_l.addWidget(fb_status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        login_btn = QPushButton("התחבר", firebase_card)
        login_btn.setObjectName("SaveButton")
        create_ws_btn = QPushButton("צור קוד", firebase_card)
        join_ws_btn = QPushButton("הצטרף", firebase_card)
        clear_ws_btn = QPushButton("נתק שיתוף", firebase_card)
        logout_btn = QPushButton("התנתק", firebase_card)
        btn_row.addWidget(login_btn)
        btn_row.addWidget(create_ws_btn)
        btn_row.addWidget(join_ws_btn)
        btn_row.addWidget(clear_ws_btn)
        btn_row.addWidget(logout_btn)
        btn_row.addStretch(1)
        fb_l.addLayout(btn_row)

        def refresh_status() -> None:
            s = store.load()
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
            s = store.load()
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
                # Changing project requires re-login.
                s.api_key = api_key
                s.project_id = project_id
                s.uid = ""
                s.id_token = ""
                s.refresh_token = ""
                s.expires_at = 0.0
                store.save(s)
                dlg.accept()
                refresh_status()

            save_btn.clicked.connect(_save_project)
            dlg.exec()

        def do_login() -> None:
            current = store.load()
            api_key = str(getattr(current, "api_key", "") or "").strip()
            project_id = str(getattr(current, "project_id", "") or "").strip()
            email = email_edit.text().strip()
            pw = password_edit.text()
            if not api_key or not project_id:
                fb_status.setText("חובה להגדיר פרויקט (API key + project id) לפני התחברות")
                return
            if not email or not pw:
                fb_status.setText("חובה למלא אימייל וסיסמה")
                return
            fb_status.setText("מתחבר...")
            QApplication.processEvents()
            try:
                auth = FirebaseAuthClient(api_key=api_key)
                res = auth.sign_in_with_password(email=email, password=pw)
                s = FirebaseSession(
                    api_key=api_key,
                    project_id=project_id,
                    email=email,
                    uid=res.uid,
                    workspace_id=workspace_edit.text().strip(),
                    refresh_token=res.refresh_token,
                    id_token=res.id_token,
                    expires_at=__import__("time").time() + float(res.expires_in),
                )
                store.save(s)
                try:
                    key = str(getattr(s, "workspace_id", "") or "").strip() or res.uid
                    FirebaseMovementsSyncService().ensure_user_local_file(key)
                except Exception:
                    pass
            except Exception as e:
                fb_status.setText(f"שגיאת התחברות: {str(e)}")
                return
            refresh_status()

        def _random_workspace_code() -> str:
            alphabet = string.ascii_uppercase + string.digits
            raw = "".join(secrets.choice(alphabet) for _ in range(12))
            return f"{raw[:4]}-{raw[4:8]}-{raw[8:12]}"

        def _ensure_workspace_membership(
            *, s: FirebaseSession, workspace_id: str, role: str
        ) -> None:
            fs = FirestoreClient(project_id=s.project_id)
            fs.upsert_document(
                document_path=f"workspaces/{workspace_id}",
                id_token=s.id_token,
                fields={
                    "created_by": s.uid,
                    "name": "Workspace",
                    "version": 1,
                },
            )
            fs.upsert_document(
                document_path=f"workspaces/{workspace_id}/members/{s.uid}",
                id_token=s.id_token,
                fields={"role": role},
            )
            fs.upsert_document(
                document_path=f"users/{s.uid}",
                id_token=s.id_token,
                fields={"active_workspace_id": workspace_id},
            )

        def do_create_workspace() -> None:
            s = store.load()
            if not s.is_logged_in:
                fb_status.setText("יש להתחבר לפני יצירת שיתוף")
                return
            code = _random_workspace_code()
            fb_status.setText("יוצר שיתוף...")
            QApplication.processEvents()
            try:
                _ensure_workspace_membership(s=s, workspace_id=code, role="owner")
                s.workspace_id = code
                store.save(s)
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
            s = store.load()
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
                # Validate workspace exists (best-effort)
                fs = FirestoreClient(project_id=s.project_id)
                fs.get_document(document_path=f"workspaces/{code}", id_token=s.id_token)
                _ensure_workspace_membership(s=s, workspace_id=code, role="editor")
                s.workspace_id = code
                store.save(s)
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
            s = store.load()
            if not s.is_logged_in:
                workspace_edit.setText("")
                return
            s.workspace_id = ""
            store.save(s)
            workspace_edit.setText("")
            fb_status.setText("שיתוף נותק (מקומי בלבד)")
            refresh_status()

        def do_logout() -> None:
            store.clear()
            refresh_status()

        login_btn.clicked.connect(do_login)
        create_ws_btn.clicked.connect(do_create_workspace)
        join_ws_btn.clicked.connect(do_join_workspace)
        clear_ws_btn.clicked.connect(do_clear_workspace)
        logout_btn.clicked.connect(do_logout)
        change_project_btn.clicked.connect(edit_project_settings)

        refresh_status()

        # Internal settings navigation: small menu on the left, content on the right.
        container = QWidget(self)
        try:
            # Keep menu on the left even in RTL app.
            container.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            try:
                container.setLayoutDirection(Qt.LeftToRight)  # type: ignore[attr-defined]
            except Exception:
                pass

        container_l = QHBoxLayout(container)
        container_l.setContentsMargins(0, 0, 0, 0)
        container_l.setSpacing(16)

        menu = QListWidget(container)
        menu.setObjectName("SettingsMenu")
        try:
            menu.setFixedWidth(210)
        except Exception:
            pass
        try:
            menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                menu.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass

        menu.addItem("כללי")
        menu.addItem("חשבונות")
        menu.addItem("התראות")
        menu.addItem("שיתוף וסנכרון")
        menu.addItem("עדכונים")

        stack = QStackedWidget(container)

        def _wrap_page(child: QWidget) -> QWidget:
            page = QWidget(stack)
            try:
                page.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                try:
                    page.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
                except Exception:
                    pass
            lay = QVBoxLayout(page)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(16)
            lay.addWidget(child, 0)
            lay.addStretch(1)
            return page

        stack.addWidget(_wrap_page(content_card))
        stack.addWidget(_wrap_page(bank_accounts_card))
        stack.addWidget(_wrap_page(extra_card_bottom_left))
        stack.addWidget(_wrap_page(firebase_card))
        stack.addWidget(_wrap_page(extra_card_bottom_right))

        def _save_selected(idx: int) -> None:
            try:
                self._app_context["settings_section"] = str(int(idx))
            except Exception:
                pass

        menu.currentRowChanged.connect(stack.setCurrentIndex)
        menu.currentRowChanged.connect(_save_selected)

        initial = 0
        try:
            initial = int(str(self._app_context.get("settings_section", "0") or "0"))
        except Exception:
            initial = 0
        if initial < 0 or initial >= stack.count():
            initial = 0
        try:
            menu.setCurrentRow(initial)
        except Exception:
            pass

        container_l.addWidget(menu, 0)
        container_l.addWidget(stack, 1)

        main_col.addWidget(container, 1)
