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
from ..models.installment_plan import InstallmentPlan
from ..models.installments_service import InstallmentsService
from ..widgets.installments_selector import InstallmentsSelector
from .base_page import BasePage


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


class InstallmentPlanDialog(QDialog):
    def __init__(
        self,
        *,
        accounts: List[MoneyAccount],
        plan: Optional[InstallmentPlan] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("תכנית תשלומים")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        self._plan: Optional[InstallmentPlan] = plan
        self._accounts = accounts

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        title = QLabel("תכנית תשלומים", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם (לדוגמה: טלוויזיה)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._vendor_query = QLineEdit(self)
        self._vendor_query.setPlaceholderText("חיפוש ספק (מופיע בתיאור התנועה)")
        root.addWidget(QLabel("חיפוש ספק", self))
        root.addWidget(self._vendor_query)

        self._account = QComboBox(self)
        self._account.setEditable(False)
        account_names: List[str] = []
        for a in accounts:
            try:
                if isinstance(a, (BankAccount, BudgetAccount)) and bool(
                    getattr(a, "active", False)
                ):
                    name = str(getattr(a, "name", "") or "").strip()
                    if name:
                        account_names.append(name)
            except Exception:
                continue
        account_names = sorted(set(account_names))
        self._account.addItems(account_names)
        root.addWidget(QLabel("חשבון מקור", self))
        root.addWidget(self._account)

        self._start_date = QDateEdit(self)
        self._start_date.setCalendarPopup(True)
        setup_calendar_popup(self._start_date)
        try:
            self._start_date.setDisplayFormat("yyyy-MM-dd")
        except Exception:
            pass
        root.addWidget(QLabel("תאריך התחלה", self))
        root.addWidget(self._start_date)

        self._payments_count = QSpinBox(self)
        self._payments_count.setMinimum(1)
        self._payments_count.setMaximum(240)
        root.addWidget(QLabel("מספר תשלומים", self))
        root.addWidget(self._payments_count)

        self._original_amount = QLineEdit(self)
        self._original_amount.setPlaceholderText("סכום כולל (לדוגמה: 3500)")
        root.addWidget(QLabel("סכום מקורי", self))
        root.addWidget(self._original_amount)

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

    def _load_initial(self) -> None:
        p = self._plan
        if p is None:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
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
        except Exception:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
                pass
        self._payments_count.setValue(max(1, int(p.payments_count)))
        self._original_amount.setText(str(float(p.original_amount)))
        self._archived.setChecked(bool(getattr(p, "archived", False)))

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        vendor_query = str(self._vendor_query.text() or "").strip()
        account_name = str(self._account.currentText() or "").strip()
        payments_count = int(self._payments_count.value())
        start_date = ""
        try:
            start_date = self._start_date.date().toString("yyyy-MM-dd")
        except Exception:
            start_date = ""
        try:
            original_amount = float(
                str(self._original_amount.text() or "").strip() or 0.0
            )
        except Exception:
            original_amount = 0.0
        archived = bool(self._archived.isChecked())

        if not name:
            QMessageBox.warning(self, "שגיאה", "שם לא יכול להיות ריק")
            return
        if not vendor_query:
            QMessageBox.warning(self, "שגיאה", "חיפוש ספק לא יכול להיות ריק")
            return
        if not account_name:
            QMessageBox.warning(self, "שגיאה", "צריך לבחור חשבון מקור")
            return
        if payments_count <= 0:
            QMessageBox.warning(self, "שגיאה", "מספר תשלומים חייב להיות גדול מ-0")
            return
        if original_amount < 0:
            QMessageBox.warning(self, "שגיאה", "סכום מקורי לא יכול להיות שלילי")
            return

        if self._plan is None:
            self._plan = InstallmentPlan(
                name=name,
                vendor_query=vendor_query,
                account_name=account_name,
                start_date=start_date,
                payments_count=payments_count,
                original_amount=float(original_amount),
                archived=archived,
            )
        else:
            self._plan = InstallmentPlan(
                id=self._plan.id,
                name=name,
                vendor_query=vendor_query,
                account_name=account_name,
                start_date=start_date,
                payments_count=payments_count,
                original_amount=float(original_amount),
                excluded_movement_ids=list(self._plan.excluded_movement_ids),
                archived=archived,
            )
        self.accept()

    def get_plan(self) -> Optional[InstallmentPlan]:
        return self._plan


class InstallmentsPage(BasePage):
    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
            settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

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
        # hero + progress
        self._name_lbl: Optional[QLabel] = None
        self._acct_badge: Optional[QLabel] = None
        self._start_lbl: Optional[QLabel] = None
        self._start_sep: Optional[QLabel] = None
        self._left_lbl: Optional[QLabel] = None
        self._left_sep: Optional[QLabel] = None
        self._prog_wrap: Optional[QWidget] = None
        self._prog_lead: Optional[QLabel] = None
        self._prog_left: Optional[QLabel] = None
        self._prog_bar: Optional[QProgressBar] = None
        self._tick_last: Optional[QLabel] = None

        super().__init__(*args, **kwargs)

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._load_and_refresh_accounts()
        self._reload()

    def _build_content(self, content_col: QVBoxLayout) -> None:
        self._clear_content_layout(content_col)

        root = QWidget(self)
        try:
            root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
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
        except Exception:
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
        id_col.addWidget(self._name_lbl)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self._acct_badge = QLabel("", hero)
        self._acct_badge.setObjectName("PlanBadge")
        self._start_lbl = QLabel("", hero)
        self._start_lbl.setObjectName("Subtitle")
        self._start_sep = self._make_dot(hero)
        self._left_lbl = QLabel("", hero)
        self._left_lbl.setObjectName("Subtitle")
        self._left_sep = self._make_dot(hero)
        meta.addWidget(self._acct_badge, 0)
        meta.addWidget(self._start_sep, 0)
        meta.addWidget(self._start_lbl, 0)
        meta.addWidget(self._left_sep, 0)
        meta.addWidget(self._left_lbl, 0)
        meta.addStretch(1)
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
            on_delete_plan=self._on_delete_clicked,
        )
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
        except Exception:
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
        self._prog_left = QLabel("", self._prog_wrap)
        self._prog_left.setObjectName("BudgetRemain")
        prow.addWidget(self._prog_lead, 0)
        prow.addStretch(1)
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
        except Exception:
            pass
        pwl.addWidget(self._prog_bar)

        ticks = QHBoxLayout()
        ticks.setSpacing(8)
        tick_first = QLabel("תשלום 1", self._prog_wrap)
        tick_first.setObjectName("TickLabel")
        self._tick_last = QLabel("", self._prog_wrap)
        self._tick_last.setObjectName("TickLabel")
        # RTL: "תשלום 1" at the right (fill origin), last payment at left.
        ticks.addWidget(tick_first, 0)
        ticks.addStretch(1)
        ticks.addWidget(self._tick_last, 0)
        pwl.addLayout(ticks)

        hero_l.addWidget(self._prog_wrap)
        return hero

    @staticmethod
    def _make_dot(parent: QWidget) -> QLabel:
        dot = QLabel("•", parent)
        dot.setObjectName("MetaDot")
        return dot

    # ----------------------------------------------------------------- tiles
    def _build_tiles(self, parent: QWidget) -> QWidget:
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
            except Exception:
                pass
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(6)
            title = QLabel(title_text, card)
            title.setObjectName("StatTitle")
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
        except Exception:
            pass
        table_card_l = QVBoxLayout(table_card)
        table_card_l.setContentsMargins(20, 18, 20, 18)
        table_card_l.setSpacing(10)

        title = QLabel("התשלומים שנמצאו", table_card)
        title.setObjectName("PanelTitle")
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
        except Exception:
            pass
        try:
            header = self._table.horizontalHeader()
            if header is not None:
                header.setObjectName("ActionHistoryHeader")
                header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            vheader = self._table.verticalHeader()
            if vheader is not None:
                vheader.setVisible(False)
        except Exception:
            pass
        table_card_l.addWidget(self._table, 1)
        return table_card

    def _reload(self) -> None:
        try:
            self._plans = self._service.list_plans()
        except Exception:
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
                self._name_lbl.setText("אין תכניות תשלומים")
            for lbl in (self._acct_badge, self._start_lbl, self._left_lbl):
                if lbl is not None:
                    lbl.setText("")
                    lbl.setVisible(False)
            for sep in (self._start_sep, self._left_sep):
                if sep is not None:
                    sep.setVisible(False)
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
        if self._exclude_btn is not None:
            self._exclude_btn.setEnabled(True)

        stats = self._service.compute_stats(plan)

        # ── hero identity ──
        if self._name_lbl is not None:
            self._name_lbl.setText((plan.name or "ללא שם").strip() or "ללא שם")
        acct = str(plan.account_name or "").strip()
        if self._acct_badge is not None:
            self._acct_badge.setText(acct)
            self._acct_badge.setVisible(bool(acct))
        start_txt = self._format_date_he(plan.start_date)
        if self._start_lbl is not None:
            self._start_lbl.setText(f"החל {start_txt}" if start_txt else "")
            self._start_lbl.setVisible(bool(start_txt))
        if self._start_sep is not None:
            self._start_sep.setVisible(bool(acct) and bool(start_txt))
        left_n = int(getattr(stats, "payments_left", 0) or 0)
        left_txt = f"נותרו {left_n} תשלומים" if left_n > 0 else "כל התשלומים בוצעו"
        if self._left_lbl is not None:
            self._left_lbl.setText(left_txt)
            self._left_lbl.setVisible(True)
        if self._left_sep is not None:
            self._left_sep.setVisible(bool(start_txt) or bool(acct))

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
                format_currency(float(stats.overpaid), use_compact=True)
            )

        # ── table ──
        self._fill_table(stats.matched_movements)

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

        lead = (
            f"שולמו <b>{paid_n}</b> מתוך <b>{total_n}</b> תשלומים · "
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
        if self._tick_last is not None:
            self._tick_last.setText(f"תשלום {total_n}")
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
            except Exception:
                amt = 0.0
            amt_item = QTableWidgetItem(format_currency(amt, use_compact=True))
            try:
                amt_item.setForeground(QColor("#d66a4e" if amt < 0 else "#2f9e68"))
            except Exception:
                pass
            cat_item = QTableWidgetItem(str(m.category or ""))
            desc_item = QTableWidgetItem(str(m.description or ""))
            for col, it in enumerate((date_item, amt_item, cat_item, desc_item)):
                try:
                    it.setData(Qt.ItemDataRole.UserRole, str(m.id))
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                except Exception:
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
        except Exception:
            return str(raw)

    def _on_plan_selected(self, plan_id: str) -> None:
        self._selected_plan_id = str(plan_id or "").strip() or None
        self._refresh_details()

    def _on_add_clicked(self) -> None:
        dlg = InstallmentPlanDialog(accounts=self._accounts, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        plan = dlg.get_plan()
        if plan is None:
            return
        self._service.upsert_plan(plan)
        self._selected_plan_id = plan.id
        self._reload()

    def _on_edit_clicked(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            QMessageBox.information(self, "עריכה", "בחר תכנית כדי לערוך")
            return
        dlg = InstallmentPlanDialog(accounts=self._accounts, plan=plan, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_plan()
        if updated is None:
            return
        self._service.upsert_plan(updated)
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
        except Exception:
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
