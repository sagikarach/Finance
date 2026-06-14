from __future__ import annotations

from dataclasses import replace
from typing import List, Optional

from ..qt import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
    Qt,
)
from ..models.accounts import BankAccount, MoneyAccount, SavingsAccount
from ..models.mortgage import (
    AssetKind,
    CostItem,
    FundingKind,
    FundingSource,
    Mortgage,
)
from ..models.mortgage_service import MortgageService
from ..models.mortgage_math import (
    cost_paid_amount,
    query_paid_amount,
    query_received_amount,
)
from .mortgage_page import HousePurchaseDialog
from .base_page import BasePage

_BANK_ACCOUNT_NAME = "בנק"  # החשבון שמכסה את היתרה (תואם למסך המשכנתא)


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


def _parse_float(text: str) -> Optional[float]:
    s = str(text or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _endpoint_balance(
    accounts: List[MoneyAccount], account_name: str, saving_name: str = ""
) -> float:
    """יתרת היעד: חיסכון ספציפי בתוך חשבון חיסכון (אם ``saving_name``), אחרת
    יתרת החשבון עצמו — ברמת בחירת ההעברות."""
    account_name = str(account_name or "").strip()
    saving_name = str(saving_name or "").strip()
    for a in accounts:
        if str(getattr(a, "name", "") or "").strip() != account_name:
            continue
        if saving_name and isinstance(a, SavingsAccount):
            for sv in a.savings:
                if str(getattr(sv, "name", "") or "").strip() == saving_name:
                    return float(getattr(sv, "amount", 0.0) or 0.0)
            return 0.0
        return float(getattr(a, "total_amount", 0.0) or 0.0)
    return 0.0


def funding_endpoints(
    accounts: List[MoneyAccount],
) -> List[tuple[str, str, str, float]]:
    """רשימת יעדים לבחירה (כמו בהעברה): חשבונות בנק + חסכונות בודדים.

    כל פריט: (תווית, שם_חשבון, שם_חיסכון, יתרה)."""
    out: List[tuple[str, str, str, float]] = []
    for a in accounts:
        if isinstance(a, SavingsAccount):
            for sv in a.savings:
                out.append(
                    (
                        f"{a.name} / {sv.name}",
                        str(a.name),
                        str(sv.name),
                        float(getattr(sv, "amount", 0.0) or 0.0),
                    )
                )
        elif isinstance(a, BankAccount) and bool(getattr(a, "active", False)):
            out.append((str(a.name), str(a.name), "", float(a.total_amount)))
    return out


def funding_available(
    source: FundingSource,
    movements: List,
    accounts: List[MoneyAccount],
) -> float:
    """כמה כסף ממקור המימון זמין/התקבל בפועל כעת."""
    if source.kind == FundingKind.ACCOUNT:
        return _endpoint_balance(accounts, source.account_name, source.saving_name)
    if source.kind == FundingKind.MOVEMENTS:
        return query_received_amount(source.query, movements, include_transfers=True)
    return 0.0  # עתידי — טרם התקבל


def account_transferred_out(movements: List, account_name: str) -> float:
    """סך ההעברות היוצאות מחשבון נתון (העברות בלבד, סכום שלילי) — הכסף שהוזרם
    מהחשבון אל חשבון הבנק לצורך הרכישה."""
    name = str(account_name or "").strip()
    if not name:
        return 0.0
    total = 0.0
    for m in movements:
        try:
            if (
                bool(getattr(m, "is_transfer", False))
                and float(getattr(m, "amount", 0.0) or 0.0) < 0
                and str(getattr(m, "account_name", "") or "").strip() == name
            ):
                total += abs(float(m.amount))
        except Exception:
            continue
    return float(total)


def funding_spent(source: FundingSource, movements: List) -> Optional[float]:
    """כמה נוצל בפועל ממקור המימון. חשבון → העברות יוצאות ממנו אל הבנק;
    תנועות → ההכנסה שנתפסה; עתידי → None ('—'). חשבון הבנק עצמו מטופל בנפרד."""
    if source.kind == FundingKind.ACCOUNT:
        return account_transferred_out(movements, source.account_name)
    if source.kind == FundingKind.MOVEMENTS:
        return query_received_amount(source.query, movements, include_transfers=True)
    return None  # עתידי


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
        except Exception:
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
        except Exception:
            pass
        if s.amount:
            self._amount.setText(f"{float(s.amount):.0f}")
        # בחר את הפריט התואם (חשבון + חיסכון).
        target = (str(s.account_name or ""), str(s.saving_name or ""))
        for i in range(self._account.count()):
            if self._account.itemData(i) == target:
                self._account.setCurrentIndex(i)
                break
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
            bal = _endpoint_balance(self._accounts, acc_name, sv_name)
            label = "יתרת החיסכון" if sv_name else "יתרת החשבון"
            self._balance_lbl.setText(f"{label}: {_fmt_money(bal)} ₪")
        else:
            self._balance_lbl.setText("")

    def _on_save(self) -> None:
        try:
            kind = FundingKind(str(self._kind.currentText()))
        except Exception:
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
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("הוצאה")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        self._cost = cost

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
        self._amount.setPlaceholderText("סכום מתוכנן")
        root.addWidget(QLabel("סכום", self))
        root.addWidget(self._amount)

        self._query = QLineEdit(self)
        self._query.setPlaceholderText("חיפוש תנועות (אופציונלי) — לחישוב ששולם בפועל")
        self._query_label = QLabel("חיפוש תנועות", self)
        root.addWidget(self._query_label)
        root.addWidget(self._query)
        if not show_query:
            self._query_label.setVisible(False)
            self._query.setVisible(False)

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

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        query = str(self._query.text() or "").strip()
        if not name and not query:
            QMessageBox.warning(self, "שגיאה", "שם ההוצאה לא יכול להיות ריק")
            return
        self._cost = CostItem(
            name=name,
            amount=_parse_float(self._amount.text()) or 0.0,
            query=query,
        )
        self.accept()

    def get_cost(self) -> Optional[CostItem]:
        return self._cost


class AssetDetailPage(BasePage):
    """עמוד הנכס (רכישה) — מציג את כל התשלומים בתהליך, כולל המשכנתא כחלק לחיץ."""

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
        kwargs.setdefault("page_title", "נכס")
        kwargs.setdefault("current_route", "asset")
        self._service = MortgageService()
        self._funding_table: Optional[QTableWidget] = None
        self._funding_sources: List[FundingSource] = []
        self._expense_table: Optional[QTableWidget] = None
        self._one_time_costs: List[CostItem] = []
        self._monthly_table: Optional[QTableWidget] = None
        self._monthly_costs: List[CostItem] = []
        self._active_tab: str = "expenses"
        self._tab_cards: dict = {}
        self._tab_buttons: dict = {}
        super().__init__(*args, **kwargs)

    def _load_accounts(self) -> List[MoneyAccount]:
        try:
            return list(self._accounts_service.load_accounts() or [])
        except Exception:
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
        except Exception:
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
        except Exception:
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

        s = self._service.purchase_summary(m)

        # כותרת + כפתורי פעולה (חזרה, משכנתא, עריכת רכישה) — כולם בשורת הכותרת.
        title_row = QHBoxLayout()
        back_btn = QToolButton(root)
        back_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(back_btn, "arrow_left", size=20, is_dark=self._is_dark_theme())
        except Exception:
            back_btn.setText("←")
        back_btn.setToolTip("חזרה לרשימת הנכסים")
        if self._navigate is not None:
            back_btn.clicked.connect(lambda: self._navigate("assets"))
        title_row.addWidget(back_btn, 0)

        name_lbl = QLabel(m.name or "(ללא שם)", root)
        name_lbl.setObjectName("HeaderTitle")
        title_row.addWidget(name_lbl, 0)
        title_row.addStretch(1)

        # כפתור המשכנתא — בשורת הכותרת לצד שאר הכפתורים, פותח את פרטי המשכנתא.
        if s.tracks_total > 0:
            mort_text = (
                f"משכנתא: {_fmt_money(s.tracks_total)} ₪ · "
                f"{_fmt_money(s.mortgage_monthly)} ₪/חודש   ›"
            )
        elif s.required_mortgage > 0:
            mort_text = f"משכנתא: בנה תמהיל בסך {_fmt_money(s.required_mortgage)} ₪   ›"
        else:
            mort_text = "משכנתא — פתח פרטים   ›"
        mort_btn = QPushButton(mort_text, root)
        mort_btn.setObjectName("SecondaryButton")
        mort_btn.setToolTip("פתח את פרטי המשכנתא (תמהיל, לוח סילוקין, תנועות)")
        try:
            mort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            mort_btn.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        mort_btn.clicked.connect(self._open_mortgage)
        title_row.addWidget(mort_btn, 0)

        edit_btn = QToolButton(root)
        edit_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(edit_btn, "edit", size=20, is_dark=self._is_dark_theme())
        except Exception:
            edit_btn.setText("✎")
        edit_btn.setToolTip("ערוך מחיר ועלויות")
        edit_btn.clicked.connect(self._on_edit_purchase)
        title_row.addWidget(edit_btn)
        lay.addLayout(title_row, 0)

        movements = self._service.list_movements()
        accounts = self._load_accounts()
        self._funding_sources = list(m.funding_sources)

        # מה שכבר שולם מהבנק לרכישה = מחיר ששולם + עלויות ששולמו.
        price_query = str(getattr(m, "price_query", "") or "").strip()
        price_paid = (
            query_paid_amount(price_query, movements, include_transfers=True)
            if price_query
            else 0.0
        )
        exp_paid = price_paid + sum(
            cost_paid_amount(c, movements) for c in m.one_time_costs
        )

        # חשבון "בנק" מכסה את היתרה. הסכום שכבר שולם מהבנק מקוזז כדי לא לספור
        # פעמיים (הכסף כבר ירד מהיתרה).
        bank_balance = _endpoint_balance(accounts, _BANK_ACCOUNT_NAME, "")
        residual = s.residual_from_bank
        remaining_need = max(0.0, residual - exp_paid)
        left_in_bank = bank_balance - remaining_need

        # כרטיסי סיכום
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        def build_card(
            title_text: str,
            value_text: str,
            style: str,
            value_color: Optional[str] = None,
        ) -> None:
            card = QWidget(root)
            card.setObjectName(style)
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                card.setAutoFillBackground(True)
            except Exception:
                pass
            cl = QVBoxLayout(card)
            cl.setContentsMargins(14, 12, 14, 12)
            cl.setSpacing(6)
            t = QLabel(title_text, card)
            t.setObjectName("StatTitle")
            v = QLabel(value_text, card)
            v.setObjectName("StatValueCard")
            if value_color:
                try:
                    v.setStyleSheet(f"color: {value_color};")
                except Exception:
                    pass
            cl.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
            cards_row.addWidget(card, 1)

        build_card("עלות רכישה", _fmt_money(s.acquisition_cost), "StatCardRed")
        build_card("כסף שנשתמש בו", _fmt_money(s.upfront_cash), "StatCardYellow")
        build_card("תשלום חודשי כולל", _fmt_money(s.monthly_total), "StatCardPurple")
        # אדום אם חשבון הבנק לא מספיק לכיסוי היתרה שנותרה (ערך שלילי).
        build_card(
            "יישאר בבנק אחרי הרכישה",
            _fmt_money(left_in_bank),
            "StatCardGreen",
            value_color="#dc2626" if left_in_bank < 0 else None,
        )
        build_card("יחס מימון", f"{s.ltv * 100:.0f}%", "StatCardYellow")
        lay.addLayout(cards_row, 0)

        # ───────── צד ההוצאות (יציאה) — מחיר הדירה + עלויות, בהוספה כמו ההכנסות ─
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
        # שורה 0 = מחיר הדירה; שורות 1..n = עלויות (אינדקס עלות = שורה − 1); ואז סה״כ.
        # (price_paid / exp_paid חושבו למעלה.)
        exp_total = float(m.property_price)
        expenses_table.setRowCount(len(self._one_time_costs) + 2)
        expenses_table.setItem(0, 0, QTableWidgetItem("מחיר הדירה"))
        expenses_table.setItem(0, 1, QTableWidgetItem(_fmt_money(m.property_price)))
        expenses_table.setItem(
            0, 2, QTableWidgetItem(_fmt_money(price_paid) if price_paid else "—")
        )
        for i, c in enumerate(self._one_time_costs):
            planned = float(c.amount)
            paid = cost_paid_amount(c, movements)
            total = planned if planned > 0 else paid
            exp_total += total
            r = i + 1
            expenses_table.setItem(r, 0, QTableWidgetItem(str(c.name)))
            expenses_table.setItem(r, 1, QTableWidgetItem(_fmt_money(total)))
            expenses_table.setItem(
                r, 2, QTableWidgetItem(_fmt_money(paid) if paid else "—")
            )
        trow_e = len(self._one_time_costs) + 1
        expenses_table.setItem(trow_e, 0, QTableWidgetItem("סה״כ"))
        expenses_table.setItem(trow_e, 1, QTableWidgetItem(_fmt_money(exp_total)))
        expenses_table.setItem(trow_e, 2, QTableWidgetItem(_fmt_money(exp_paid)))

        # ───────── צד ההכנסות / מקורות מימון (כניסה) ─────────
        income_card = QWidget(root)
        income_card.setObjectName("AssetTablePanel")
        try:
            income_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            income_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
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
        income_table.setAlternatingRowColors(True)
        try:
            income_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh2 = income_table.horizontalHeader()
            if hh2 is not None:
                hh2.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh2.setObjectName("ActionHistoryHeader")
        except Exception:
            pass
        income_table.doubleClicked.connect(self._on_edit_funding)
        self._funding_table = income_table

        # שורות מקורות המימון (קודם — מתאימות לאינדקסים לעריכה/מחיקה),
        # ואז שורת המשכנתא האוטומטית, ואז סה״כ.
        inc_total = 0.0
        inc_avail = 0.0
        # מקורות מימון (0..n-1) · משכנתא · חשבון בנק (היתרה) · סה״כ
        income_table.setRowCount(len(self._funding_sources) + 3)
        for i, f in enumerate(self._funding_sources):
            avail = funding_available(f, movements, accounts)
            spent = funding_spent(f, movements)
            inc_total += float(f.amount)
            inc_avail += avail
            income_table.setItem(i, 0, QTableWidgetItem(str(f.name)))
            income_table.setItem(
                i, 1, QTableWidgetItem(str(getattr(f.kind, "value", f.kind)))
            )
            income_table.setItem(i, 2, QTableWidgetItem(_fmt_money(f.amount)))
            income_table.setItem(i, 3, QTableWidgetItem(_fmt_money(avail)))
            income_table.setItem(
                i, 4, QTableWidgetItem(_fmt_money(spent) if spent else "—")
            )
        # שורת המשכנתא (= התמהיל שנבנה); הכסף "יוצא" כתשלומי המשכנתא — לא נמדד כאן.
        loan = float(s.tracks_total)
        mrow = len(self._funding_sources)
        inc_total += loan
        inc_avail += loan
        income_table.setItem(mrow, 0, QTableWidgetItem("משכנתא"))
        income_table.setItem(mrow, 1, QTableWidgetItem("מימון"))
        income_table.setItem(mrow, 2, QTableWidgetItem(_fmt_money(loan)))
        income_table.setItem(mrow, 3, QTableWidgetItem(_fmt_money(loan)))
        income_table.setItem(mrow, 4, QTableWidgetItem("—"))
        # שורת חשבון הבנק — מכסה את היתרה:
        #   סכום       = הסכום שצריך לשלם מהבנק (היתרה).
        #   זמין בפועל = הסכום שצריך לשלם פחות מה שכבר שולם (מה שנותר לשלם).
        #   הוצא בפועל = הסכום שכבר שולם בפועל.
        brow = mrow + 1
        inc_total += residual
        inc_avail += remaining_need
        income_table.setItem(brow, 0, QTableWidgetItem(f"חשבון {_BANK_ACCOUNT_NAME}"))
        income_table.setItem(brow, 1, QTableWidgetItem("יתרה"))
        income_table.setItem(brow, 2, QTableWidgetItem(_fmt_money(residual)))
        income_table.setItem(brow, 3, QTableWidgetItem(_fmt_money(remaining_need)))
        income_table.setItem(
            brow,
            4,
            QTableWidgetItem(_fmt_money(exp_paid) if exp_paid else "—"),
        )
        # סה״כ
        trow = brow + 1
        income_table.setItem(trow, 0, QTableWidgetItem("סה״כ"))
        income_table.setItem(trow, 1, QTableWidgetItem(""))
        income_table.setItem(trow, 2, QTableWidgetItem(_fmt_money(inc_total)))
        income_table.setItem(trow, 3, QTableWidgetItem(_fmt_money(inc_avail)))
        income_table.setItem(trow, 4, QTableWidgetItem(""))
        il.addWidget(income_table, 1)

        # ───────── עלויות חודשיות נלוות (מנוהל אינליין כמו השאר) ─────────
        self._monthly_costs = list(m.monthly_costs)
        monthly_card, monthly_table = self._panel_with_actions(
            "עלויות חודשיות נלוות",
            self._on_add_monthly_cost,
            self._on_edit_monthly_cost,
            self._on_remove_monthly_cost,
        )
        self._monthly_table = monthly_table
        monthly_table.setColumnCount(2)
        monthly_table.setHorizontalHeaderLabels(["רכיב", "סכום לחודש"])
        monthly_table.doubleClicked.connect(self._on_edit_monthly_cost)
        monthly_table.setRowCount(len(self._monthly_costs) + 1)
        m_total = 0.0
        for i, c in enumerate(self._monthly_costs):
            m_total += float(c.amount)
            monthly_table.setItem(i, 0, QTableWidgetItem(str(c.name)))
            monthly_table.setItem(i, 1, QTableWidgetItem(_fmt_money(c.amount)))
        monthly_table.setItem(len(self._monthly_costs), 0, QTableWidgetItem("סה״כ"))
        monthly_table.setItem(
            len(self._monthly_costs), 1, QTableWidgetItem(_fmt_money(m_total))
        )

        # ───────── בורר טבלאות — מציגים טבלה אחת בכל פעם ─────────
        self._tab_cards = {
            "expenses": expenses_card,
            "income": income_card,
            "monthly": monthly_card,
        }
        # עוטפים את הבורר ואת הטבלאות באותו מיכל ללא רווח, כך שהכפתור הפעיל
        # והטבלה שמתחתיו נראים על אותו רקע רציף.
        self._tab_buttons = {}
        tabs_wrap = QWidget(root)
        tabs_wrap_l = QVBoxLayout(tabs_wrap)
        tabs_wrap_l.setContentsMargins(0, 0, 0, 0)
        tabs_wrap_l.setSpacing(0)

        tab_bar_w = QWidget(tabs_wrap)
        tab_bar = QHBoxLayout(tab_bar_w)
        tab_bar.setContentsMargins(0, 0, 0, 0)
        tab_bar.setSpacing(4)
        for key, label in (
            ("expenses", "הוצאות"),
            ("income", "הכנסות / מימון"),
            ("monthly", "עלויות חודשיות"),
        ):
            btn = QPushButton(label, tab_bar_w)
            btn.setObjectName("AssetTabButton")
            btn.setCheckable(True)
            try:
                btn.setMinimumHeight(34)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
            except Exception:
                pass
            btn.clicked.connect(lambda _checked=False, k=key: self._show_table(k))
            tab_bar.addWidget(btn)
            self._tab_buttons[key] = btn
        tab_bar.addStretch(1)
        tabs_wrap_l.addWidget(tab_bar_w, 0)

        for card in self._tab_cards.values():
            tabs_wrap_l.addWidget(card, 1)

        lay.addWidget(tabs_wrap, 1)

        if self._active_tab not in self._tab_cards:
            self._active_tab = "expenses"
        self._show_table(self._active_tab)

    def _show_table(self, key: str) -> None:
        """הצג את הטבלה הנבחרת בלבד והדגש את הכפתור המתאים."""
        self._active_tab = key
        for k, card in (self._tab_cards or {}).items():
            try:
                card.setVisible(k == key)
            except Exception:
                pass
        for k, btn in (self._tab_buttons or {}).items():
            try:
                btn.setChecked(k == key)
            except Exception:
                pass

    def _panel_with_actions(
        self, title_text, on_add, on_edit, on_remove
    ) -> tuple[QWidget, QTableWidget]:
        """כרטיס עם כותרת + כפתורי הוסף/ערוך/מחק + טבלה — להוספה אחידה."""
        card = QWidget(self)
        card.setObjectName("AssetTablePanel")
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
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
        header.addWidget(add_b)
        header.addWidget(edit_b)
        header.addWidget(rm_b)
        cl.addLayout(header)
        table = QTableWidget(card)
        table.setObjectName("ActionHistoryTableWidget")
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        try:
            table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh.setObjectName("ActionHistoryHeader")
        except Exception:
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
        self.on_route_activated()

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
        self.on_route_activated()

    def _on_add_monthly_cost(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        dlg = CostItemDialog(show_query=False, parent=self)
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
            cost=self._monthly_costs[idx], show_query=False, parent=self
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_cost()
        if updated is None:
            return
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
        self.on_route_activated()

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
        except Exception:
            pass
        if self._navigate is not None:
            self._navigate("mortgage")

    def _on_edit_purchase(self) -> None:
        m = self._selected_asset()
        if m is None:
            return
        if m.kind != AssetKind.PURCHASE:
            return
        HousePurchaseDialog(
            service=self._service, mortgage_id=m.id, parent=self
        ).exec()
        self.on_route_activated()
