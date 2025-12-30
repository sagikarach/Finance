from __future__ import annotations

from typing import Callable, Optional, Dict, List

from ..qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QDialog,
    QPushButton,
    Qt,
    QSizePolicy,
    QApplication,
    QTimer,
    QToolTip,
    QCursor,
    Signal,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..data.user_profile_store import UserProfileStore
from ..models.user import UserProfile
from ..utils.defaults import load_defaults
from ..widgets.sidebar import Sidebar
from ..widgets.bank_movement_actions import BankMovementActions
from ..widgets.action_history_table import ActionHistoryTable
from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..models.accounts import BankAccount, BudgetAccount, MoneyAccount
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..models.accounts_service import AccountsService
from ..models.bank_movement_service import BankMovementService
from ..models.movement_classifier import SimilarityBasedClassifier
from ..ui.bank_movement_dialog import BankMovementDialog
from ..ui.notifications_dialog import NotificationsDialog
from ..styles.theme import load_default_stylesheet, load_dark_stylesheet
from ..models.notifications_service import NotificationsService


class BasePage(QWidget):
    try:
        _sync_finished = Signal(int, str)
    except Exception:
        _sync_finished = None

    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        page_title: str = "",
        current_route: str = "",
    ) -> None:
        super().__init__(parent)
        self._app_context = app_context or {}
        self._provider: AccountsProvider = provider or JsonFileAccountsProvider()
        self._accounts: List = self._provider.list_accounts()
        self._navigate = navigate
        self._user_store = UserProfileStore()
        defaults = load_defaults()
        default_name = self._app_context.get("userName") or defaults.get(
            "default_full_name", "אורח"
        )
        self._user: UserProfile = self._user_store.load(
            default_full_name=default_name,
            accounts=self._accounts,
        )
        self._page_title = page_title
        self._current_route = current_route
        self._sidebar: Optional[Sidebar] = None
        self._theme_btn: Optional[QToolButton] = None
        self._content_col: Optional[QVBoxLayout] = None
        self._bank_movement_provider = JsonFileBankMovementProvider()
        self._history_provider = JsonFileActionHistoryProvider()
        self._accounts_service: AccountsService = AccountsService(
            self._provider, history_provider=self._history_provider
        )
        classifier = None
        try:
            classifier = SimilarityBasedClassifier()
            classifier.initialize()
        except Exception:
            classifier = None
        self._bank_movement_service: BankMovementService = BankMovementService(
            self._bank_movement_provider,
            self._history_provider,
            classifier=classifier,
        )
        self._notifications_service = NotificationsService(
            accounts_provider=self._provider,
            movement_provider=self._bank_movement_provider,
            history_provider=self._history_provider,
        )
        self._bell_btn: Optional[QToolButton] = None
        self._bell_badge: Optional[QLabel] = None
        self._sync_btn: Optional[QToolButton] = None
        self._sync_in_progress: bool = False

        self._build_ui()
        try:
            if self._sync_finished is not None:
                self._sync_finished.connect(self._on_sync_finished)
        except Exception:
            pass

    def _build_ui(self) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        main_area = QWidget(self)
        main_col = QVBoxLayout(main_area)
        main_col.setContentsMargins(40, 40, 16, 40)
        main_col.setSpacing(16)

        header_container = self._build_header()
        try:
            header_container.setFixedHeight(56)
            header_container.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        main_col.addWidget(header_container, 0)

        content_area = QWidget(self)
        content_col = QVBoxLayout(content_area)
        content_col.setContentsMargins(0, 0, 0, 0)
        content_col.setSpacing(16)

        self._content_col = content_col

        self._build_content(content_col)
        main_col.addWidget(content_area, 1)

        selected_name = None
        try:
            value = self._app_context.get("selected_savings_account")
            if isinstance(value, str) and value:
                selected_name = value
        except Exception:
            selected_name = None

        self._sidebar = Sidebar(
            self._user,
            self._user_store,
            self,
            app_context=self._app_context,
            navigate=self._navigate,
            current_route=self._current_route,
            accounts=self._accounts,
            selected_savings_account=selected_name,
        )

        try:
            self._sidebar.setFixedWidth(240)
            self._sidebar.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        sidebar_container = QWidget(self)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 40, 16, 40)
        sidebar_layout.setSpacing(12)
        sidebar_layout.addWidget(self._sidebar, 1)

        self._bank_actions = BankMovementActions(
            parent=sidebar_container,
            on_add_income=self._on_add_income,
            on_add_outcome=self._on_add_outcome,
        )
        sidebar_layout.addWidget(self._bank_actions, 0)

        layout.addWidget(main_area, 1)
        layout.addWidget(sidebar_container, 0)

        self.setLayout(layout)

    def _build_header(self) -> QWidget:
        header_container = QWidget(self)
        header_container.setObjectName("Sidebar")
        try:
            header_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(12)

        left_buttons = self._build_header_left_buttons()
        for btn in left_buttons:
            header_layout.addWidget(btn)

        bell_wrap = QWidget(header_container)
        try:
            bell_wrap.setFixedSize(36, 36)
        except Exception:
            pass

        self._bell_btn = QToolButton(bell_wrap)
        self._bell_btn.setObjectName("IconButton")
        self._bell_btn.setText("🔔")
        self._bell_btn.setToolTip("התראות")
        self._bell_btn.clicked.connect(self._open_notifications)
        try:
            self._bell_btn.setGeometry(0, 0, 36, 36)
        except Exception:
            pass

        self._bell_badge = QLabel(bell_wrap)
        self._bell_badge.setObjectName("NotificationsBadge")
        try:
            self._bell_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._bell_badge.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
        except Exception:
            pass
        try:
            self._bell_badge.setVisible(False)
        except Exception:
            pass
        try:
            self._bell_badge.adjustSize()
            self._bell_badge.move(22, -2)
        except Exception:
            pass

        header_layout.addWidget(bell_wrap)

        sync_wrap = QWidget(header_container)
        try:
            sync_wrap.setFixedSize(36, 36)
        except Exception:
            pass
        self._sync_btn = QToolButton(sync_wrap)
        self._sync_btn.setObjectName("IconButton")
        self._sync_btn.setText("🔄")
        self._sync_btn.setToolTip("סנכרן עכשיו")
        self._sync_btn.clicked.connect(self._on_sync_clicked)
        try:
            self._sync_btn.setGeometry(0, 0, 36, 36)
        except Exception:
            pass
        header_layout.addWidget(sync_wrap)

        self._theme_btn = self._build_theme_toggle_button()
        header_layout.addWidget(self._theme_btn)

        header_layout.addStretch(1)

        header_title = QLabel(self._page_title, self)
        header_title.setObjectName("HeaderTitle")
        header_layout.addWidget(header_title)

        return header_container

    def on_route_activated(self) -> None:
        self._refresh_notifications_badge()
        self._refresh_sync_button_state()

    def _refresh_sync_button_state(self) -> None:
        btn = self._sync_btn
        if btn is None:
            return
        if self._sync_in_progress:
            try:
                btn.setEnabled(False)
                btn.setToolTip("מסנכרן...")
            except Exception:
                pass
            return
        try:
            from ..models.firebase_session import FirebaseSessionStore

            s = FirebaseSessionStore().load()
            ok = bool(
                s.is_logged_in and str(getattr(s, "workspace_id", "") or "").strip()
            )
            btn.setEnabled(bool(ok))
            btn.setToolTip(
                "סנכרן עכשיו" if ok else "התחבר ל-Firebase ובחר Workspace בהגדרות"
            )
        except Exception:
            try:
                btn.setEnabled(False)
            except Exception:
                pass

    def _on_sync_clicked(self) -> None:
        if self._sync_in_progress:
            return
        try:
            from ..models.firebase_session import FirebaseSessionStore

            s = FirebaseSessionStore().load()
            wid = str(getattr(s, "workspace_id", "") or "").strip()
            if not (s.is_logged_in and wid):
                try:
                    QToolTip.showText(
                        QCursor.pos(),
                        "כדי לסנכרן צריך להתחבר ל-Firebase ולבחור Workspace בהגדרות",
                    )
                except Exception:
                    pass
                return
        except Exception:
            return

        self._sync_in_progress = True
        try:
            if self._sync_btn is not None:
                self._sync_btn.setEnabled(False)
                self._sync_btn.setText("⏳")
                self._sync_btn.setToolTip("מסנכרן...")
        except Exception:
            pass

        def _run() -> None:
            pulled = 0
            err: Optional[str] = None
            try:
                from ..models.firebase_movements_sync import (
                    FirebaseMovementsSyncService,
                )

                pulled, _ = FirebaseMovementsSyncService().sync_now()
            except Exception as e:
                err = str(e)
            try:
                if self._sync_finished is not None:
                    self._sync_finished.emit(int(pulled), str(err or ""))
                    return
            except Exception:
                pass
            try:
                self._on_sync_finished(int(pulled), str(err or ""))
            except Exception:
                pass

        try:
            import threading

            threading.Thread(target=_run, daemon=True).start()
        except Exception:
            _run()

    def _on_sync_finished(self, pulled: int, err: str) -> None:
        self._sync_in_progress = False
        try:
            if self._sync_btn is not None:
                self._sync_btn.setText("🔄")
        except Exception:
            pass
        self._refresh_sync_button_state()

        try:
            self._load_and_refresh_accounts()
        except Exception:
            pass

        try:
            from ..models.workspace_ml_trainer import WorkspaceMLTrainer

            trainer = WorkspaceMLTrainer()
            cls = getattr(self._bank_movement_service, "classifier", None)
            if cls is not None:
                try:
                    movements = self._bank_movement_service.list_movements()
                except Exception:
                    movements = []
                trainer.rebuild_training_file(movements=movements, classifier=cls)
                try:
                    cls.reload()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            history_table = self._find_history_table()
            if history_table is not None:
                try:
                    history = self._history_provider.list_history()
                except Exception:
                    history = []
                try:
                    history_table.set_history(history)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self._refresh_notifications_badge()
        except Exception:
            pass

        if err:
            try:
                QToolTip.showText(QCursor.pos(), f"שגיאת סנכרון: {err}")
            except Exception:
                pass
        else:
            try:
                QToolTip.showText(QCursor.pos(), f"סונכרן בהצלחה ({int(pulled)})")
            except Exception:
                pass
        try:
            self.on_route_activated()
        except Exception:
            pass

    def _open_notifications(self) -> None:
        try:
            if not bool(self._notifications_service.is_enabled()):
                dlg = QDialog(self)
                dlg.setWindowTitle("התראות")
                try:
                    dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                except Exception:
                    try:
                        dlg.setLayoutDirection(Qt.RightToLeft)
                    except Exception:
                        pass
                layout = QVBoxLayout(dlg)
                layout.setContentsMargins(24, 20, 24, 20)
                layout.setSpacing(12)

                msg = QLabel("ההתראות כבויות. ניתן להפעיל אותן בעמוד ההגדרות.", dlg)
                try:
                    msg.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                except Exception:
                    pass
                layout.addWidget(msg)

                close_btn = QPushButton("סגור", dlg)
                close_btn.clicked.connect(dlg.accept)
                try:
                    layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignHCenter)
                except Exception:
                    layout.addWidget(close_btn)

                dlg.exec()
                return
        except Exception:
            pass
        try:
            dlg = NotificationsDialog(service=self._notifications_service, parent=None)
            dlg.exec()
        except Exception:
            return
        self._refresh_notifications_badge()

    def _refresh_notifications_badge(self) -> None:
        if self._bell_btn is None:
            return
        try:
            self._notifications_service.refresh()
            count = int(self._notifications_service.unread_count())
            tip = "התראות" if count <= 0 else f"התראות ({count})"
            self._bell_btn.setToolTip(tip)
            if self._bell_badge is not None:
                if count <= 0:
                    self._bell_badge.setVisible(False)
                else:
                    text = str(count) if count < 100 else "99+"
                    self._bell_badge.setText(text)
                    try:
                        if count < 10:
                            w = 16
                        else:
                            self._bell_badge.adjustSize()
                            w = max(16, int(self._bell_badge.sizeHint().width()) + 10)
                        self._bell_badge.setFixedSize(w, 16)
                        self._bell_badge.move(36 - w + 2, -2)
                    except Exception:
                        pass
                    self._bell_badge.setVisible(True)
        except Exception:
            pass

    def _build_header_left_buttons(self) -> List[QToolButton]:
        return []

    def _clear_content_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout_recursive(sub_layout)
                    sub_layout.deleteLater()

        try:
            QApplication.processEvents()
        except Exception:
            pass

    def _clear_layout_recursive(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout_recursive(sub_layout)
                    sub_layout.deleteLater()

    def _on_add_income(self) -> None:
        self._open_bank_movement_dialog(is_income=True)

    def _on_add_outcome(self) -> None:
        self._open_bank_movement_dialog(is_income=False)

    def _open_bank_movement_dialog(self, is_income: bool) -> None:
        try:
            bank_accounts: List[MoneyAccount] = [
                acc
                for acc in self._accounts
                if isinstance(acc, (BankAccount, BudgetAccount))
                and bool(getattr(acc, "active", False))
            ]
        except Exception:
            bank_accounts = []

        categories: list[str] = []
        provider = self._bank_movement_provider
        try:
            if hasattr(provider, "list_categories_for_type"):
                categories = provider.list_categories_for_type(is_income)
            else:
                categories = provider.list_categories()
        except Exception:
            categories = []

        on_category_added = None
        try:
            if hasattr(provider, "add_category_for_type"):

                def _on_cat_added(
                    name: str, *, _prov=provider, _is_income=is_income
                ) -> None:
                    try:
                        _prov.add_category_for_type(name, _is_income)
                    except Exception:
                        pass
                    try:
                        from ..models.firebase_movements_sync import (
                            FirebaseMovementsSyncService,
                        )

                        FirebaseMovementsSyncService().sync_categories_only()
                    except Exception:
                        pass

                on_category_added = _on_cat_added
            elif hasattr(provider, "add_category"):
                on_category_added = getattr(provider, "add_category")
        except Exception:
            on_category_added = None

        dialog = BankMovementDialog(
            bank_accounts,
            categories,
            is_income,
            parent=None,
            on_category_added=on_category_added,
        )
        result = dialog.exec()
        if not result:
            return
        movement = dialog.get_movement()
        if movement is None:
            return

        service = self._bank_movement_service
        if service is not None:
            try:
                self._accounts = service.apply_movement(
                    self._accounts,
                    movement,
                    is_income_hint=is_income,
                    record_history=True,
                )
            except Exception as e:
                try:
                    QToolTip.showText(QCursor.pos(), str(e))
                except Exception:
                    pass
                return

        try:
            history_table = self._find_history_table()
            if history_table is not None and hasattr(
                self._history_provider, "list_history"
            ):
                try:
                    history = self._history_provider.list_history()
                except Exception:
                    history = []
                try:
                    history_table.set_history(history)
                except Exception:
                    pass
        except Exception:
            pass

        self._save_and_refresh_accounts()

    def _load_and_refresh_accounts(self) -> None:
        if self._accounts_service is not None:
            try:
                self._accounts = self._accounts_service.load_accounts()
            except Exception:
                pass

        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)
            except Exception:
                pass

    def _save_and_refresh_accounts(self) -> None:
        svc = self._accounts_service
        if svc is None:
            try:
                svc = AccountsService(
                    self._provider, history_provider=self._history_provider
                )
                self._accounts_service = svc
            except Exception:
                svc = None

        if svc is not None:
            try:
                svc.save_all(self._accounts)
            except Exception:
                pass

        self._load_and_refresh_accounts()

        if isinstance(self._content_col, QVBoxLayout):
            layout = self._content_col
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            self._build_content(layout)

    def _build_theme_toggle_button(self) -> QToolButton:
        theme_btn = QToolButton(self)
        theme_btn.setObjectName("IconButton")
        theme_btn.setCheckable(True)

        app = QApplication.instance()
        current_theme = "light"
        if app is not None:
            try:
                current_theme = str(app.property("theme") or "light")
            except Exception:
                current_theme = "light"
        is_dark = current_theme == "dark"
        theme_btn.setChecked(is_dark)
        theme_btn.setText("🌙" if is_dark else "☀")
        theme_btn.setToolTip("מצב כהה / מצב בהיר")

        def on_theme_toggled(checked: bool) -> None:
            app_ = QApplication.instance()
            if app_ is None:
                return
            try:
                if checked:
                    setter = getattr(app_, "setProperty", None)
                    if callable(setter):
                        setter("theme", "dark")
                    ss = getattr(app_, "setStyleSheet", None)
                    if callable(ss):
                        ss(load_dark_stylesheet())
                    theme_btn.setText("🌙")
                else:
                    setter = getattr(app_, "setProperty", None)
                    if callable(setter):
                        setter("theme", "light")
                    ss = getattr(app_, "setStyleSheet", None)
                    if callable(ss):
                        ss(load_default_stylesheet())
                    theme_btn.setText("☀")
                self._on_theme_changed(checked)
            except Exception:
                pass

        theme_btn.toggled.connect(on_theme_toggled)
        return theme_btn

    def _on_theme_changed(self, is_dark: bool) -> None:
        if self._theme_btn is not None:
            self._theme_btn.setChecked(is_dark)
            self._theme_btn.setText("🌙" if is_dark else "☀")

        if self._sidebar is not None:
            if hasattr(self._sidebar, "_update_button_width"):
                try:
                    QTimer.singleShot(100, self._sidebar._update_button_width)
                except Exception:
                    pass

            if hasattr(self._sidebar, "_savings_section"):
                try:
                    self._sidebar._savings_section.refresh_theme()
                except Exception:
                    pass
            if hasattr(self._sidebar, "_bank_section"):
                try:
                    self._sidebar._bank_section.refresh_theme()
                except Exception:
                    pass

        try:
            history_table = self._find_history_table()
            if history_table is not None and hasattr(history_table, "_update_table"):
                history_table._update_table()
        except Exception:
            pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._theme_btn is not None:
            app = QApplication.instance()
            current_theme = "light"
            if app is not None:
                try:
                    current_theme = str(app.property("theme") or "light")
                except Exception:
                    current_theme = "light"
            is_dark = current_theme == "dark"
            self._theme_btn.blockSignals(True)
            self._theme_btn.setChecked(is_dark)
            self._theme_btn.setText("🌙" if is_dark else "☀")
            self._theme_btn.blockSignals(False)

    def _build_content(self, main_col: QVBoxLayout) -> None:
        raise NotImplementedError("Subclasses must implement _build_content()")

    def _find_history_table(self) -> Optional[ActionHistoryTable]:
        widget = self.findChild(ActionHistoryTable)
        if widget is not None:
            return widget
        top_level = self.window()
        if top_level is not None:
            for child in top_level.findChildren(ActionHistoryTable):
                if child is not None:
                    return child
        return None

    def set_selected_savings_account(self, account_name: str) -> None:
        try:
            self._app_context["selected_savings_account"] = account_name
        except Exception:
            pass

    def set_selected_bank_account(self, account_name: str) -> None:
        try:
            self._app_context["selected_bank_account"] = account_name
        except Exception:
            pass
