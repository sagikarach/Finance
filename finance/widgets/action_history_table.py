from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any, Dict, List, Optional, Callable

from ..qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
    Qt,
    QSizePolicy,
    QApplication,
    QPalette,
    QSize,
)
from ..models.action_history import ActionHistory
from ..ui.action_history_details_dialog import ActionHistoryDetailsDialog
from ..models.bank_movement_service import BankMovementService
from ..models.action_history import (
    TransferAction,
    UploadOutcomeFileAction,
    DeleteMovementAction,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    AddInstallmentPlanAction,
    EditInstallmentPlanAction,
    DeleteInstallmentPlanAction,
    AddOneTimeEventAction,
    EditOneTimeEventAction,
    DeleteOneTimeEventAction,
    AssignMovementToOneTimeEventAction,
    UnassignMovementFromOneTimeEventAction,
    AddSavingsAccountAction,
    EditSavingsAccountAction,
    DeleteSavingsAccountAction,
    AddSavingAction,
    EditSavingAction,
    DeleteSavingAction,
    ActivateBankAccountAction,
    DeactivateBankAccountAction,
    SetStarterAmountAction,
)


def _fmt_money(amount: float) -> str:
    try:
        return f"{amount:,.2f}"
    except Exception:
        try:
            return str(amount)
        except Exception:
            return ""


_ACTION_TITLE_MAP: dict[str, str] = {
    "transfer": "העברת כסף",
    "add_savings_account": "הוספת חסכון",
    "edit_savings_account": "עריכת חסכון",
    "delete_savings_account": "מחיקת חסכון",
    "add_saving": "הוספת סוג חסכון",
    "edit_saving": "עריכת סוג חסכון",
    "delete_saving": "מחיקת סוג חסכון",
    "activate_bank_account": "הפעלת חשבון",
    "deactivate_bank_account": "ביטול חשבון",
    "set_starter_amount": "הגדרת סכום התחלתי",
    "add_income_movement": "הוספת הכנסה",
    "add_outcome_movement": "הוספת הוצאה",
    "delete_movement": "מחיקת תנועה",
    "upload_outcome_file": "ייבוא קובץ הוצאות",
    "add_one_time_event": "יצירת אירוע חד־פעמי",
    "edit_one_time_event": "עריכת אירוע חד־פעמי",
    "delete_one_time_event": "מחיקת אירוע חד־פעמי",
    "assign_movement_to_one_time_event": "שיוך תנועה לאירוע",
    "unassign_movement_from_one_time_event": "הסרת שיוך תנועה מאירוע",
    "add_installment_plan": "יצירת תשלומים",
    "edit_installment_plan": "עריכת תשלומים",
    "delete_installment_plan": "מחיקת תשלומים",
}


def _action_title(action_name: str) -> str:
    key = str(action_name or "").strip()
    return _ACTION_TITLE_MAP.get(key, key or "פעולה")


def _action_body(
    entry: ActionHistory, *, movements_by_id: Optional[Dict[str, Any]] = None
) -> str:
    a = entry.action

    def _movement_details(mid: str) -> Optional[str]:
        mid_s = str(mid or "").strip()
        if not mid_s or movements_by_id is None:
            return None
        m = movements_by_id.get(mid_s)
        if m is None:
            return None
        try:
            acc = str(getattr(m, "account_name", "") or "").strip()
            date = str(getattr(m, "date", "") or "").strip()
            cat = str(getattr(m, "category", "") or "").strip()
            desc = str(getattr(m, "description", "") or "").strip()
            amt = _fmt_money(float(getattr(m, "amount", 0.0) or 0.0))
            parts = [p for p in (acc, date, (amt if amt else ""), cat) if p]
            if desc:
                parts.append(desc)
            return " • ".join(parts) if parts else None
        except Exception:
            return None

    try:
        if isinstance(a, TransferAction):
            amount = _fmt_money(float(getattr(a, "amount", 0.0) or 0.0))
            src = str(getattr(a, "source_name", "") or "").strip()
            tgt = str(getattr(a, "target_name", "") or "").strip()
            if src and tgt:
                return f"{src} → {tgt} • {amount}"
            if src:
                return f"{src} • {amount}"
            if tgt:
                return f"{tgt} • {amount}"
            return amount

        if isinstance(a, UploadOutcomeFileAction):
            file_name = str(getattr(a, "file_name", "") or "").strip()
            cnt = int(getattr(a, "expenses_count", 0) or 0)
            total = _fmt_money(float(getattr(a, "total_amount", 0.0) or 0.0))
            parts = []
            if file_name:
                parts.append(file_name)
            parts.append(f"{cnt} שורות")
            parts.append(f"סה״כ {total}")
            return " • ".join([p for p in parts if p])

        if isinstance(a, DeleteMovementAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            date = str(getattr(a, "date", "") or "").strip()
            amt = _fmt_money(float(getattr(a, "amount", 0.0) or 0.0))
            parts = []
            if acc:
                parts.append(acc)
            if date:
                parts.append(date)
            if amt:
                parts.append(amt)
            return " • ".join(parts)

        if isinstance(a, (AddIncomeMovementAction, AddOutcomeMovementAction)):
            mid = str(getattr(a, "movement_id", "") or "").strip()
            details = _movement_details(mid)
            if details:
                return details
            return "תנועה חדשה"

        if isinstance(a, AddInstallmentPlanAction):
            name = str(getattr(a, "plan_name", "") or "").strip()
            acc = str(getattr(a, "account_name", "") or "").strip()
            amt = _fmt_money(float(getattr(a, "original_amount", 0.0) or 0.0))
            parts = [p for p in (name, acc, (amt if amt else "")) if p]
            return " • ".join(parts) if parts else "תשלומים"

        if isinstance(a, EditInstallmentPlanAction):
            name = str(getattr(a, "plan_name", "") or "").strip()
            new_name = str(getattr(a, "new_name", "") or "").strip()
            if name and new_name and new_name != name:
                return f"{name} → {new_name}"
            return name or "תשלומים"

        if isinstance(a, DeleteInstallmentPlanAction):
            name = str(getattr(a, "plan_name", "") or "").strip()
            return name or "תשלומים"

        if isinstance(
            a, (AddOneTimeEventAction, EditOneTimeEventAction, DeleteOneTimeEventAction)
        ):
            name = str(getattr(a, "event_name", "") or "").strip()
            budget = getattr(a, "budget", None)
            parts = [p for p in (name,) if p]
            if isinstance(budget, (int, float)) and float(budget) != 0.0:
                parts.append(f"תקציב {_fmt_money(float(budget))}")
            return " • ".join(parts) if parts else "אירוע"

        if isinstance(a, AssignMovementToOneTimeEventAction):
            mid = str(getattr(a, "movement_id", "") or "").strip()
            details = _movement_details(mid)
            if details:
                return details
            # Never show raw IDs in the list.
            return "שיוך תנועה לאירוע"

        if isinstance(a, UnassignMovementFromOneTimeEventAction):
            mid = str(getattr(a, "movement_id", "") or "").strip()
            details = _movement_details(mid)
            if details:
                return details
            return "הסרת שיוך תנועה מאירוע"

        if isinstance(a, AddSavingsAccountAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            return acc or "חסכון"

        if isinstance(a, EditSavingsAccountAction):
            old = str(getattr(a, "old_name", "") or "").strip()
            new = str(getattr(a, "new_name", "") or "").strip()
            acc = str(getattr(a, "account_name", "") or "").strip()
            if old and new and old != new:
                return f"{old} → {new}"
            return acc or old or new or "חסכון"

        if isinstance(a, DeleteSavingsAccountAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            total = _fmt_money(float(getattr(a, "account_total_amount", 0.0) or 0.0))
            if acc and total:
                return f"{acc} • {total}"
            return acc or total or "חסכון"

        if isinstance(a, AddSavingAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            name = str(getattr(a, "saving_name", "") or "").strip()
            amt = _fmt_money(float(getattr(a, "saving_amount", 0.0) or 0.0))
            parts = [p for p in (acc, name, amt) if p]
            return " • ".join(parts) if parts else "חסכון"

        if isinstance(a, EditSavingAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            name = str(getattr(a, "saving_name", "") or "").strip()
            old = _fmt_money(float(getattr(a, "old_amount", 0.0) or 0.0))
            new = _fmt_money(float(getattr(a, "new_amount", 0.0) or 0.0))
            parts = [p for p in (acc, name) if p]
            if old and new and old != new:
                parts.append(f"{old} → {new}")
            return " • ".join(parts) if parts else "חסכון"

        if isinstance(a, DeleteSavingAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            name = str(getattr(a, "saving_name", "") or "").strip()
            amt = _fmt_money(float(getattr(a, "saving_amount", 0.0) or 0.0))
            parts = [p for p in (acc, name, amt) if p]
            return " • ".join(parts) if parts else "חסכון"

        if isinstance(a, ActivateBankAccountAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            starter = getattr(a, "starter_amount", None)
            if isinstance(starter, (int, float)):
                return (
                    f"{acc} • {_fmt_money(float(starter))}"
                    if acc
                    else _fmt_money(float(starter))
                )
            return acc or "חשבון"

        if isinstance(a, DeactivateBankAccountAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            return acc or "חשבון"

        if isinstance(a, SetStarterAmountAction):
            acc = str(getattr(a, "account_name", "") or "").strip()
            starter = _fmt_money(float(getattr(a, "starter_amount", 0.0) or 0.0))
            return f"{acc} • {starter}" if acc else starter

        if is_dataclass(a):
            fallback_parts: List[str] = []
            for k, v in vars(a).items():
                k_norm = str(k or "").strip()
                if k_norm in ("action_name", "success", "error_message"):
                    continue
                # Never show IDs in the list (movement_id, event_id, plan_id, ...).
                if k_norm == "id" or k_norm.endswith("_id") or k_norm.endswith("_ids"):
                    continue
                if v is None:
                    continue
                s = str(v).strip()
                if not s:
                    continue
                fallback_parts.append(s)
                if len(fallback_parts) >= 3:
                    break
            return " • ".join(fallback_parts) if fallback_parts else "פרטים"
    except Exception:
        return "פרטים"
    return "פרטים"


def _stripe_color_for_action(action_name: str, *, is_dark: bool) -> str:
    key = str(action_name or "").strip()
    if key in ("add_income_movement",):
        return "#6fbd58" if is_dark else "#97f57c"  # green
    if key in ("add_outcome_movement", "delete_movement"):
        return "#c76868" if is_dark else "#fe8383"  # red
    if key in ("upload_outcome_file",):
        return "#789bbf" if is_dark else "#96c7f8"  # blue
    if key in ("transfer",):
        return "#9670ba" if is_dark else "#ca98fa"  # purple
    if key.startswith("add_") or key.startswith("edit_"):
        return "#9feffd" if is_dark else "#4fc3f7"  # cyan/sky
    if key.startswith("delete_") or key.startswith("deactivate_"):
        return "#a3aebf"  # slate
    return "#f7c167"  # amber


class ActionHistoryTable(QWidget):
    def __init__(
        self,
        history: Optional[List[ActionHistory]] = None,
        max_rows: int = 10,
        parent: Optional[object] = None,
        categories: Optional[List[str]] = None,
        movement_service: Optional[BankMovementService] = None,
        on_saved: Optional[Callable[[], None]] = None,
        history_provider: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionHistoryTable")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        self._history: List[ActionHistory] = list(history or [])
        self._max_rows = max_rows
        self._categories = categories or []
        self._movement_service = movement_service
        self._on_saved = on_saved
        self._history_provider = history_provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._list = QListWidget(self)
        self._list.setObjectName("ActionHistoryListWidget")
        try:
            self._list.setContentsMargins(0, 8, 0, 0)
        except Exception:
            pass
        try:
            self._list.setViewportMargins(6, 12, 0, 0)
        except Exception:
            pass
        try:
            self._list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            self._list.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        except Exception:
            pass
        try:
            self._list.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        try:
            self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        except Exception:
            pass
        try:
            self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            pass
        try:
            self._list.setSpacing(2)
        except Exception:
            pass
        try:
            self._list.itemClicked.connect(self._on_item_clicked)
        except Exception:
            pass

        layout.addWidget(self._list, 1)

        self._apply_scrollbar_style()
        self._update_table()

    def _apply_scrollbar_style(self) -> None:
        try:
            is_dark = False
            try:
                app = QApplication.instance()
                if app is not None:
                    is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False

            handle = "#1e3a5f" if is_dark else "#93c5fd"
            handle_hover = "#2d5a8e" if is_dark else "#60a5fa"

            qss = """
                QListWidget#ActionHistoryListWidget { border: none; background: transparent; }
                QListWidget#ActionHistoryListWidget::item { border: none; background: transparent; }
                QListWidget#ActionHistoryListWidget QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                    margin: 8px 2px 8px 2px;
                    border: none;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical {
                    background: __HANDLE__;
                    border-radius: 999px;
                    min-height: 24px;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::handle:vertical:hover {
                    background: __HANDLE_HOVER__;
                }
                QListWidget#ActionHistoryListWidget QScrollBar:horizontal {
                    background: transparent;
                    height: 8px;
                    margin: 2px 8px 2px 8px;
                    border: none;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal {
                    background: __HANDLE__;
                    border-radius: 999px;
                    min-width: 24px;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::handle:horizontal:hover {
                    background: __HANDLE_HOVER__;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::add-line:vertical,
                QListWidget#ActionHistoryListWidget QScrollBar::sub-line:vertical,
                QListWidget#ActionHistoryListWidget QScrollBar::add-line:horizontal,
                QListWidget#ActionHistoryListWidget QScrollBar::sub-line:horizontal {
                    height: 0px;
                    width: 0px;
                    border: none;
                    background: transparent;
                }
                QListWidget#ActionHistoryListWidget QScrollBar::up-arrow,
                QListWidget#ActionHistoryListWidget QScrollBar::down-arrow,
                QListWidget#ActionHistoryListWidget QScrollBar::left-arrow,
                QListWidget#ActionHistoryListWidget QScrollBar::right-arrow {
                    background: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }
            """
            qss = qss.replace("__HANDLE__", handle).replace(
                "__HANDLE_HOVER__", handle_hover
            )
            self._list.setStyleSheet(qss)
        except Exception:
            pass

    def _is_dark_theme(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        try:
            theme_value = app.property("theme")
            if isinstance(theme_value, str):
                return theme_value.lower() == "dark"
        except Exception:
            pass
        try:
            palette = app.palette()
            try:
                window_color = palette.color(QPalette.ColorRole.Window)
            except Exception:
                try:
                    window_color = palette.window().color()
                except Exception:
                    return False
            try:
                return getattr(window_color, "lightness", lambda: 255)() < 128
            except Exception:
                return False
        except Exception:
            return False

    def set_history(self, history: List[ActionHistory]) -> None:
        self._history = history
        self._apply_scrollbar_style()
        self._update_table()

    def _on_item_clicked(self, item: Any) -> None:
        if item is None:
            return
        try:
            entry = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(entry, ActionHistory):
                return

            dialog = ActionHistoryDetailsDialog(
                entry,
                None,
                categories=self._categories,
                movement_service=self._movement_service,
                on_saved=self._on_saved,
                history_provider=self._history_provider,
            )
            dialog.exec()
        except Exception:
            pass

    def _update_table(self) -> None:
        self._apply_scrollbar_style()
        try:
            self._list.clear()
        except Exception:
            pass

        if not self._history:
            try:
                empty_item = QListWidgetItem()
                empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
                empty_w = QWidget()
                empty_l = QVBoxLayout(empty_w)
                empty_l.setContentsMargins(16, 24, 16, 24)
                empty_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl = QLabel("📋")
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl.setStyleSheet("font-size: 28px; color: #94a3b8; background: transparent;")
                msg_lbl = QLabel("אין היסטוריית פעולות עדיין")
                msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                msg_lbl.setObjectName("Subtitle")
                msg_lbl.setStyleSheet("background: transparent;")
                sub_lbl = QLabel("פעולות כמו הוספת תנועות יופיעו כאן")
                sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sub_lbl.setStyleSheet("font-size: 12px; color: #94a3b8; background: transparent;")
                empty_l.addWidget(icon_lbl)
                empty_l.addSpacing(8)
                empty_l.addWidget(msg_lbl)
                empty_l.addSpacing(4)
                empty_l.addWidget(sub_lbl)
                empty_item.setSizeHint(empty_w.sizeHint())
                self._list.addItem(empty_item)
                self._list.setItemWidget(empty_item, empty_w)
            except Exception:
                pass
            return

        max_rows = int(self._max_rows or 10)
        try:
            indexed = list(enumerate(self._history))
            indexed.sort(key=lambda p: (str(p[1].timestamp or ""), p[0]))
            latest_history = [p[1] for p in reversed(indexed)][:max_rows]
        except Exception:
            latest_history = list(reversed(list(self._history)))[:max_rows]
        is_dark = False
        try:
            is_dark = self._is_dark_theme()
        except Exception:
            is_dark = False

        movements_by_id: Dict[str, Any] = {}
        if self._movement_service is not None:
            try:
                all_moves = self._movement_service.list_movements()
                movements_by_id = {
                    str(getattr(m, "id", "") or "").strip(): m for m in all_moves
                }
            except Exception:
                movements_by_id = {}

        for entry in latest_history:
            title = _action_title(getattr(entry.action, "action_name", ""))
            body = _action_body(entry, movements_by_id=movements_by_id)
            date_str = str(entry.timestamp or "").strip()
            stripe_color = _stripe_color_for_action(
                getattr(entry.action, "action_name", ""), is_dark=is_dark
            )

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, entry)
            try:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            except Exception:
                pass

            row_w = _ActionHistoryRow(
                title=title,
                body=body,
                date_str=date_str,
                stripe_color=stripe_color,
                parent=self._list,
            )
            try:
                item.setSizeHint(QSize(10, 82))
            except Exception:
                pass
            try:
                self._list.addItem(item)
                self._list.setItemWidget(item, row_w)
            except Exception:
                pass


class _ActionHistoryRow(QWidget):
    def __init__(
        self,
        *,
        title: str,
        body: str,
        date_str: str,
        stripe_color: str,
        parent: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionHistoryRow")
        self._stripe_color = str(stripe_color or "").strip()
        self._stripe_px = 24
        # Avoid strict Qt type annotations here; our `qt` shim types are dynamic.
        self._outer: Optional[Any] = None
        self._content_layout: Optional[Any] = None
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        outer = QFrame(self)
        self._outer = outer
        outer.setObjectName("ActionHistoryCard")
        try:
            outer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._apply_card_style()

        content = QWidget(outer)
        content.setObjectName("ActionHistoryContent")
        content_layout = QVBoxLayout(content)
        self._content_layout = content_layout
        content_layout.setContentsMargins(int(self._stripe_px + 14), 10, 12, 10)
        content_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        title_label = QLabel(str(title or "").strip(), content)
        title_label.setObjectName("ActionHistoryTitle")
        try:
            title_label.setWordWrap(False)
        except Exception:
            pass

        date_label = QLabel(str(date_str or "").strip(), content)
        date_label.setObjectName("ActionHistoryDate")
        try:
            date_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass

        top_row.addWidget(title_label, 1)
        top_row.addWidget(date_label, 0)

        body_label = QLabel(str(body or "").strip(), content)
        body_label.setObjectName("ActionHistoryBody")
        try:
            body_label.setWordWrap(True)
        except Exception:
            pass

        content_layout.addLayout(top_row)
        content_layout.addWidget(body_label, 0)

        outer_layout.addWidget(content, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(outer, 1)

        try:
            self.setMinimumHeight(76)
        except Exception:
            pass

    def resizeEvent(self, event) -> None:
        try:
            self._apply_card_style()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            return

    def _apply_card_style(self) -> None:
        outer = self._outer
        if outer is None:
            return
        try:
            is_dark = False
            try:
                app = QApplication.instance()
                if app is not None:
                    is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False

            base_bg = "#020617" if is_dark else "#dbeafe"
            border = "#1f2937" if is_dark else "#bfdbfe"
            stripe_color = self._stripe_color or "#9fc6f7"

            w = max(int(outer.width() or 0), 1)
            stop = float(self._stripe_px) / float(w)
            if stop < 0.0:
                stop = 0.0
            if stop > 0.4:
                stop = 0.4

            outer.setStyleSheet(
                f"""
                QFrame#ActionHistoryCard {{
                    border-radius: 18px;
                    border: 1px solid {border};
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0 {stripe_color},
                        stop: {stop:.4f} {stripe_color},
                        stop: {stop:.4f} {base_bg},
                        stop: 1 {base_bg}
                    );
                }}
                """
            )

            if self._content_layout is not None:
                self._content_layout.setContentsMargins(
                    int(self._stripe_px + 14), 10, 12, 10
                )
        except Exception:
            return
