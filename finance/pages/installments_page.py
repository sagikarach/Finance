from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QDialog,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QSpinBox,
    QCheckBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QSizePolicy,
    Qt,
    QDate,
    QColor,
)
from ..models.accounts import BankAccount, BudgetAccount, MoneyAccount, parse_iso_date
from ..utils.formatting import format_currency
from ..ui.dialog_utils import setup_calendar_popup
from ..models.installment_plan import (
    KIND_DIRECT_DEBIT,
    KIND_INSTALLMENTS,
    InstallmentPlan,
    normalize_plan_kind,
)
from ..models.installments_service import InstallmentsService
from ..widgets.installments_selector import InstallmentsSelector
from ..widgets.category_combo import CategoryComboBox, category_value, fill_category_combo
from .base_page import BasePage


from ..utils.formatting import fmt_money
from ..utils.safe import QT_ERRORS


def _fmt_money(value: float) -> str:
    return fmt_money(value, 2)


class InstallmentPlanDialog(QDialog):
    """Create/edit a payments plan: an installment plan (tracked by matching
    bank movements) or a direct debit — הוראת קבע — with a fixed monthly
    amount charged on the same day for a set number of months."""

    def __init__(
        self,
        *,
        accounts: List[MoneyAccount],
        plan: Optional[InstallmentPlan] = None,
        kind: str = KIND_INSTALLMENTS,
        categories: Optional[List[str]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("תכנית תשלומים")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except QT_ERRORS:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass

        self._plan: Optional[InstallmentPlan] = plan
        self._accounts = accounts
        initial_kind = normalize_plan_kind(plan.kind if plan is not None else kind)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        self._title = QLabel("", self)
        self._title.setObjectName("HeaderTitle")
        root.addWidget(self._title)

        self._kind = QComboBox(self)
        self._kind.addItem("תכנית תשלומים", KIND_INSTALLMENTS)
        self._kind.addItem("הוראת קבע", KIND_DIRECT_DEBIT)
        root.addWidget(QLabel("סוג", self))
        root.addWidget(self._kind)

        self._name = QLineEdit(self)
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        # Installment plan only: payments are found by vendor text.
        self._vendor_query = QLineEdit(self)
        self._vendor_query.setPlaceholderText("חיפוש ספק (מופיע בתיאור התנועה)")
        self._vendor_label = QLabel("חיפוש ספק", self)
        root.addWidget(self._vendor_label)
        root.addWidget(self._vendor_query)

        self._account = QComboBox(self)
        self._account.setEditable(False)
        # A direct debit always comes from the bank, so its dialog hides this
        # field and saves the bank account (named "בנק", else the first bank).
        all_names: List[str] = []
        bank_names: List[str] = []
        for a in accounts:
            try:
                if isinstance(a, (BankAccount, BudgetAccount)) and bool(
                    getattr(a, "active", False)
                ):
                    name = str(getattr(a, "name", "") or "").strip()
                    if name:
                        all_names.append(name)
                        if isinstance(a, BankAccount):
                            bank_names.append(name)
            except QT_ERRORS:
                continue
        self._account.addItems(sorted(set(all_names)))
        banks = sorted(set(bank_names))
        self._debit_account_name = "בנק" if "בנק" in banks else (banks[0] if banks else "")
        self._account_label = QLabel("חשבון מקור", self)
        root.addWidget(self._account_label)
        root.addWidget(self._account)

        self._start_date = QDateEdit(self)
        self._start_date.setCalendarPopup(True)
        setup_calendar_popup(self._start_date)
        try:
            self._start_date.setDisplayFormat("yyyy-MM-dd")
        except QT_ERRORS:
            pass
        self._start_label = QLabel("תאריך התחלה", self)
        root.addWidget(self._start_label)
        root.addWidget(self._start_date)

        # Direct debit only: the fixed monthly charge and its day of month.
        self._monthly_amount = QLineEdit(self)
        self._monthly_amount.setPlaceholderText("סכום כל חיוב (לדוגמה: 250)")
        self._monthly_label = QLabel("סכום חודשי", self)
        root.addWidget(self._monthly_label)
        root.addWidget(self._monthly_amount)

        self._charge_day = QSpinBox(self)
        self._charge_day.setMinimum(1)
        self._charge_day.setMaximum(31)
        self._charge_day.setToolTip("בחודש קצר יותר החיוב יורד ביום האחרון של החודש")
        self._charge_day_label = QLabel("יום החיוב בחודש", self)
        root.addWidget(self._charge_day_label)
        root.addWidget(self._charge_day)

        self._payments_count = QSpinBox(self)
        self._payments_count.setMinimum(1)
        self._payments_count.setMaximum(240)
        self._count_label = QLabel("מספר תשלומים", self)
        root.addWidget(self._count_label)
        root.addWidget(self._payments_count)

        # Installment plan only: the total, typed by the user.
        self._original_amount = QLineEdit(self)
        self._original_amount.setPlaceholderText("סכום כולל (לדוגמה: 3500)")
        self._original_label = QLabel("סכום מקורי", self)
        root.addWidget(self._original_label)
        root.addWidget(self._original_amount)

        # Direct debit only: live total = monthly × months.
        self._total_hint = QLabel("", self)
        self._total_hint.setObjectName("Subtitle")
        root.addWidget(self._total_hint)

        # Direct debit only: post each charge as a real bank movement.
        self._auto_post = QCheckBox("צור תנועות בנק אוטומטית בכל חיוב", self)
        self._auto_post.setChecked(True)
        self._auto_post.setToolTip(
            "בתאריך כל חיוב תיווצר הוצאה בחשבון הבנק (כולל חיובים שכבר עברו)"
        )
        root.addWidget(self._auto_post)
        # Hierarchical picker (label = full path, data = the stored name).
        # Starts on "(ללא קטגוריה)" — no guess, the user picks.
        self._category_names = [str(c) for c in (categories or []) if str(c).strip()] or [
            "הוראת קבע"
        ]
        self._category = CategoryComboBox(self)
        fill_category_combo(self._category, self._category_names, "")
        self._category_label = QLabel("קטגוריה לתנועות", self)
        root.addWidget(self._category_label)
        root.addWidget(self._category)

        self._archived = QCheckBox("בארכיון", self)
        root.addWidget(self._archived)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self._save_btn = QPushButton("שמור", self)
        self._cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(self._save_btn)
        buttons.addWidget(self._cancel_btn)
        root.addLayout(buttons)

        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)

        self._load_initial()
        try:
            idx = self._kind.findData(initial_kind)
            self._kind.setCurrentIndex(max(0, idx))
        except QT_ERRORS:
            pass
        self._apply_kind()
        self._kind.currentIndexChanged.connect(lambda _i: self._apply_kind())
        self._monthly_amount.textChanged.connect(lambda _t: self._update_total_hint())
        self._auto_post.toggled.connect(lambda _c: self._apply_kind())
        self._payments_count.valueChanged.connect(lambda _v: self._update_total_hint())

    def _current_kind(self) -> str:
        try:
            return normalize_plan_kind(self._kind.currentData())
        except QT_ERRORS:
            return KIND_INSTALLMENTS

    def _apply_kind(self) -> None:
        dd = self._current_kind() == KIND_DIRECT_DEBIT
        try:
            self._title.setText("הוראת קבע" if dd else "תכנית תשלומים")
            self.setWindowTitle("הוראת קבע" if dd else "תכנית תשלומים")
            self._name.setPlaceholderText(
                "שם (לדוגמה: חוג שחייה)" if dd else "שם (לדוגמה: טלוויזיה)"
            )
            for w in (self._vendor_label, self._vendor_query,
                      self._original_label, self._original_amount):
                w.setVisible(not dd)
            for w in (self._monthly_label, self._monthly_amount,
                      self._charge_day_label, self._charge_day, self._total_hint,
                      self._auto_post):
                w.setVisible(dd)
            self._category_label.setVisible(dd and self._auto_post.isChecked())
            self._category.setVisible(dd and self._auto_post.isChecked())
            self._account_label.setVisible(not dd)
            self._account.setVisible(not dd)
            self._count_label.setText("מספר חודשים" if dd else "מספר תשלומים")
            self._start_label.setText("תאריך החיוב הראשון" if dd else "תאריך התחלה")
            self.adjustSize()
        except QT_ERRORS:
            pass
        self._update_total_hint()

    def _monthly_value(self) -> Optional[float]:
        try:
            return float(str(self._monthly_amount.text() or "").replace(",", "").strip())
        except (ValueError, TypeError):
            return None

    def _update_total_hint(self) -> None:
        monthly = self._monthly_value()
        try:
            if monthly is None or monthly <= 0:
                self._total_hint.setText("")
                return
            months = int(self._payments_count.value())
            self._total_hint.setText(
                f"סה״כ {format_currency(monthly * months)} · "
                f"{months} חיובים של {format_currency(monthly)}"
            )
        except QT_ERRORS:
            pass

    def _load_initial(self) -> None:
        p = self._plan
        if p is None:
            try:
                self._start_date.setDate(QDate.currentDate())
                self._charge_day.setValue(QDate.currentDate().day())
            except QT_ERRORS:
                pass
            self._payments_count.setValue(1)
            self._archived.setChecked(False)
            return
        self._name.setText(str(p.name or ""))
        self._vendor_query.setText(str(p.vendor_query or ""))
        if p.account_name:
            self._account.setCurrentText(str(p.account_name))
        try:
            dt = parse_iso_date(str(p.start_date or ""))
            self._start_date.setDate(QDate(dt.year, dt.month, dt.day))
        except QT_ERRORS:
            try:
                self._start_date.setDate(QDate.currentDate())
            except QT_ERRORS:
                pass
        self._payments_count.setValue(max(1, int(p.payments_count)))
        self._original_amount.setText(str(float(p.original_amount)))
        if float(p.monthly_amount or 0.0) > 0:
            self._monthly_amount.setText(f"{float(p.monthly_amount):g}")
        day = int(p.charge_day or 0)
        if not 1 <= day <= 31:
            try:
                day = self._start_date.date().day()
            except QT_ERRORS:
                day = 1
        self._charge_day.setValue(day)
        self._auto_post.setChecked(bool(getattr(p, "auto_post", True)))
        if str(p.category or "").strip():
            # The plan's own value is kept even when it is not in the list.
            fill_category_combo(self._category, self._category_names, str(p.category))
        self._archived.setChecked(bool(getattr(p, "archived", False)))

    def _on_save(self) -> None:
        kind = self._current_kind()
        dd = kind == KIND_DIRECT_DEBIT
        name = str(self._name.text() or "").strip()
        vendor_query = str(self._vendor_query.text() or "").strip()
        account_name = (
            self._debit_account_name
            if dd
            else str(self._account.currentText() or "").strip()
        )
        payments_count = int(self._payments_count.value())
        start_date = ""
        try:
            start_date = self._start_date.date().toString("yyyy-MM-dd")
        except QT_ERRORS:
            start_date = ""
        try:
            original_amount = float(
                str(self._original_amount.text() or "").strip() or 0.0
            )
        except (ValueError, TypeError):
            original_amount = 0.0
        archived = bool(self._archived.isChecked())
        monthly_amount = 0.0
        charge_day = 0

        if not name:
            QMessageBox.warning(self, "שגיאה", "שם לא יכול להיות ריק")
            return
        if not dd and not vendor_query:
            QMessageBox.warning(self, "שגיאה", "חיפוש ספק לא יכול להיות ריק")
            return
        if not account_name:
            QMessageBox.warning(
                self,
                "שגיאה",
                "צריך חשבון בנק פעיל כדי ליצור הוראת קבע" if dd else "צריך לבחור חשבון מקור",
            )
            return
        if payments_count <= 0:
            QMessageBox.warning(self, "שגיאה", "מספר תשלומים חייב להיות גדול מ-0")
            return
        if dd:
            monthly = self._monthly_value()
            if monthly is None or monthly <= 0:
                QMessageBox.warning(self, "שגיאה", "סכום חודשי חייב להיות מספר גדול מ-0")
                return
            monthly_amount = float(monthly)
            charge_day = int(self._charge_day.value())
            if self._auto_post.isChecked() and not category_value(self._category):
                QMessageBox.warning(self, "שגיאה", "צריך לבחור קטגוריה לתנועות הבנק")
                return
            # The total is derived, so the rest of the app (history, tiles)
            # can keep reading ``original_amount``.
            original_amount = round(monthly_amount * payments_count, 2)
        elif original_amount < 0:
            QMessageBox.warning(self, "שגיאה", "סכום מקורי לא יכול להיות שלילי")
            return

        prev = self._plan
        self._plan = InstallmentPlan(
            **({"id": prev.id} if prev is not None else {}),
            name=name,
            vendor_query=vendor_query,
            account_name=account_name,
            start_date=start_date,
            payments_count=payments_count,
            original_amount=float(original_amount),
            excluded_movement_ids=list(prev.excluded_movement_ids) if prev else [],
            archived=archived,
            kind=kind,
            monthly_amount=monthly_amount,
            charge_day=charge_day,
            auto_post=bool(self._auto_post.isChecked()) if dd else False,
            category=category_value(self._category) if dd else "",
            posted_count=int(prev.posted_count) if prev else 0,
        )
        self.accept()

    def get_plan(self) -> Optional[InstallmentPlan]:
        return self._plan


class InstallmentsPage(BasePage):
    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("page_title", "תשלומים")
        kwargs.setdefault("current_route", "installments")
        self._service = InstallmentsService()
        self._plans: List[InstallmentPlan] = []
        self._selected_plan_id: Optional[str] = None

        self._selector: Optional[InstallmentsSelector] = None
        self._edit_btn: Optional[QToolButton] = None
        self._table: Optional[QTableWidget] = None
        self._exclude_btn: Optional[QToolButton] = None
        self._card_original: Optional[QLabel] = None
        self._card_paid: Optional[QLabel] = None
        self._card_left: Optional[QLabel] = None
        self._card_overpaid: Optional[QLabel] = None
        self._card_titles: List[QLabel] = []
        self._table_title: Optional[QLabel] = None
        # hero + progress
        self._name_lbl: Optional[QLabel] = None
        self._acct_badge: Optional[QLabel] = None
        self._meta_lbl: Optional[QLabel] = None
        self._prog_wrap: Optional[QWidget] = None
        self._prog_lead: Optional[QLabel] = None
        self._prog_left: Optional[QLabel] = None
        self._prog_bar: Optional[QProgressBar] = None
        self._tick_first: Optional[QLabel] = None
        self._tick_last: Optional[QLabel] = None

        super().__init__(*args, **kwargs)

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._post_due_direct_debits()
        self._load_and_refresh_accounts()
        self._reload()

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
        lay.setSpacing(16)

        lay.addWidget(self._build_hero(root), 0)
        lay.addWidget(self._build_tiles(root), 0)
        lay.addWidget(self._build_table_panel(root), 1)

        self._reload()

    # ------------------------------------------------------------------ hero
    def _build_hero(self, parent: QWidget) -> QWidget:
        hero = QWidget(parent)
        hero.setObjectName("ContentPanel")
        try:
            hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except QT_ERRORS:
            pass
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(24, 22, 24, 22)
        hero_l.setSpacing(18)

        top = QHBoxLayout()
        top.setSpacing(16)

        id_col = QVBoxLayout()
        id_col.setSpacing(8)
        self._name_lbl = QLabel("", hero)
        self._name_lbl.setObjectName("EventName")
        self._name_lbl.setWordWrap(True)
        id_col.addWidget(self._name_lbl)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self._acct_badge = QLabel("", hero)
        self._acct_badge.setObjectName("PlanBadge")
        # One combined, word-wrapping meta label so the row breaks cleanly as a
        # unit when narrow (keeps the page dynamic) instead of forcing width.
        self._meta_lbl = QLabel("", hero)
        self._meta_lbl.setObjectName("Subtitle")
        self._meta_lbl.setWordWrap(True)
        meta.addWidget(self._acct_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        meta.addWidget(self._meta_lbl, 1)
        id_col.addLayout(meta)

        id_wrap = QWidget(hero)
        id_wrap.setLayout(id_col)
        top.addWidget(id_wrap, 1)

        actions = QWidget(hero)
        actions_l = QHBoxLayout(actions)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(8)
        self._selector = InstallmentsSelector(
            actions,
            on_selected=self._on_plan_selected,
            on_add_plan=self._on_add_clicked,
            on_add_direct_debit=self._on_add_direct_debit_clicked,
            on_delete_plan=self._on_delete_clicked,
        )
        # The hero title already shows the full plan name, so the selector
        # button need not grow to fit long names — cap it so the page stays
        # dynamic and never forces the window wider.
        try:
            self._selector.setMaximumWidth(200)
            self._selector.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
        except QT_ERRORS:
            pass
        actions_l.addWidget(self._selector, 0)

        self._exclude_btn = QToolButton(actions)
        self._exclude_btn.setObjectName("IconButton")
        self._exclude_btn.setText("🚫")
        self._exclude_btn.setToolTip("החרג תנועה מהרשימה")
        self._exclude_btn.clicked.connect(self._on_exclude_selected_row)
        actions_l.addWidget(self._exclude_btn)

        self._edit_btn = QToolButton(actions)
        self._edit_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(self._edit_btn, "edit", size=18, is_dark=self._is_dark_theme())
        except QT_ERRORS:
            self._edit_btn.setText("✎")
        self._edit_btn.setToolTip("עריכת תכנית")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        actions_l.addWidget(self._edit_btn)
        top.addWidget(actions, 0, Qt.AlignmentFlag.AlignTop)

        hero_l.addLayout(top)

        # payment-progress bar
        self._prog_wrap = QWidget(hero)
        pwl = QVBoxLayout(self._prog_wrap)
        pwl.setContentsMargins(0, 0, 0, 0)
        pwl.setSpacing(9)

        prow = QHBoxLayout()
        prow.setSpacing(12)
        self._prog_lead = QLabel("", self._prog_wrap)
        self._prog_lead.setObjectName("Subtitle")
        self._prog_lead.setWordWrap(True)
        self._prog_left = QLabel("", self._prog_wrap)
        self._prog_left.setObjectName("BudgetRemain")
        # Give the lead the stretch so a word-wrap label keeps one line while
        # there's room and only wraps when the window is genuinely narrow.
        prow.addWidget(self._prog_lead, 1)
        prow.addWidget(self._prog_left, 0)
        pwl.addLayout(prow)

        self._prog_bar = QProgressBar(self._prog_wrap)
        self._prog_bar.setObjectName("BudgetBar")
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setTextVisible(False)
        try:
            self._prog_bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self._prog_bar.setFixedHeight(14)
            self._prog_bar.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except QT_ERRORS:
            pass
        pwl.addWidget(self._prog_bar)

        ticks = QHBoxLayout()
        ticks.setSpacing(8)
        tick_first = QLabel("תשלום 1", self._prog_wrap)
        tick_first.setObjectName("TickLabel")
        self._tick_first = tick_first
        self._tick_last = QLabel("", self._prog_wrap)
        self._tick_last.setObjectName("TickLabel")
        # RTL: "תשלום 1" at the right (fill origin), last payment at left.
        ticks.addWidget(tick_first, 0)
        ticks.addStretch(1)
        ticks.addWidget(self._tick_last, 0)
        pwl.addLayout(ticks)

        hero_l.addWidget(self._prog_wrap)
        return hero

    # ----------------------------------------------------------------- tiles
    def _build_tiles(self, parent: QWidget) -> QWidget:
        self._card_titles = []
        tiles = QWidget(parent)
        tiles_l = QHBoxLayout(tiles)
        tiles_l.setContentsMargins(0, 0, 0, 0)
        tiles_l.setSpacing(16)

        def build_card(title_text: str, style: str) -> QLabel:
            card = QWidget(tiles)
            card.setObjectName(style)
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                card.setAutoFillBackground(True)
            except QT_ERRORS:
                pass
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(6)
            title = QLabel(title_text, card)
            title.setObjectName("StatTitle")
            self._card_titles.append(title)
            value = QLabel("", card)
            value.setObjectName("StatValueCard")
            cl.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(value, 0, Qt.AlignmentFlag.AlignHCenter)
            tiles_l.addWidget(card, 1)
            return value

        self._card_original = build_card("סכום מקורי", "MonthNetCard")
        self._card_paid = build_card("שולם עד כה", "MonthIncomeCard")
        self._card_left = build_card("נותר לתשלום", "MonthInfoCard")
        self._card_overpaid = build_card("חריגה", "MonthExpenseCard")
        return tiles

    # ----------------------------------------------------------------- table
    def _build_table_panel(self, parent: QWidget) -> QWidget:
        table_card = QWidget(parent)
        table_card.setObjectName("ContentPanel")
        try:
            table_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except QT_ERRORS:
            pass
        table_card_l = QVBoxLayout(table_card)
        table_card_l.setContentsMargins(20, 18, 20, 18)
        table_card_l.setSpacing(10)

        title = QLabel("התשלומים שנמצאו", table_card)
        title.setObjectName("PanelTitle")
        self._table_title = title
        table_card_l.addWidget(title)

        self._table = QTableWidget(table_card)
        self._table.setObjectName("ActionHistoryTableWidget")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["תאריך", "סכום", "קטגוריה", "תיאור"])
        self._table.setRowCount(0)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        try:
            self._table.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        try:
            header = self._table.horizontalHeader()
            if header is not None:
                header.setObjectName("ActionHistoryHeader")
                header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            vheader = self._table.verticalHeader()
            if vheader is not None:
                vheader.setVisible(False)
        except QT_ERRORS:
            pass
        table_card_l.addWidget(self._table, 1)
        return table_card

    def _reload(self) -> None:
        try:
            self._plans = self._service.list_plans()
        except QT_ERRORS:
            self._plans = []
        if self._selected_plan_id and not any(
            p.id == self._selected_plan_id for p in self._plans
        ):
            self._selected_plan_id = None
        if self._selected_plan_id is None and self._plans:
            self._selected_plan_id = self._plans[0].id

        if self._selector is not None:
            self._selector.set_plans(self._plans, self._selected_plan_id)

        self._refresh_details()

    def _selected_plan(self) -> Optional[InstallmentPlan]:
        pid = str(self._selected_plan_id or "").strip()
        if not pid:
            return None
        for p in self._plans:
            if p.id == pid:
                return p
        return None

    def _refresh_details(self) -> None:
        plan = self._selected_plan()
        if self._table is None:
            return
        if plan is None:
            self._table.setRowCount(0)
            if self._name_lbl is not None:
                self._name_lbl.setText("אין תכניות תשלומים או הוראות קבע")
            if self._acct_badge is not None:
                self._acct_badge.setText("")
                self._acct_badge.setVisible(False)
            if self._meta_lbl is not None:
                self._meta_lbl.setText("")
                self._meta_lbl.setVisible(False)
            if self._prog_wrap is not None:
                self._prog_wrap.setVisible(False)
            for card in (
                self._card_original,
                self._card_paid,
                self._card_left,
                self._card_overpaid,
            ):
                if card is not None:
                    card.setText("—")
            if self._edit_btn is not None:
                self._edit_btn.setEnabled(False)
            if self._exclude_btn is not None:
                self._exclude_btn.setEnabled(False)
            return

        if self._edit_btn is not None:
            self._edit_btn.setEnabled(True)
        dd = plan.is_direct_debit
        if self._exclude_btn is not None:
            # A direct debit is not matched against bank movements.
            self._exclude_btn.setEnabled(not dd)
            self._exclude_btn.setVisible(not dd)
        self._apply_kind_labels(dd)

        stats = self._service.compute_stats(plan)

        # ── hero identity ──
        if self._name_lbl is not None:
            self._name_lbl.setText((plan.name or "ללא שם").strip() or "ללא שם")
        acct = str(plan.account_name or "").strip()
        if self._acct_badge is not None:
            self._acct_badge.setText(acct)
            self._acct_badge.setVisible(bool(acct))
        start_txt = self._format_date_he(plan.start_date)
        left_n = int(getattr(stats, "payments_left", 0) or 0)
        parts = []
        if dd:
            parts.append("הוראת קבע")
            parts.append(
                f"{format_currency(float(plan.monthly_amount))} בחודש"
            )
            sched = plan.schedule()
            if sched:
                parts.append(f"יורד ב-{sched[0].date.day} לכל חודש")
                start_txt = self._format_date_he(sched[0].date.isoformat())
        if start_txt:
            parts.append(f"החל {start_txt}")
        if dd:
            parts.append(
                f"נותרו {left_n} חיובים" if left_n > 0 else "כל החיובים בוצעו"
            )
        else:
            parts.append(
                f"נותרו {left_n} תשלומים" if left_n > 0 else "כל התשלומים בוצעו"
            )
        if self._meta_lbl is not None:
            self._meta_lbl.setText("  ·  ".join(parts))
            self._meta_lbl.setVisible(bool(parts))

        # ── payment-progress bar ──
        self._fill_progress(plan, stats)

        # ── tiles ──
        original = float(plan.original_amount)
        paid = float(stats.total_paid)
        remaining = max(0.0, original - paid)
        if self._card_original is not None:
            self._card_original.setText(format_currency(original, use_compact=True))
        if self._card_paid is not None:
            self._card_paid.setText(format_currency(paid, use_compact=True))
        if self._card_left is not None:
            self._card_left.setText(format_currency(remaining, use_compact=True))
        if self._card_overpaid is not None:
            self._card_overpaid.setText(
                format_currency(
                    float(plan.monthly_amount if dd else stats.overpaid),
                    use_compact=True,
                )
            )

        # ── table ──
        if dd:
            self._fill_schedule_table(plan)
        else:
            self._fill_table(stats.matched_movements)

    def _apply_kind_labels(self, dd: bool) -> None:
        """Tile/table wording differs between installment plans and direct debits."""
        titles = (
            ("סכום כולל", "ירד עד כה", "נותר לחיוב", "חיוב חודשי")
            if dd
            else ("סכום מקורי", "שולם עד כה", "נותר לתשלום", "חריגה")
        )
        for lbl, text in zip(self._card_titles, titles):
            try:
                lbl.setText(text)
            except QT_ERRORS:
                pass
        if self._table_title is not None:
            self._table_title.setText("לוח החיובים" if dd else "התשלומים שנמצאו")
        if self._table is not None:
            try:
                self._table.setHorizontalHeaderLabels(
                    ["תאריך", "סכום", "חיוב", "סטטוס"]
                    if dd
                    else ["תאריך", "סכום", "קטגוריה", "תיאור"]
                )
            except QT_ERRORS:
                pass

    def _fill_schedule_table(self, plan: InstallmentPlan) -> None:
        if self._table is None:
            return
        sched = plan.schedule()
        total = len(sched)
        self._table.setRowCount(total)
        for row, p in enumerate(sched):
            cells = (
                QTableWidgetItem(self._format_date_he(p.date.isoformat())),
                QTableWidgetItem(format_currency(-p.amount, use_compact=True)),
                QTableWidgetItem(f"{p.number} מתוך {total}"),
                QTableWidgetItem("ירד" if p.done else "עתידי"),
            )
            try:
                cells[1].setForeground(QColor("#d66a4e"))
                cells[3].setForeground(QColor("#2f9e68" if p.done else "#8a94a6"))
            except QT_ERRORS:
                pass
            for col, it in enumerate(cells):
                try:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                except QT_ERRORS:
                    pass
                self._table.setItem(row, col, it)

    # -------------------------------------------------------- refresh helpers
    def _fill_progress(self, plan: InstallmentPlan, stats) -> None:
        total_n = int(plan.payments_count or 0)
        paid_n = int(stats.paid_count or 0)
        if self._prog_wrap is not None:
            self._prog_wrap.setVisible(total_n > 0)
        if total_n <= 0:
            return

        pct = max(0.0, min(1.0, paid_n / total_n))
        original = float(plan.original_amount)
        paid = float(stats.total_paid)
        over = float(stats.overpaid) > 0.0

        noun = ("ירדו", "חיובים") if plan.is_direct_debit else ("שולמו", "תשלומים")
        lead = (
            f"{noun[0]} <b>{paid_n}</b> מתוך <b>{total_n}</b> {noun[1]} · "
            f"<b>{int(round(pct * 100))}%</b>"
        )
        if original > 0:
            lead += (
                f" · <b>{format_currency(paid, use_compact=True)}</b> "
                f"מתוך {format_currency(original, use_compact=True)}"
            )
        if self._prog_lead is not None:
            self._prog_lead.setText(lead)

        remaining = max(0.0, original - paid)
        if self._prog_left is not None:
            if over:
                self._prog_left.setText(
                    f"חריגה {format_currency(float(stats.overpaid), use_compact=True)}"
                )
                self._prog_left.setStyleSheet("color:#d66a4e;font-weight:800;")
            elif original > 0:
                self._prog_left.setText(
                    f"נותרו {format_currency(remaining, use_compact=True)}"
                )
                self._prog_left.setStyleSheet("color:#2f9e68;font-weight:800;")
            else:
                self._prog_left.setText("")
        if self._tick_first is not None:
            self._tick_first.setText(
                "חיוב 1" if plan.is_direct_debit else "תשלום 1"
            )
        if self._tick_last is not None:
            self._tick_last.setText(
                f"{'חיוב' if plan.is_direct_debit else 'תשלום'} {total_n}"
            )
        if self._prog_bar is not None:
            self._prog_bar.setValue(int(round(pct * 100)))
            chunk = (
                "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #e9a491,stop:1 #d66a4e)"
                if over
                else "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #8FBF9F,stop:1 #2f9e68)"
            )
            self._prog_bar.setStyleSheet(
                "QProgressBar#BudgetBar{background:#eef1ea;border:none;"
                "border-radius:7px;}"
                "QProgressBar#BudgetBar::chunk{border-radius:7px;background:"
                f"{chunk};}}"
            )

    def _fill_table(self, movements) -> None:
        if self._table is None:
            return
        self._table.setRowCount(len(movements))
        for row, m in enumerate(movements):
            date_item = QTableWidgetItem(self._format_date_he(str(m.date)) or str(m.date))
            try:
                amt = float(getattr(m, "amount", 0.0))
            except QT_ERRORS:
                amt = 0.0
            amt_item = QTableWidgetItem(format_currency(amt, use_compact=True))
            try:
                amt_item.setForeground(QColor("#d66a4e" if amt < 0 else "#2f9e68"))
            except QT_ERRORS:
                pass
            cat_item = QTableWidgetItem(str(m.category or ""))
            desc_item = QTableWidgetItem(str(m.description or ""))
            for col, it in enumerate((date_item, amt_item, cat_item, desc_item)):
                try:
                    it.setData(Qt.ItemDataRole.UserRole, str(m.id))
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                except QT_ERRORS:
                    pass
                self._table.setItem(row, col, it)

    @staticmethod
    def _format_date_he(raw: Optional[str]) -> str:
        if not raw:
            return ""
        try:
            from datetime import datetime
            d = datetime.strptime(str(raw)[:10], "%Y-%m-%d")
            months = [
                "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
            ]
            return f"{d.day} ב{months[d.month - 1]} {d.year}"
        except QT_ERRORS:
            return str(raw)

    def _on_plan_selected(self, plan_id: str) -> None:
        self._selected_plan_id = str(plan_id or "").strip() or None
        self._refresh_details()

    def _on_add_direct_debit_clicked(self) -> None:
        self._on_add_clicked(kind=KIND_DIRECT_DEBIT)

    def _expense_categories(self) -> List[str]:
        try:
            return list(self._bank_movement_provider.list_categories_for_type(False))
        except QT_ERRORS:
            return []

    def _post_due_direct_debits(self) -> None:
        """Turn due direct debit charges into bank movements, then refresh
        balances if anything was posted."""
        try:
            n = self._service.post_due_direct_debits()
        except QT_ERRORS:
            n = 0
        if n <= 0:
            return
        try:
            if isinstance(self._app_context, dict):
                self._app_context["_balances_dirty"] = "1"
            self._load_and_refresh_accounts()
        except QT_ERRORS:
            pass

    def _on_add_clicked(self, kind: str = KIND_INSTALLMENTS) -> None:
        dlg = InstallmentPlanDialog(
            accounts=self._accounts,
            kind=kind,
            categories=self._expense_categories(),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        plan = dlg.get_plan()
        if plan is None:
            return
        self._service.upsert_plan(plan)
        self._post_due_direct_debits()
        self._selected_plan_id = plan.id
        self._reload()

    def _on_edit_clicked(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "עריכה", "בחר תכנית כדי לערוך")
            return
        dlg = InstallmentPlanDialog(
            accounts=self._accounts,
            plan=plan,
            categories=self._expense_categories(),
            parent=self,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_plan()
        if updated is None:
            return
        self._service.upsert_plan(updated)
        self._post_due_direct_debits()
        self._selected_plan_id = updated.id
        self._reload()

    def _on_delete_clicked(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "מחיקה", "בחר תכנית כדי למחוק")
            return
        res = QMessageBox.question(
            self,
            "מחיקה",
            f'למחוק את "{plan.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        self._service.delete_plan(plan.id)
        self._selected_plan_id = None
        self._reload()

    def _selected_row_movement_id(self) -> Optional[str]:
        if self._table is None:
            return None
        try:
            row = self._table.currentRow()
            if row < 0:
                return None
            item = self._table.item(row, 0)
            if item is None:
                return None
            mid = item.data(Qt.ItemDataRole.UserRole)
            mid = str(mid or "").strip()
            return mid if mid else None
        except QT_ERRORS:
            return None

    def _on_exclude_selected_row(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "בחירה", "בחר תכנית")
            return
        mid = self._selected_row_movement_id()
        if not mid:
            QMessageBox.information(self, "בחירה", "בחר תנועה כדי להחריג")
            return
        self._service.exclude_movement(plan_id=plan.id, movement_id=mid)
        self._reload()
