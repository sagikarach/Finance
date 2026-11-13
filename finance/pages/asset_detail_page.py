from __future__ import annotations

from dataclasses import replace
from typing import Dict, List, Optional

from ..qt import (
    QWidget,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QDialog,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QScrollArea,
    QSizePolicy,
    Qt,
    QDate,
    QTimer,
    QColor,
)
from ..models.accounts import (
    MoneyAccount,
    parse_iso_date,
)
from ..models.transfers import funding_endpoints
from ..ui.dialog_utils import setup_calendar_popup
from ..models.mortgage import (
    AssetKind,
    CostItem,
    FundingKind,
    FundingSource,
    Mortgage,
    endpoint_balance,
)
from ..models.mortgage_service import MortgageService
from ..models.asset import (
    DEFAULT_ASSUMPTIONS,
    HousePurchase,
    MortgageLoan,
    build_asset,
    expense_breakdown_rows,
    funding_breakdown_rows,
)
from ..models.mortgage_math import (
    average_monthly,
    cost_matched_movements,
    cost_monthly_average,
    equity_split,
    query_paid_amount,
    yearly_cost_cycles,
)
from ..models.asset_expense_service import AssetExpenseService
from ..models.car_costs import selection_label
from ..widgets.category_combo import CategoryChecklist, category_label
from .mortgage_page import HousePurchaseDialog
from .base_page import BasePage

_BANK_ACCOUNT_NAME = "בנק"  # החשבון שמכסה את היתרה (תואם למסך המשכנתא)

_MONTH_NAMES = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]


class _DetailTile(QFrame):
    """A clickable tile: bold name + muted subtitle + chevron. Opens a focused
    dialog (or navigates) so the overview stays clean."""

    def __init__(self, name, subtitle, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailTile")
        self._on_click = on_click
        try:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(10)
        col = QVBoxLayout()
        col.setSpacing(3)
        name_lbl = QLabel(str(name), self)
        name_lbl.setObjectName("TileName")
        self._sub_lbl = QLabel(str(subtitle), self)
        self._sub_lbl.setObjectName("TileSub")
        self._sub_lbl.setWordWrap(True)
        col.addWidget(name_lbl)
        col.addWidget(self._sub_lbl)
        row.addLayout(col, 1)
        chev = QLabel("‹", self)
        chev.setObjectName("TileChev")
        row.addWidget(chev, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):  # noqa: N802
        super().mousePressEvent(event)
        # DEFER the callback: it opens a dialog that rebuilds the page and
        # deletes this tile. Running it synchronously deletes the widget while
        # Qt is still dispatching this mouse event, and Qt's C++ machinery then
        # touches the freed object → SIGSEGV. singleShot(0) runs it after the
        # event fully unwinds, when nothing holds the tile any more.
        cb = self._on_click
        if callable(cb):
            QTimer.singleShot(0, cb)


from ..utils.formatting import fmt_money as _fmt_money


from ..utils.formatting import parse_float as _parse_float
from ..utils.safe import QT_ERRORS


class FundingSourceDialog(QDialog):
    """עריכת מקור מימון: שם, סוג, סכום מוקצה, וחיפוש/חשבון לפי הסוג."""

    def __init__(
        self,
        *,
        accounts: List[MoneyAccount],
        source: Optional[FundingSource] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("מקור מימון")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        self._accounts = accounts
        self._source = source

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)
        title = QLabel("מקור מימון", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם (לדוגמה: מתנה מההורים)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._kind = QComboBox(self)
        self._kind.addItems([k.value for k in FundingKind])
        root.addWidget(QLabel("סוג", self))
        root.addWidget(self._kind)

        self._amount = QLineEdit(self)
        self._amount.setPlaceholderText("סכום מוקצה / צפוי")
        root.addWidget(QLabel("סכום", self))
        root.addWidget(self._amount)

        # בחירה ברמת ההעברות: חשבון בנק או חיסכון ספציפי בתוך חשבון חיסכון.
        self._account = QComboBox(self)
        self._account.addItem("", ("", ""))
        for label, acc_name, sv_name, _bal in funding_endpoints(accounts):
            self._account.addItem(label, (acc_name, sv_name))
        self._account_label = QLabel("חשבון / חיסכון", self)
        root.addWidget(self._account_label)
        root.addWidget(self._account)
        self._balance_lbl = QLabel("", self)
        root.addWidget(self._balance_lbl)

        self._query = QLineEdit(self)
        self._query.setPlaceholderText("חיפוש תנועות נכנסות (לדוגמה: מתנה)")
        self._query_label = QLabel("חיפוש תנועות", self)
        root.addWidget(self._query_label)
        root.addWidget(self._query)

        self._kind.currentTextChanged.connect(self._on_kind_changed)
        self._account.currentIndexChanged.connect(self._update_balance_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_btn = QPushButton("שמור", self)
        cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

        self._load_initial()
        self._on_kind_changed(self._kind.currentText())

    def _load_initial(self) -> None:
        s = self._source
        if s is None:
            return
        self._name.setText(str(s.name or ""))
        try:
            self._kind.setCurrentText(str(getattr(s.kind, "value", s.kind)))
        except QT_ERRORS:
            pass
        if s.amount:
            self._amount.setText(f"{float(s.amount):.0f}")
        # בחר את הפריט התואם (חשבון + חיסכון). הערך נשמר כ-tuple אך Qt מחזיר
        # אותו כ-list, לכן משווים אחרי נירמול לזוג מחרוזות.
        target = (str(s.account_name or ""), str(s.saving_name or ""))
        if target != ("", ""):
            idx = -1
            for i in range(self._account.count()):
                d = self._account.itemData(i)
                cur = (str(d[0]), str(d[1])) if d and len(d) >= 2 else ("", "")
                if cur == target:
                    idx = i
                    break
            if idx < 0:
                # החשבון/חיסכון אינו מוצע יותר (למשל נמחק) — מוסיפים אותו כדי
                # לא לאבד את השיוך בעת עריכה.
                label = f"{target[0]} / {target[1]}" if target[1] else target[0]
                self._account.addItem(label, (target[0], target[1]))
                idx = self._account.count() - 1
            self._account.setCurrentIndex(idx)
        self._query.setText(str(s.query or ""))

    def _on_kind_changed(self, text: str) -> None:
        is_account = str(text) == FundingKind.ACCOUNT.value
        is_movements = str(text) == FundingKind.MOVEMENTS.value
        self._account_label.setVisible(is_account)
        self._account.setVisible(is_account)
        self._balance_lbl.setVisible(is_account)
        self._query_label.setVisible(is_movements)
        self._query.setVisible(is_movements)
        self._update_balance_label()

    def _update_balance_label(self, *_args) -> None:
        data = self._account.currentData() or ("", "")
        acc_name, sv_name = data
        if acc_name:
            bal = endpoint_balance(self._accounts, acc_name, sv_name)
            label = "יתרת החיסכון" if sv_name else "יתרת החשבון"
            self._balance_lbl.setText(f"{label}: {_fmt_money(bal)} ₪")
        else:
            self._balance_lbl.setText("")

    def _on_save(self) -> None:
        try:
            kind = FundingKind(str(self._kind.currentText()))
        except QT_ERRORS:
            kind = FundingKind.FUTURE
        account_name = ""
        saving_name = ""
        if kind == FundingKind.ACCOUNT:
            data = self._account.currentData() or ("", "")
            account_name, saving_name = str(data[0]), str(data[1])
        default_name = self._account.currentText() if kind == FundingKind.ACCOUNT else ""
        name = str(self._name.text() or "").strip() or default_name.strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "שם מקור המימון לא יכול להיות ריק")
            return
        query = (
            str(self._query.text() or "").strip()
            if kind == FundingKind.MOVEMENTS
            else ""
        )
        self._source = FundingSource(
            name=name,
            amount=_parse_float(self._amount.text()) or 0.0,
            kind=kind,
            query=query,
            account_name=account_name,
            saving_name=saving_name,
        )
        self.accept()

    def get_source(self) -> Optional[FundingSource]:
        return self._source


class CostItemDialog(QDialog):
    """עריכת שורת עלות (הוצאה חד-פעמית): שם, סכום, וחיפוש תנועות אופציונלי."""

    def __init__(
        self,
        *,
        cost: Optional[CostItem] = None,
        show_query: bool = True,
        show_renewal: bool = False,
        show_amount: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("הוצאה")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        self._cost = cost
        self._initial_cost = cost
        self._show_renewal = show_renewal

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)
        title = QLabel("הוצאה", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם (לדוגמה: מס רכישה / עו\"ד / מובילים)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._amount = QLineEdit(self)
        # לעלויות שנתיות הסכום נגזר מהתנועות לכל מחזור — לכן אופציונלי.
        self._amount.setPlaceholderText(
            "סכום מתוכנן (אופציונלי — נגזר מהתנועות)"
            if (show_renewal or show_query)
            else "סכום מתוכנן"
        )
        self._amount_label = QLabel("סכום", self)
        root.addWidget(self._amount_label)
        root.addWidget(self._amount)
        if not show_amount:
            # Amount comes only from the movement search — hide the manual field.
            self._amount_label.setVisible(False)
            self._amount.setVisible(False)

        self._query = QLineEdit(self)
        self._query.setPlaceholderText("חיפוש תנועות (אופציונלי) — לחישוב ששולם בפועל")
        self._query_label = QLabel("חיפוש תנועות", self)
        root.addWidget(self._query_label)
        root.addWidget(self._query)
        if not show_query:
            self._query_label.setVisible(False)
            self._query.setVisible(False)

        # חודש חידוש שנתי — מגדיר מתי מתחיל המחזור השנתי של העלות.
        self._renewal = QComboBox(self)
        self._renewal.addItem("ללא", 0)
        for i, mn in enumerate(_MONTH_NAMES, start=1):
            self._renewal.addItem(mn, i)
        self._renewal_label = QLabel("חודש חידוש (תחילת השנה)", self)
        root.addWidget(self._renewal_label)
        root.addWidget(self._renewal)
        if not show_renewal:
            self._renewal_label.setVisible(False)
            self._renewal.setVisible(False)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_btn = QPushButton("שמור", self)
        cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

        if cost is not None:
            self._name.setText(str(cost.name or ""))
            if cost.amount:
                self._amount.setText(f"{float(cost.amount):.0f}")
            self._query.setText(str(getattr(cost, "query", "") or ""))
            rm = int(getattr(cost, "renewal_month", 0) or 0)
            idx = self._renewal.findData(rm)
            if idx >= 0:
                self._renewal.setCurrentIndex(idx)

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        query = str(self._query.text() or "").strip()
        if not name and not query:
            QMessageBox.warning(self, "שגיאה", "שם ההוצאה לא יכול להיות ריק")
            return
        renewal = 0
        try:
            renewal = int(self._renewal.currentData() or 0)
        except QT_ERRORS:
            renewal = 0
        prev = getattr(self, "_initial_cost", None)
        self._cost = CostItem(
            name=name,
            amount=_parse_float(self._amount.text()) or 0.0,
            query=query,
            renewal_month=renewal,
            excluded_movement_ids=list(
                getattr(prev, "excluded_movement_ids", None) or []
            ),
        )
        self.accept()

    def get_cost(self) -> Optional[CostItem]:
        return self._cost


class CostMovementsDialog(QDialog):
    """The bank movements an expense item's search matched (e.g. every 'ועד
    בית' charge), with exclude/restore — so a one-off catch-up payment or a
    look-alike movement doesn't skew the item's average."""

    def __init__(
        self,
        *,
        cost: CostItem,
        movements: list,
        yearly: bool = False,
        parent: Optional[QWidget] = None,
        candidates: Optional[list] = None,
        subtitle: Optional[str] = None,
        locked: Optional[Dict[str, str]] = None,
        show_category: bool = False,
    ) -> None:
        """``candidates`` (instead of the cost's text search) lists the
        movements to show; ``locked`` maps movement id → a status shown for a
        row that is not counted here and cannot be toggled (e.g. counted by a
        yearly item, or waiting for review)."""
        super().__init__(parent)
        self._cost = cost
        self._yearly = bool(yearly)
        self._locked: Dict[str, str] = dict(locked or {})
        self._show_category = bool(show_category)
        self._excluded: List[str] = [
            str(x) for x in (cost.excluded_movement_ids or []) if str(x).strip()
        ]
        # Every match, newest first, including excluded ones (shown dimmed).
        source = (
            list(candidates)
            if candidates is not None
            else cost_matched_movements(cost, movements, apply_exclusions=False)
        )
        self._all = sorted(
            source,
            key=lambda mv: str(getattr(mv, "date", "") or ""),
            reverse=True,
        )
        title = f"תנועות · {cost.name or cost.query}"
        self.setWindowTitle(title)
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.resize(720, 520)
        except QT_ERRORS:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(10)
        head = QLabel(title, self)
        head.setObjectName("HeaderTitle")
        root.addWidget(head)
        sub = QLabel(subtitle if subtitle is not None else f"חיפוש: \"{cost.query}\"", self)
        sub.setObjectName("Subtitle")
        root.addWidget(sub)
        self._summary = QLabel("", self)
        self._summary.setObjectName("Subtitle")
        self._summary.setWordWrap(True)
        root.addWidget(self._summary)

        self._table = QTableWidget(self)
        self._table.setObjectName("ActionHistoryTableWidget")
        headers = ["תאריך", "סכום", "תיאור", "סטטוס"]
        if self._show_category:
            headers.insert(2, "קטגוריה")
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = self._table.horizontalHeader()
            if hh is not None:
                hh.setObjectName("ActionHistoryHeader")
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            vh = self._table.verticalHeader()
            if vh is not None:
                vh.setVisible(False)
        except QT_ERRORS:
            pass
        self._table.doubleClicked.connect(lambda _i: self._toggle_selected())
        self._table.itemSelectionChanged.connect(self._update_toggle_text)
        root.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        self._toggle_btn = QPushButton("החרג תנועה", self)
        self._toggle_btn.setToolTip("תנועה מוחרגת לא נספרת בממוצע של הפריט")
        self._toggle_btn.clicked.connect(self._toggle_selected)
        buttons.addWidget(self._toggle_btn)
        buttons.addStretch(1)
        save = QPushButton("שמור", self)
        cancel = QPushButton("בטל", self)
        save.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        self._fill()

    @staticmethod
    def _date_he(raw: str) -> str:
        try:
            dt = parse_iso_date(str(raw or ""))
            return f"{dt.day} ב{_MONTH_NAMES[dt.month - 1]} {dt.year}"
        except QT_ERRORS:
            return str(raw or "")

    def _included(self) -> list:
        ex = set(self._excluded) | set(self._locked)
        return [mv for mv in self._all if str(getattr(mv, "id", "")) not in ex]

    def _fill(self) -> None:
        ex = set(self._excluded)
        self._table.setRowCount(len(self._all))
        for row, mv in enumerate(self._all):
            mid = str(getattr(mv, "id", "") or "")
            is_ex = mid in ex
            try:
                amt = float(getattr(mv, "amount", 0.0) or 0.0)
            except QT_ERRORS:
                amt = 0.0
            lock = self._locked.get(mid)
            status = lock or ("הוחרג" if is_ex else "נכלל")
            cells = [
                QTableWidgetItem(self._date_he(str(getattr(mv, "date", "")))),
                QTableWidgetItem(f"{_fmt_money(amt)} ₪"),
                QTableWidgetItem(str(getattr(mv, "description", "") or "")),
                QTableWidgetItem(status),
            ]
            if self._show_category:
                cells.insert(
                    2, QTableWidgetItem(category_label(str(getattr(mv, "category", "") or "")))
                )
            status_col = len(cells) - 1
            for col, it in enumerate(cells):
                try:
                    it.setData(Qt.ItemDataRole.UserRole, mid)
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if is_ex or lock:
                        it.setForeground(QColor("#9aa3b2"))
                    elif col == 1:
                        it.setForeground(QColor("#d66a4e"))
                    elif col == status_col:
                        it.setForeground(QColor("#2f9e68"))
                except QT_ERRORS:
                    pass
                self._table.setItem(row, col, it)
        self._update_summary()
        self._update_toggle_text()

    def _update_summary(self) -> None:
        inc = self._included()
        n_locked = sum(1 for mv in self._all if str(getattr(mv, "id", "")) in self._locked)
        n_ex = len(self._all) - len(inc) - n_locked
        total = sum(abs(float(getattr(mv, "amount", 0.0) or 0.0)) for mv in inc)
        avg, months = average_monthly(inc)
        parts = [f"{len(inc)} תנועות נכללות", f"סה״כ {_fmt_money(total)} ₪"]
        if not self._yearly and months:
            parts.append(f"ממוצע חודשי {_fmt_money(avg)} ₪ ({months} חודשים)")
        if n_ex:
            parts.append(f"{n_ex} הוחרגו")
        if n_locked:
            parts.append(f"{n_locked} לא נספרות כאן")
        if not self._all:
            parts = ["לא נמצאו תנועות שתואמות את החיפוש"]
        try:
            self._summary.setText("  ·  ".join(parts))
        except QT_ERRORS:
            pass

    def _selected_row(self) -> int:
        try:
            rows = sorted({i.row() for i in self._table.selectedIndexes()})
            if rows:
                return rows[0]
            return int(self._table.currentRow())
        except QT_ERRORS:
            return -1

    def _selected_id(self) -> str:
        try:
            row = self._selected_row()
            it = self._table.item(row, 0) if row >= 0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""
        except QT_ERRORS:
            return ""

    def _update_toggle_text(self) -> None:
        mid = self._selected_id()
        try:
            self._toggle_btn.setEnabled(bool(mid) and mid not in self._locked)
            self._toggle_btn.setText(
                "החזר תנועה" if mid and mid in self._excluded else "החרג תנועה"
            )
        except QT_ERRORS:
            pass

    def _toggle_selected(self) -> None:
        mid = self._selected_id()
        if not mid or mid in self._locked:
            return
        row = self._selected_row()
        if mid in self._excluded:
            self._excluded.remove(mid)
        else:
            self._excluded.append(mid)
        self._fill()
        try:
            if 0 <= row < self._table.rowCount():
                self._table.setCurrentCell(row, 0)
        except QT_ERRORS:
            pass

    def get_cost(self) -> CostItem:
        return replace(self._cost, excluded_movement_ids=list(self._excluded))


class AssetDetailPage(BasePage):
    """עמוד הנכס (רכישה) — מציג את כל התשלומים בתהליך, כולל המשכנתא כחלק לחיץ."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("page_title", "נכס")
        kwargs.setdefault("current_route", "asset")
        self._service = MortgageService()
        self._expenses = AssetExpenseService(self._service)
        self._funding_table: Optional[QTableWidget] = None
        self._funding_sources: List[FundingSource] = []
        self._expense_table: Optional[QTableWidget] = None
        self._one_time_costs: List[CostItem] = []
        self._monthly_table: Optional[QTableWidget] = None
        self._monthly_costs: List[CostItem] = []
        self._active_tab: str = "expenses"
        self._tab_cards: dict = {}
        self._tab_buttons: dict = {}
        self._details_dialog: Optional[QDialog] = None
        self._details_host: Optional[QWidget] = None
        self._yearly_costs: List[CostItem] = []
        self._yearly_table: Optional[QTableWidget] = None
        self._yearly_host: Optional[QWidget] = None
        super().__init__(*args, **kwargs)

    def _load_accounts(self) -> List[MoneyAccount]:
        try:
            return list(self._accounts_service.load_accounts() or [])
        except QT_ERRORS:
            return list(self._accounts or [])

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            try:
                self.setUpdatesEnabled(False)
                self._clear_content_layout(self._content_col)
                self._build_content(self._content_col)
            finally:
                self.setUpdatesEnabled(True)
                self.update()

    def _selected_asset(self) -> Optional[Mortgage]:
        try:
            sel = str(self._app_context.get("selected_mortgage_id") or "").strip()
        except QT_ERRORS:
            sel = ""
        if not sel:
            return None
        for m in self._service.list_mortgages():
            if m.id == sel:
                return m
        return None

    def _build_content(self, content_col: QVBoxLayout) -> None:
        self._clear_content_layout(content_col)

        root = QWidget(self)
        try:
            root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        content_col.addWidget(root, 1)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        m = self._selected_asset()
        if m is None:
            lay.addWidget(QLabel("לא נבחר נכס. חזור לרשימת הנכסים.", root), 0)
            lay.addStretch(1)
            return

        # פירורי לחם — נכסים › שם הנכס (מבהיר את היררכיית הניווט התלת-שלבית).
        crumb = QLabel(f"נכסים  ›  {m.name or '(ללא שם)'}", root)
        crumb.setObjectName("AssetBreadcrumb")
        lay.addWidget(crumb, 0)

        # כותרת + כפתורי פעולה (חזרה, עריכת רכישה). כפתור המשכנתא ירד לשורה נפרדת.
        title_row = QHBoxLayout()
        back_btn = QToolButton(root)
        back_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(back_btn, "arrow_right", size=20, is_dark=self._is_dark_theme())
        except QT_ERRORS:
            back_btn.setText("→")
        back_btn.setToolTip("חזרה לרשימת הנכסים")
        if self._navigate is not None:
            back_btn.clicked.connect(lambda: self._navigate("assets"))
        title_row.addWidget(back_btn, 0)

        name_lbl = QLabel(m.name or "(ללא שם)", root)
        name_lbl.setObjectName("HeaderTitle")
        title_row.addWidget(name_lbl, 0)
        title_row.addStretch(1)

        edit_btn = QToolButton(root)
        edit_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(edit_btn, "edit", size=20, is_dark=self._is_dark_theme())
        except QT_ERRORS:
            edit_btn.setText("✎")
        if m.kind == AssetKind.CAR:
            edit_btn.setToolTip("ערוך פרטי רכב")
            edit_btn.clicked.connect(lambda: self._open_car_details_dialog())
        else:
            edit_btn.setToolTip("ערוך מחיר ועלויות")
            edit_btn.clicked.connect(self._on_edit_purchase)
        title_row.addWidget(edit_btn)
        lay.addLayout(title_row, 0)

        # רכב — עמוד ייעודי (שווי מתעדכן ידנית, הלוואה אופציונלית, עלויות שנתיות).
        if m.kind == AssetKind.CAR:
            self._build_car_body(lay, root, m)
            return

        s = self._service.purchase_summary(m)

        # ── מצב נוכחי: שווי, יתרה, הון עצמי וסטטוס המשכנתא ──
        prepaid = self._service.prepaid_amount(m)
        st = MortgageLoan(m).status(
            assumptions=DEFAULT_ASSUMPTIONS,
            prepaid=prepaid,
            paid_count=self._service.paid_payments_count(m),
        )
        value = float(build_asset(m).current_value())
        # היתרה האמיתית = כל התשלומים שנותרו (קרן + ריבית עתידית).
        outstanding = float(st.remaining_total)
        equity, eq_frac = equity_split(value, outstanding)

        two = QHBoxLayout()
        two.setSpacing(16)
        two.addWidget(
            self._build_equity_panel(root, value, outstanding, equity, eq_frac), 1
        )
        two.addWidget(self._build_status_panel(root, st), 1)
        lay.addLayout(two, 0)

        lay.addWidget(self._build_allin_strip(root, m, s), 0)

        details_title = QLabel("פרטים נוספים", root)
        details_title.setObjectName("PanelTitle")
        lay.addWidget(details_title, 0)

        grid = QVBoxLayout()
        grid.setSpacing(12)
        r1 = QHBoxLayout()
        r1.setSpacing(12)
        r1.addWidget(
            _DetailTile(
                "עלויות רכישה",
                f"עלות כוללת {_fmt_money(s.acquisition_cost)} ₪ · "
                f"כסף עצמי {_fmt_money(s.upfront_cash)} ₪",
                lambda: self._open_details_dialog("expenses"),
                root,
            ),
            1,
        )
        r1.addWidget(
            _DetailTile(
                "מקורות מימון",
                f"מימון {s.ltv * 100:.0f}% משווי הנכס",
                lambda: self._open_details_dialog("income"),
                root,
            ),
            1,
        )
        grid.addLayout(r1)
        r2 = QHBoxLayout()
        r2.setSpacing(12)
        # Monthly + yearly expenses summed from the house's OWN cost items (the
        # lists in the הוצאות הבית dialog), each derived from its movement search.
        # NOT a category average.
        _hx = self._expenses.house_cost_expenses(m)
        has_items = bool(getattr(m, "monthly_costs", None)) or bool(
            getattr(m, "yearly_costs", None)
        )
        monthly_txt = f"{_fmt_money(_hx.monthly)} ₪" if has_items else "—"
        yearly_txt = f"{_fmt_money(_hx.yearly)} ₪" if has_items else "—"
        r2.addWidget(
            _DetailTile(
                "הוצאות הבית",
                f"ממוצע חודשי · {monthly_txt}\nממוצע שנתי · {yearly_txt}",
                lambda: self._open_details_dialog("house_costs"),
                root,
            ),
            1,
        )
        r2.addWidget(
            _DetailTile(
                "מסלולי המשכנתא · גרף · סימולציה",
                f"{len(m.tracks)} מסלולים · ריבית צפויה "
                f"{_fmt_money(st.total_interest)} ₪",
                self._open_mortgage,
                root,
            ),
            1,
        )
        grid.addLayout(r2)
        lay.addLayout(grid, 0)

        lay.addStretch(1)

    def _build_details_widget(self, parent, m, s):
        """Return ONLY the panel for the requested detail (self._active_tab).
        Each detail opens in its own separate dialog — there is no tab bar, so
        you can't move between them; each is reached from its tile only."""
        key = self._active_tab
        if key == "income":
            return self._build_funding_panel(parent, m, s)
        if key == "monthly":
            return self._build_monthly_panel(parent, m)
        if key == "house_costs":
            return self._build_house_costs_panel(parent, m)
        return self._build_expenses_panel(parent, m)

    def _build_house_costs_panel(self, parent, m):
        """הוצאות הבית — ניהול העלויות החודשיות והשנתיות יחד, זו מעל זו."""
        scroll = QScrollArea(parent)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget(scroll)
        v = QVBoxLayout(inner)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        v.addWidget(self._build_monthly_panel(inner, m))
        v.addWidget(self._build_yearly_panel(inner, m))
        v.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    def _build_expenses_panel(self, parent, m):
        movements = self._service.list_movements()
        price_query = str(getattr(m, "price_query", "") or "").strip()
        price_paid = (
            query_paid_amount(price_query, movements, include_transfers=True)
            if price_query
            else 0.0
        )
        self._one_time_costs = list(m.one_time_costs)
        expenses_card, expenses_table = self._panel_with_actions(
            "הוצאות — עלות מלאה ושולם בפועל",
            self._on_add_cost,
            self._on_edit_cost,
            self._on_remove_cost,
        )
        self._expense_table = expenses_table
        expenses_table.setColumnCount(3)
        expenses_table.setHorizontalHeaderLabels(["רכיב", "סכום", "שולם בפועל"])
        expenses_table.doubleClicked.connect(self._on_edit_cost)
        expense_rows = expense_breakdown_rows(
            float(m.property_price), price_paid, self._one_time_costs, movements
        )
        expenses_table.setRowCount(len(expense_rows))
        for r, row in enumerate(expense_rows):
            if row.is_total:
                paid_text = _fmt_money(row.paid)
            else:
                paid_text = _fmt_money(row.paid) if row.paid else "—"
            expenses_table.setItem(r, 0, QTableWidgetItem(row.label))
            expenses_table.setItem(r, 1, QTableWidgetItem(_fmt_money(row.amount)))
            expenses_table.setItem(r, 2, QTableWidgetItem(paid_text))
        return expenses_card

    def _build_funding_panel(self, parent, m, s):
        root = parent
        movements = self._service.list_movements()
        accounts = self._load_accounts()
        self._funding_sources = list(m.funding_sources)
        exp_paid = self._expenses.acquisition_paid(m)
        residual = s.residual_from_bank
        remaining_need = self._expenses.financing_gap(m, residual)
        # ───────── צד ההכנסות / מקורות מימון (כניסה) ─────────
        income_card = QWidget(root)
        income_card.setObjectName("AssetTablePanel")
        try:
            income_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            income_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except QT_ERRORS:
            pass
        il = QVBoxLayout(income_card)
        il.setContentsMargins(16, 16, 16, 16)
        il.setSpacing(8)
        inc_header = QHBoxLayout()
        inc_header.addWidget(QLabel("הכנסות / מקורות מימון", income_card), 0)
        inc_header.addStretch(1)
        add_f = QToolButton(income_card)
        add_f.setText("➕")
        add_f.setToolTip("הוסף מקור מימון")
        add_f.clicked.connect(self._on_add_funding)
        edit_f = QToolButton(income_card)
        edit_f.setText("✎")
        edit_f.setToolTip("ערוך מקור מימון")
        edit_f.clicked.connect(self._on_edit_funding)
        rm_f = QToolButton(income_card)
        rm_f.setText("🗑")
        rm_f.setToolTip("מחק מקור מימון")
        rm_f.clicked.connect(self._on_remove_funding)
        inc_header.addWidget(add_f)
        inc_header.addWidget(edit_f)
        inc_header.addWidget(rm_f)
        il.addLayout(inc_header)

        income_table = QTableWidget(income_card)
        income_table.setObjectName("ActionHistoryTableWidget")
        income_table.setColumnCount(5)
        income_table.setHorizontalHeaderLabels(
            ["מקור", "סוג", "סכום", "זמין בפועל", "הוצא בפועל"]
        )
        income_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        income_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        income_table.setAlternatingRowColors(False)
        try:
            income_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh2 = income_table.horizontalHeader()
            if hh2 is not None:
                hh2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh2.setObjectName("ActionHistoryHeader")
        except QT_ERRORS:
            pass
        income_table.doubleClicked.connect(self._on_edit_funding)
        self._funding_table = income_table

        # שורות מקורות המימון (קודם — מתאימות לאינדקסים לעריכה/מחיקה),
        # ואז שורת המשכנתא האוטומטית, שורת חשבון הבנק, ואז סה״כ. החישוב נעשה
        # ב-funding_breakdown_rows (לוגיקה טהורה); כאן רק מציירים את השורות.
        rows = funding_breakdown_rows(
            self._funding_sources,
            movements,
            accounts,
            tracks_total=float(s.tracks_total),
            residual=residual,
            remaining_need=remaining_need,
            exp_paid=exp_paid,
            bank_account_name=_BANK_ACCOUNT_NAME,
        )
        income_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            if row.is_total:
                spent_text = ""
            else:
                spent_text = _fmt_money(row.spent) if row.spent else "—"
            income_table.setItem(i, 0, QTableWidgetItem(row.label))
            income_table.setItem(i, 1, QTableWidgetItem(row.kind))
            income_table.setItem(i, 2, QTableWidgetItem(_fmt_money(row.amount)))
            income_table.setItem(i, 3, QTableWidgetItem(_fmt_money(row.available)))
            income_table.setItem(i, 4, QTableWidgetItem(spent_text))
        il.addWidget(income_table, 1)
        return income_card

    def _build_monthly_panel(self, parent, m):
        self._monthly_costs = list(m.monthly_costs)
        monthly_card, monthly_table = self._panel_with_actions(
            "עלויות חודשיות נלוות",
            self._on_add_monthly_cost,
            self._on_edit_monthly_cost,
            self._on_remove_monthly_cost,
            self._on_monthly_cost_movements,
        )
        self._monthly_table = monthly_table
        movements = self._service.list_movements()
        monthly_table.setColumnCount(3)
        monthly_table.setHorizontalHeaderLabels(["רכיב", "חיפוש תנועות", "סכום לחודש"])
        # Double-click shows the matched movements (✎ still edits the item).
        monthly_table.doubleClicked.connect(self._on_monthly_cost_movements)
        monthly_table.setRowCount(len(self._monthly_costs) + 1)
        m_total = 0.0
        for i, c in enumerate(self._monthly_costs):
            query = str(getattr(c, "query", "") or "").strip()
            # When a movement search is set, the amount is DERIVED from the
            # matched movements (monthly average); otherwise use the typed sum.
            amount = cost_monthly_average(c, movements) if query else float(c.amount)
            m_total += amount
            monthly_table.setItem(i, 0, QTableWidgetItem(str(c.name)))
            monthly_table.setItem(
                i, 1, QTableWidgetItem(self._query_cell(c, movements))
            )
            monthly_table.setItem(i, 2, QTableWidgetItem(_fmt_money(amount)))
        monthly_table.setItem(len(self._monthly_costs), 0, QTableWidgetItem("סה״כ"))
        monthly_table.setItem(
            len(self._monthly_costs), 2, QTableWidgetItem(_fmt_money(m_total))
        )
        return monthly_card

    # ----------------------------------------------------------------- car
    def _labeled_edit(self, parent, layout, label, value=""):
        layout.addWidget(QLabel(label, parent))
        e = QLineEdit(parent)
        e.setText(str(value))
        layout.addWidget(e)
        return e

    def _labeled_date(self, parent, layout, label, value_iso=""):
        layout.addWidget(QLabel(label, parent))
        d = QDateEdit(parent)
        d.setCalendarPopup(True)
        setup_calendar_popup(d)
        try:
            d.setDisplayFormat("yyyy-MM-dd")
        except QT_ERRORS:
            pass
        try:
            dt = parse_iso_date(str(value_iso or ""))
            d.setDate(QDate(dt.year, dt.month, dt.day))
        except QT_ERRORS:
            try:
                d.setDate(QDate.currentDate())
            except QT_ERRORS:
                pass
        layout.addWidget(d)
        return d

    def _build_car_body(self, lay, root, m):
        a = build_asset(m)  # CarAsset
        current = float(a.current_value())
        initial = float(a.purchase_price)

        lay.addWidget(self._build_car_value_panel(root, current, initial), 0)
        lay.addWidget(self._build_car_expenses_stats(root, a), 0)

        details_title = QLabel("פרטים נוספים", root)
        details_title.setObjectName("PanelTitle")
        lay.addWidget(details_title, 0)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(
            _DetailTile(
                "עדכן שווי רכב",
                "עדכון ידני · מחירון העם",
                self._open_update_value_dialog,
                root,
            ),
            1,
        )
        row.addWidget(
            _DetailTile(
                "פרטי הרכב והמחיר",
                f"מחיר קנייה {_fmt_money(initial)} ₪",
                self._open_car_details_dialog,
                root,
            ),
            1,
        )
        row.addWidget(
            _DetailTile(
                "עלויות שנתיות",
                f"ביטוח · טסט · אגרה  ·  {len(m.yearly_costs)} פריטים",
                self._open_yearly_costs_dialog,
                root,
            ),
            1,
        )
        row.addWidget(
            _DetailTile(
                "תנועות הרכב",
                "מה נספר, מה הוחרג ומה ממתין לבדיקה",
                self._open_car_movements_dialog,
                root,
            ),
            1,
        )
        lay.addLayout(row, 0)
        lay.addStretch(1)

    def _build_car_value_panel(self, parent, current, initial):
        panel = QWidget(parent)
        panel.setObjectName("ContentPanel")
        try:
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 20, 22, 20)
        pl.setSpacing(14)
        title = QLabel("שווי הרכב", panel)
        title.setObjectName("PanelTitle")
        pl.addWidget(title)

        has_initial = initial > 0
        retained = max(0.0, min(1.0, (current / initial) if has_initial else 1.0))
        loss = max(0.0, initial - current) if has_initial else 0.0
        pct_txt = (
            f"  <span style='font-size:14px;font-weight:800;color:#2f9e68;'>"
            f"{retained * 100:.0f}% מהמחיר המקורי</span>"
            if has_initial
            else ""
        )
        big = QLabel(f"{_fmt_money(current)} ₪{pct_txt}", panel)
        big.setStyleSheet("font-size:30px;font-weight:900;color:#1e1e22;")
        pl.addWidget(big)

        if has_initial:
            # EquityBar = green chunk over clay groove → reads as retained vs lost.
            bar = QProgressBar(panel)
            bar.setObjectName("EquityBar")
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            try:
                bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                bar.setFixedHeight(16)
            except QT_ERRORS:
                pass
            bar.setValue(int(round(retained * 100)))
            pl.addWidget(bar)
            pl.addWidget(self._legend_row(panel, "#2f9e68", "שווי נוכחי", current))
            pl.addWidget(self._legend_row(panel, "#d66a4e", "ירידת ערך", loss))
            pl.addWidget(self._legend_row(panel, "#e6e2d4", "מחיר קנייה", initial))
        return panel

    def _car_stat_card(self, parent, label, value_txt, per, foot, tone):
        card = QWidget(parent)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        if tone == "green":
            bg, lbl_c, num_c, dot, foot_c = "#eaf5ef", "#5b7a68", "#2f9e68", "#2f9e68", "#5b7a68"
        else:
            bg, lbl_c, num_c, dot, foot_c = "#faf1d4", "#7a6420", "#2c2612", "#d9b64a", "#8a7c52"
        card.setStyleSheet("QWidget{background:%s;border-radius:20px;}" % bg)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(6)
        lrow = QHBoxLayout()
        lrow.setSpacing(7)
        d = QLabel(card)
        d.setFixedSize(8, 8)
        d.setStyleSheet(f"background:{dot};border-radius:4px;")
        ll = QLabel(str(label), card)
        ll.setStyleSheet(
            f"font-size:13px;font-weight:700;color:{lbl_c};background:transparent;"
        )
        lrow.addWidget(d, 0, Qt.AlignmentFlag.AlignVCenter)
        lrow.addWidget(ll, 0)
        lrow.addStretch(1)
        cl.addLayout(lrow)
        v = QLabel(
            f"{value_txt} ₪  "
            f"<span style='font-size:14px;font-weight:700;'>{per}</span>",
            card,
        )
        v.setStyleSheet(
            f"font-size:30px;font-weight:900;color:{num_c};background:transparent;"
        )
        cl.addWidget(v)
        f = QLabel(str(foot), card)
        f.setStyleSheet(f"font-size:12px;color:{foot_c};background:transparent;")
        cl.addWidget(f)
        return card

    def _build_car_expenses_stats(self, parent, a):
        wrap = QWidget(parent)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(12)

        # Monthly = the car-category spend EXCLUDING the yearly items (so they're
        # not double-counted), PLUS the yearly items amortized (÷12). The yearly
        # items are the ones defined on the car's עלויות שנתיות manager.
        m = getattr(a, "record", None)
        _cx = self._expenses.car_expenses(m) if m is not None else None
        _bd = self._expenses.car_breakdown(m) if m is not None else None
        avg_month = _cx.monthly if _cx else 0.0
        avg_year = _cx.yearly if _cx else 0.0
        # yearly items = the part of the annual figure above the annualized monthly
        yearly_total = (avg_year - avg_month * 12.0) if _cx else 0.0
        has_data = bool(_cx) and (_cx.months_of_data > 0 or yearly_total > 0)
        trow = QHBoxLayout()
        trow.setContentsMargins(4, 2, 4, 0)
        t = QLabel("הוצאות הרכב", wrap)
        t.setStyleSheet("font-size:16px;font-weight:800;color:#1e1e22;background:transparent;")
        label = a.expense_category  # the selected categories, short
        note_text = (
            (f"{label} (חודשי)" + (" + עלויות שנתיות" if yearly_total > 0 else ""))
            if has_data
            else f"אין תנועות בקטגוריות: {label}"
        )
        if _bd is not None and _bd.review:
            names = ", ".join(f"״{n}״" for n in _bd.selection.review)
            note_text += f"  ·  {len(_bd.review)} תנועות ב{names} ממתינות לבדיקה"
        note = QLabel(note_text, wrap)
        note.setToolTip(
            "נספרות רק הקטגוריות שנבחרו לרכב (פרטי הרכב והמחיר). "
            "תחבורה ציבורית, מוניות והשכרת רכב לא נספרות אלא אם נבחרו."
        )
        note.setStyleSheet("font-size:12.5px;color:#a8aca1;background:transparent;")
        trow.addWidget(t, 0)
        trow.addStretch(1)
        trow.addWidget(note, 0)
        wl.addLayout(trow)

        monthly_txt = _fmt_money(avg_month) if has_data else "—"
        yearly_txt = _fmt_money(avg_year) if has_data else "—"
        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(
            self._car_stat_card(
                wrap, "ממוצע חודשי", monthly_txt, "/ חודש",
                "מה שהרכב עולה בממוצע בכל חודש", "green",
            ),
            1,
        )
        cards.addWidget(
            self._car_stat_card(
                wrap, "ממוצע שנתי", yearly_txt, "/ שנה",
                "סך ההוצאה השנתית הצפויה", "yellow",
            ),
            1,
        )
        wl.addLayout(cards)
        return wrap

    def _car_persist(self, updated):
        self._service.upsert_mortgage(updated)
        self.on_route_activated()
        self._refresh_yearly_dialog()

    def _open_update_value_dialog(self):
        m = self._selected_asset()
        if m is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("עדכון שווי הרכב")
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dlg.setModal(True)
        except QT_ERRORS:
            pass
        root = QVBoxLayout(dlg)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)
        info = QLabel(
            "אין מקור אוטומטי אמין לשווי רכב. הזן את השווי הנוכחי ידנית, או בדוק "
            "במחירון העם ואז הזן את המספר.",
            dlg,
        )
        info.setWordWrap(True)
        root.addWidget(info)
        val = self._labeled_edit(
            dlg, root, "שווי נוכחי (₪)", f"{float(m.current_value or 0.0):.0f}"
        )
        open_btn = QPushButton("בדוק במחירון העם ↗", dlg)
        open_btn.setObjectName("SecondaryButton")

        def _open_site():
            try:
                import webbrowser
                webbrowser.open("https://carlistprice.mot.gov.il/")
            except QT_ERRORS:
                pass

        open_btn.clicked.connect(_open_site)
        root.addWidget(open_btn)
        btns = QHBoxLayout()
        btns.addStretch(1)
        save = QPushButton("שמור", dlg)
        save.setObjectName("PrimaryButton")
        cancel = QPushButton("בטל", dlg)
        btns.addWidget(save)
        btns.addWidget(cancel)
        root.addLayout(btns)
        cancel.clicked.connect(dlg.reject)

        def _save():
            v = _parse_float(val.text())
            if v is None or v < 0:
                QMessageBox.warning(dlg, "שגיאה", "הזן שווי תקין")
                return
            self._car_persist(replace(m, current_value=float(v)))
            dlg.accept()

        save.clicked.connect(_save)
        dlg.exec()

    def _open_car_details_dialog(self):
        m = self._selected_asset()
        if m is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("פרטי הרכב")
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dlg.setModal(True)
        except QT_ERRORS:
            pass
        root = QVBoxLayout(dlg)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)
        name = self._labeled_edit(dlg, root, "שם הרכב", m.name or "")
        price = self._labeled_edit(
            dlg, root, "מחיר קנייה (₪)", f"{float(m.property_price or 0.0):.0f}"
        )
        date = self._labeled_date(dlg, root, "תאריך קנייה", m.start_date or "")
        # הקטגוריות שנספרות כעלויות אחזקת הרכב — רק מה שמסומן (בלי כל תתי־הקטגוריות
        # של "רכב ותחבורה" אוטומטית). שני רכבים? סמנו לכל אחד קטגוריות משלו.
        from ..models.car_costs import car_category_selection
        from ..models.category_tree import active_tree

        tree = active_tree()
        sel = car_category_selection(m, tree)
        root.addWidget(QLabel("קטגוריות שנספרות כעלויות הרכב", dlg))
        hint = QLabel(
            "סימון קטגוריה ראשית סופר רק תנועות שסווגו לקטגוריה הראשית עצמה. "
            "תחבורה ציבורית, מוניות והשכרת רכב אינן עלויות אחזקה ולכן לא מסומנות.",
            dlg,
        )
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        root.addWidget(hint)
        if sel.review:
            review_note = QLabel(
                "מההגדרה הקודמת: "
                + ", ".join(f"״{n}״" for n in sel.review)
                + " — קטגוריה רחבה, ולכן לא נספרת עד שתסמנו אותה. "
                "אפשר לבדוק את התנועות שלה ב״תנועות הרכב״.",
                dlg,
            )
            review_note.setObjectName("Subtitle")
            review_note.setWordWrap(True)
            root.addWidget(review_note)
        cat = CategoryChecklist(
            dlg,
            tree=tree,
            extra_names=list(sel.review),
            checked=list(sel.categories),
            expanded=list(sel.review),
        )
        cat.setMinimumHeight(240)
        root.addWidget(cat, 1)
        # Word-wrapped hints make the natural height too small; keep room for
        # the checklist so it never slides under the buttons.
        dlg.setMinimumSize(500, 760 if sel.review else 700)
        initial_checked = sorted(cat.checked_names())
        btns = QHBoxLayout()
        btns.addStretch(1)
        save = QPushButton("שמור", dlg)
        save.setObjectName("PrimaryButton")
        cancel = QPushButton("בטל", dlg)
        btns.addWidget(save)
        btns.addWidget(cancel)
        root.addLayout(btns)
        cancel.clicked.connect(dlg.reject)

        def _save():
            nm = str(name.text() or "").strip() or m.name
            p = _parse_float(price.text()) or 0.0
            try:
                purchase = date.date().toString("yyyy-MM-dd")
            except QT_ERRORS:
                purchase = m.start_date
            updated = replace(m, name=nm, property_price=float(p), start_date=purchase)
            checked = cat.checked_names()
            # Only an actual change of the checkboxes is saved — saving the
            # other fields never freezes a converted older setting by itself
            # (which would silently drop its "for review" category).
            if sorted(checked) != initial_checked:
                updated = replace(updated, expense_categories=list(checked))
            if updated != m:
                self._car_persist(updated)
            dlg.accept()

        save.clicked.connect(_save)
        dlg.exec()

    def _open_car_movements_dialog(self):
        """Every movement behind the car's figures: counted in the monthly
        spend, excluded by the user, counted by a yearly item, or waiting for
        review (a broad category from the older setting). Exclusions are saved
        on the car; categories are never changed here."""
        m = self._selected_asset()
        if m is None:
            return
        bd = self._expenses.car_breakdown(m)
        locked = {str(mv.id): "בעלות שנתית" for mv in bd.cost_items}
        locked.update({str(mv.id): "לבדיקה · לא נספר" for mv in bd.review})
        by_cat = "  ·  ".join(
            f"{c} {_fmt_money(total)} ₪" for c, total, _n in bd.monthly_by_category()[:6]
        )
        subtitle = f"קטגוריות: {selection_label(bd.selection, limit=8)}"
        if by_cat:
            subtitle += f"\nסה״כ לפי קטגוריה (כל התקופה): {by_cat}"
        pseudo = CostItem(
            name="הוצאות הרכב",
            excluded_movement_ids=[str(x) for x in (m.excluded_movement_ids or [])],
        )
        dlg = CostMovementsDialog(
            cost=pseudo,
            movements=[],
            candidates=bd.monthly + bd.excluded + bd.cost_items + bd.review,
            subtitle=subtitle,
            locked=locked,
            show_category=True,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_ex = list(dlg.get_cost().excluded_movement_ids)
        if sorted(new_ex) != sorted(str(x) for x in (m.excluded_movement_ids or [])):
            self._car_persist(replace(m, excluded_movement_ids=new_ex))

    def _open_yearly_costs_dialog(self):
        m = self._selected_asset()
        if m is None:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("עלויות שנתיות")
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dlg.resize(760, 520)
        except QT_ERRORS:
            pass
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 16, 16, 16)
        host = QWidget(dlg)
        self._yearly_host = host
        hl = QVBoxLayout(host)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self._build_yearly_panel(host, m))
        outer.addWidget(host)
        try:
            dlg.exec()
        finally:
            self._yearly_host = None

    def _cost_cycle_cell(self, cost, movements, which):
        """Text for a cost's cycle: 'yy/yy: amount' (which=0 current, 1 prev)."""
        cycles = yearly_cost_cycles(cost, movements, n_cycles=2)
        if which >= len(cycles):
            return "—"
        year, total = cycles[which]
        rm = int(getattr(cost, "renewal_month", 0) or 0)
        if 1 < rm <= 12:
            short = f"{str(year)[2:]}/{str(year + 1)[2:]}"
        else:
            short = str(year)
        return f"{short}:  {_fmt_money(total)} ₪"

    def _build_yearly_panel(self, parent, m):
        self._yearly_costs = list(m.yearly_costs)
        card, table = self._panel_with_actions(
            "עלויות שנתיות (ביטוח, טסט, אגרה) — לפי מחזור חידוש",
            self._on_add_yearly_cost,
            self._on_edit_yearly_cost,
            self._on_remove_yearly_cost,
            self._on_yearly_cost_movements,
        )
        self._yearly_table = table
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(
            ["רכיב", "חודש חידוש", "המחזור הנוכחי", "המחזור הקודם"]
        )
        table.doubleClicked.connect(self._on_yearly_cost_movements)
        movements = self._service.list_movements()
        costs = self._yearly_costs
        table.setRowCount(len(costs))
        for i, c in enumerate(costs):
            rm = int(getattr(c, "renewal_month", 0) or 0)
            month_txt = _MONTH_NAMES[rm - 1] if 1 <= rm <= 12 else "—"
            table.setItem(i, 0, QTableWidgetItem(str(c.name)))
            table.setItem(i, 1, QTableWidgetItem(month_txt))
            table.setItem(i, 2, QTableWidgetItem(self._cost_cycle_cell(c, movements, 0)))
            table.setItem(i, 3, QTableWidgetItem(self._cost_cycle_cell(c, movements, 1)))
        return card

    def _refresh_yearly_dialog(self):
        host = getattr(self, "_yearly_host", None)
        if host is None:
            return
        m = self._selected_asset()
        if m is None:
            return
        lay = host.layout()
        if lay is None:
            return
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        lay.addWidget(self._build_yearly_panel(host, m))

    def _selected_yearly_index(self):
        t = self._yearly_table
        if t is None:
            return -1
        r = t.currentRow()
        return r if 0 <= r < len(self._yearly_costs) else -1

    def _save_yearly(self, costs):
        m = self._selected_asset()
        if m is None:
            return
        self._service.upsert_mortgage(replace(m, yearly_costs=list(costs)))
        self.on_route_activated()
        self._refresh_yearly_dialog()
        # When reached from the house "הוצאות הבית" dialog (not the standalone
        # yearly dialog), refresh that combined panel too.
        self._refresh_details_dialog()

    def _on_add_yearly_cost(self):
        m = self._selected_asset()
        if m is None:
            return
        dlg = CostItemDialog(show_query=True, show_renewal=True, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cost = dlg.get_cost()
        if cost is not None:
            self._save_yearly(list(m.yearly_costs) + [cost])

    def _on_edit_yearly_cost(self):
        m = self._selected_asset()
        if m is None:
            return
        idx = self._selected_yearly_index()
        if idx < 0:
            QMessageBox.information(self, "עריכה", "בחר פריט")
            return
        dlg = CostItemDialog(cost=m.yearly_costs[idx], show_query=True, show_renewal=True, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cost = dlg.get_cost()
        if cost is not None:
            costs = list(m.yearly_costs)
            costs[idx] = cost
            self._save_yearly(costs)

    @staticmethod
    def _query_cell(cost, movements) -> str:
        """'ועד בית · 10 תנועות' — the search text and how many movements count."""
        query = str(getattr(cost, "query", "") or "").strip()
        if not query:
            return "—"
        n = len(cost_matched_movements(cost, movements))
        n_ex = len(getattr(cost, "excluded_movement_ids", None) or [])
        txt = f"{query} · {n} תנועות"
        return f"{txt} ({n_ex} הוחרגו)" if n_ex else txt

    def _open_cost_movements(self, cost, *, yearly: bool):
        """Show ``cost``'s matched movements; return the cost with the user's
        exclusions, or None if cancelled / nothing to show."""
        if not str(getattr(cost, "query", "") or "").strip():
            QMessageBox.information(
                self,
                "תנועות",
                "לפריט הזה אין חיפוש תנועות. ערוך אותו (✎) והוסף מילים מתיאור התנועה בבנק.",
            )
            return None
        dlg = CostMovementsDialog(
            cost=cost,
            movements=self._service.list_movements(),
            yearly=yearly,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        updated = dlg.get_cost()
        if list(updated.excluded_movement_ids) == list(cost.excluded_movement_ids):
            return None
        return updated

    def _on_yearly_cost_movements(self, *_args):
        m = self._selected_asset()
        if m is None:
            return
        idx = self._selected_yearly_index()
        if idx < 0:
            QMessageBox.information(self, "תנועות", "בחר פריט")
            return
        updated = self._open_cost_movements(m.yearly_costs[idx], yearly=True)
        if updated is not None:
            costs = list(m.yearly_costs)
            costs[idx] = updated
            self._save_yearly(costs)

    def _on_remove_yearly_cost(self):
        m = self._selected_asset()
        if m is None:
            return
        idx = self._selected_yearly_index()
        if idx < 0:
            QMessageBox.information(self, "מחיקה", "בחר פריט")
            return
        costs = list(m.yearly_costs)
        del costs[idx]
        self._save_yearly(costs)

    # ------------------------------------------------------------- overview
    def _build_equity_panel(
        self,
        parent,
        value,
        outstanding,
        equity,
        eq_frac,
        *,
        title_text="הון עצמי בנכס",
        debt_label="יתרת חוב",
        value_label="שווי הנכס",
    ):
        panel = QWidget(parent)
        panel.setObjectName("ContentPanel")
        try:
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 20, 22, 20)
        pl.setSpacing(14)
        title = QLabel(title_text, panel)
        title.setObjectName("PanelTitle")
        pl.addWidget(title)
        big = QLabel(
            f"{_fmt_money(equity)} ₪  "
            f"<span style='font-size:14px;font-weight:800;color:#2f9e68;'>"
            f"{eq_frac * 100:.1f}% מהשווי</span>",
            panel,
        )
        big.setStyleSheet("font-size:30px;font-weight:900;color:#1e1e22;")
        pl.addWidget(big)
        bar = QProgressBar(panel)
        bar.setObjectName("EquityBar")
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        try:
            bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            bar.setFixedHeight(16)
        except QT_ERRORS:
            pass
        bar.setValue(int(round(max(0.0, min(1.0, eq_frac)) * 100)))
        pl.addWidget(bar)
        pl.addWidget(self._legend_row(panel, "#2f9e68", "הון עצמי", equity))
        pl.addWidget(self._legend_row(panel, "#d66a4e", debt_label, outstanding))
        pl.addWidget(self._legend_row(panel, "#e6e2d4", value_label, value))
        return panel

    def _legend_row(self, parent, color, name, amount):
        row = QWidget(parent)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(9)
        sw = QLabel(row)
        sw.setFixedSize(11, 11)
        sw.setStyleSheet(f"background:{color};border-radius:3px;")
        nm = QLabel(str(name), row)
        nm.setStyleSheet("font-size:13.5px;color:#6b6f66;")
        val = QLabel(f"{_fmt_money(amount)} ₪", row)
        val.setStyleSheet("font-size:13.5px;font-weight:800;color:#1e1e22;")
        rl.addWidget(sw, 0)
        rl.addWidget(nm, 0)
        rl.addStretch(1)
        rl.addWidget(val, 0)
        return row

    def _mini_stat(self, parent, key, value, sub=None, green=False):
        frame = QFrame(parent)
        frame.setStyleSheet(
            "QFrame{background:#faf9f4;border:1px solid #ecece2;"
            "border-radius:14px;}"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(14, 12, 14, 12)
        fl.setSpacing(3)
        k = QLabel(str(key), frame)
        k.setStyleSheet("font-size:12px;color:#6b6f66;font-weight:600;")
        v = QLabel(str(value), frame)
        vcolor = "#2f9e68" if green else "#1e1e22"
        v.setStyleSheet(f"font-size:19px;font-weight:900;color:{vcolor};")
        fl.addWidget(k)
        fl.addWidget(v)
        if sub:
            sb = QLabel(str(sub), frame)
            sb.setStyleSheet("font-size:11px;color:#a8aca1;")
            fl.addWidget(sb)
        return frame

    def _build_status_panel(self, parent, st, *, title_text="מצב המשכנתא"):
        panel = QWidget(parent)
        panel.setObjectName("ContentPanel")
        try:
            panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(22, 20, 22, 20)
        pl.setSpacing(14)
        title = QLabel(title_text, panel)
        title.setObjectName("PanelTitle")
        pl.addWidget(title)

        mini = QHBoxLayout()
        mini.setSpacing(10)
        mini.addWidget(
            self._mini_stat(
                panel,
                "נותר לתשלום",
                f"{_fmt_money(st.remaining_total)} ₪",
                sub="כולל ריבית",
                green=True,
            ),
            1,
        )
        pay_sub = None
        if st.dated and st.monthly_now > 0:
            pay_sub = (
                f"ריבית {_fmt_money(st.interest_now)} ₪ · "
                f"קרן {_fmt_money(st.principal_now)} ₪"
            )
        mini.addWidget(
            self._mini_stat(
                panel, "תשלום חודשי", f"{_fmt_money(st.monthly_now)} ₪", sub=pay_sub
            ),
            1,
        )
        pl.addLayout(mini)

        bar = QProgressBar(panel)
        bar.setObjectName("AssetProgress")
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        lbl = QLabel("", panel)
        lbl.setObjectName("AssetCaption")
        lbl.setWordWrap(True)
        if st.dated:
            pct = int(round(st.pct_paid * 100))
            bar.setValue(pct)
            payoff = (
                f" · סיום {st.payoff_month:02d}/{st.payoff_year}"
                if st.payoff_year
                else ""
            )
            lbl.setText(
                f"שולם {pct}% מהקרן · נותרו {st.remaining_payments} "
                f"תשלומים{payoff}"
            )
        else:
            bar.setValue(0)
            lbl.setText("טרם הוגדר תאריך התחלה — לא ניתן לחשב התקדמות")
        pl.addWidget(bar)
        pl.addWidget(lbl)
        pl.addStretch(1)
        return panel

    def _build_allin_strip(self, parent, m, s):
        # Same look as the car expenses section: a title + two pastel stat cards
        # (green monthly, yellow yearly). Total = mortgage payment + הוצאות הבית;
        # yearly = ×12. Nothing else is included.
        _ai = self._expenses.house_all_in(m)
        house_month = _ai.house_monthly
        mortgage_month = _ai.mortgage_monthly
        total_month = _ai.total_monthly
        total_year = _ai.total_yearly

        wrap = QWidget(parent)
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(12)
        trow = QHBoxLayout()
        trow.setContentsMargins(4, 2, 4, 0)
        t = QLabel("הוצאות על הבית", wrap)
        t.setStyleSheet(
            "font-size:16px;font-weight:800;color:#1e1e22;background:transparent;"
        )
        note = QLabel(
            f"משכנתא {_fmt_money(mortgage_month)} ₪ + "
            f"הוצאות הבית {_fmt_money(house_month)} ₪",
            wrap,
        )
        note.setStyleSheet("font-size:12.5px;color:#a8aca1;background:transparent;")
        trow.addWidget(t, 0)
        trow.addStretch(1)
        trow.addWidget(note, 0)
        wl.addLayout(trow)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(
            self._car_stat_card(
                wrap, "הוצאה חודשית", _fmt_money(total_month), "/ חודש",
                "משכנתא + הוצאות הבית", "green",
            ),
            1,
        )
        cards.addWidget(
            self._car_stat_card(
                wrap, "הוצאה שנתית", _fmt_money(total_year), "/ שנה",
                "סך ההוצאה השנתית על הבית", "yellow",
            ),
            1,
        )
        wl.addLayout(cards)
        return wrap

    # -------------------------------------------------------- detail dialogs
    def _open_details_dialog(self, initial_tab):
        m = self._selected_asset()
        if m is None:
            return
        self._active_tab = initial_tab
        titles = {
            "expenses": "עלויות רכישה",
            "income": "מקורות מימון",
            "monthly": "עלויות חודשיות",
            "house_costs": "הוצאות הבית — חודשי ושנתי",
        }
        dlg = QDialog(self)
        dlg.setWindowTitle(titles.get(initial_tab, "פרטי הנכס"))
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            dlg.resize(840, 620)
        except QT_ERRORS:
            pass
        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(16, 16, 16, 16)
        host = QWidget(dlg)
        self._details_host = host
        hl = QVBoxLayout(host)
        hl.setContentsMargins(0, 0, 0, 0)
        s = self._service.purchase_summary(m)
        hl.addWidget(self._build_details_widget(host, m, s))
        outer.addWidget(host)
        self._details_dialog = dlg
        try:
            dlg.exec()
        finally:
            self._details_dialog = None
            self._details_host = None

    def _refresh_details_dialog(self):
        host = getattr(self, "_details_host", None)
        if host is None:
            return
        m = self._selected_asset()
        if m is None:
            return
        lay = host.layout()
        if lay is None:
            return
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        s = self._service.purchase_summary(m)
        lay.addWidget(self._build_details_widget(host, m, s))

    def _after_change(self):
        # Refresh the overview numbers, then the open detail dialog (if any).
        self.on_route_activated()
        self._refresh_details_dialog()

    def _panel_with_actions(
        self, title_text, on_add, on_edit, on_remove, on_movements=None
    ) -> tuple[QWidget, QTableWidget]:
        """כרטיס עם כותרת + כפתורי הוסף/ערוך/מחק + טבלה — להוספה אחידה."""
        card = QWidget(self)
        card.setObjectName("AssetTablePanel")
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except QT_ERRORS:
            pass
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(QLabel(title_text, card), 0)
        header.addStretch(1)
        add_b = QToolButton(card)
        add_b.setText("➕")
        add_b.setToolTip("הוסף")
        add_b.clicked.connect(on_add)
        edit_b = QToolButton(card)
        edit_b.setText("✎")
        edit_b.setToolTip("ערוך")
        edit_b.clicked.connect(on_edit)
        rm_b = QToolButton(card)
        rm_b.setText("🗑")
        rm_b.setToolTip("מחק")
        rm_b.clicked.connect(on_remove)
        if on_movements is not None:
            mv_b = QToolButton(card)
            mv_b.setText("🔍")
            mv_b.setToolTip("התנועות שנמצאו (אפשר להחריג)")
            mv_b.clicked.connect(on_movements)
            header.addWidget(mv_b)
        header.addWidget(add_b)
        header.addWidget(edit_b)
        header.addWidget(rm_b)
        cl.addLayout(header)
        table = QTableWidget(card)
        table.setObjectName("ActionHistoryTableWidget")
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(False)
        try:
            table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh.setObjectName("ActionHistoryHeader")
        except QT_ERRORS:
            pass
        cl.addWidget(table, 1)
        return card, table

    # ───────── ניהול הוצאות (עלויות חד-פעמיות) ─────────

    def _selected_cost_index(self) -> int:
        """אינדקס שורת העלות הנבחרת (שורה 0 = מחיר הדירה, לכן −1)."""
        if self._expense_table is None:
            return -1
        row = self._expense_table.currentRow()
        idx = row - 1
        return idx if 0 <= idx < len(self._one_time_costs) else -1

    def _save_costs(self, costs: List[CostItem]) -> None:
        m = self._selected_asset()
        if m is None:
            return
        self._service.upsert_mortgage(replace(m, one_time_costs=list(costs)))
        self._after_change()

    def _on_add_cost(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        dlg = CostItemDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cost = dlg.get_cost()
        if cost is not None:
            self._save_costs(list(m.one_time_costs) + [cost])

    def _on_edit_cost(self) -> None:
        idx = self._selected_cost_index()
        if idx < 0:
            QMessageBox.information(self, "הוצאה", "בחר הוצאה לעריכה")
            return
        dlg = CostItemDialog(cost=self._one_time_costs[idx], parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_cost()
        if updated is None:
            return
        costs = list(self._one_time_costs)
        costs[idx] = updated
        self._save_costs(costs)

    def _on_remove_cost(self) -> None:
        idx = self._selected_cost_index()
        if idx < 0:
            QMessageBox.information(self, "הוצאה", "בחר הוצאה למחיקה")
            return
        costs = list(self._one_time_costs)
        del costs[idx]
        self._save_costs(costs)

    # ───────── ניהול עלויות חודשיות ─────────

    def _selected_monthly_index(self) -> int:
        if self._monthly_table is None:
            return -1
        row = self._monthly_table.currentRow()
        return row if 0 <= row < len(self._monthly_costs) else -1

    def _save_monthly(self, costs: List[CostItem]) -> None:
        m = self._selected_asset()
        if m is None:
            return
        self._service.upsert_mortgage(replace(m, monthly_costs=list(costs)))
        self._after_change()

    def _on_add_monthly_cost(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        dlg = CostItemDialog(show_query=True, show_amount=False, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        cost = dlg.get_cost()
        if cost is not None:
            self._save_monthly(list(m.monthly_costs) + [cost])

    def _on_edit_monthly_cost(self) -> None:
        idx = self._selected_monthly_index()
        if idx < 0:
            QMessageBox.information(self, "עלות חודשית", "בחר עלות לעריכה")
            return
        dlg = CostItemDialog(
            cost=self._monthly_costs[idx],
            show_query=True,
            show_amount=False,
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_cost()
        if updated is None:
            return
        costs = list(self._monthly_costs)
        costs[idx] = updated
        self._save_monthly(costs)

    def _on_monthly_cost_movements(self, *_args) -> None:
        idx = self._selected_monthly_index()
        if idx < 0:
            QMessageBox.information(self, "עלות חודשית", "בחר עלות")
            return
        updated = self._open_cost_movements(self._monthly_costs[idx], yearly=False)
        if updated is not None:
            costs = list(self._monthly_costs)
            costs[idx] = updated
            self._save_monthly(costs)

    def _on_remove_monthly_cost(self) -> None:
        idx = self._selected_monthly_index()
        if idx < 0:
            QMessageBox.information(self, "עלות חודשית", "בחר עלות למחיקה")
            return
        costs = list(self._monthly_costs)
        del costs[idx]
        self._save_monthly(costs)

    # ───────── ניהול מקורות מימון ─────────

    def _selected_funding(self) -> Optional[FundingSource]:
        if self._funding_table is None:
            return None
        row = self._funding_table.currentRow()
        if 0 <= row < len(self._funding_sources):
            return self._funding_sources[row]
        return None

    def _save_funding(self, sources: List[FundingSource]) -> None:
        m = self._selected_asset()
        if m is None:
            return
        self._service.upsert_mortgage(replace(m, funding_sources=list(sources)))
        self._after_change()

    def _on_add_funding(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        dlg = FundingSourceDialog(accounts=self._load_accounts(), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        src = dlg.get_source()
        if src is not None:
            self._save_funding(list(m.funding_sources) + [src])

    def _on_edit_funding(self) -> None:
        sel = self._selected_funding()
        if sel is None:
            QMessageBox.information(self, "מקור מימון", "בחר מקור מימון לעריכה")
            return
        row = self._funding_table.currentRow() if self._funding_table else -1
        dlg = FundingSourceDialog(
            accounts=self._load_accounts(), source=sel, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_source()
        if updated is None:
            return
        sources = list(self._funding_sources)
        if 0 <= row < len(sources):
            sources[row] = updated
            self._save_funding(sources)

    def _on_remove_funding(self) -> None:
        row = self._funding_table.currentRow() if self._funding_table else -1
        if not (0 <= row < len(self._funding_sources)):
            QMessageBox.information(self, "מקור מימון", "בחר מקור מימון למחיקה")
            return
        sources = list(self._funding_sources)
        del sources[row]
        self._save_funding(sources)

    def _open_mortgage(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        try:
            if isinstance(self._app_context, dict):
                self._app_context["selected_mortgage_id"] = str(m.id)
        except QT_ERRORS:
            pass
        if self._navigate is not None:
            self._navigate("mortgage")

    def _on_edit_purchase(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        if not isinstance(build_asset(m), HousePurchase):
            return
        HousePurchaseDialog(
            service=self._service, mortgage_id=m.id, parent=self
        ).exec()
        self.on_route_activated()
