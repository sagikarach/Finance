from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSizePolicy,
    Qt,
)
from ..models.mortgage import AssetKind, Mortgage
from ..models.mortgage_service import MortgageService
from ..models.mortgage_math import (
    cost_paid_amount,
    mortgage_outstanding,
    query_paid_amount,
)
from .mortgage_page import HousePurchaseDialog
from .base_page import BasePage


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


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
        super().__init__(*args, **kwargs)

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

        # כותרת + כפתורי פעולה (חזרה, עריכת רכישה) — אייקונים בלבד.
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
        edit_btn = QToolButton(root)
        edit_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(edit_btn, "edit", size=20, is_dark=self._is_dark_theme())
        except Exception:
            edit_btn.setText("✎")
        edit_btn.setToolTip("ערוך מחיר, הון עצמי ועלויות")
        edit_btn.clicked.connect(self._on_edit_purchase)
        title_row.addWidget(edit_btn)
        lay.addLayout(title_row, 0)

        s = self._service.purchase_summary(m)
        movements = self._service.list_movements()

        # כרטיסי סיכום
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        def build_card(title_text: str, value_text: str, style: str) -> None:
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
            cl.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
            cards_row.addWidget(card, 1)

        build_card("מזומן נדרש לרכישה", _fmt_money(s.upfront_cash), "StatCardYellow")
        build_card("תשלום חודשי כולל", _fmt_money(s.monthly_total), "StatCardGreen")
        build_card("עלות כוללת", _fmt_money(s.total_cost), "StatCardRed")
        build_card("יחס מימון", f"{s.ltv * 100:.0f}%", "StatCardPurple")
        lay.addLayout(cards_row, 0)

        # חלק המשכנתא — לחיץ, פותח את פרטי המשכנתא
        if s.tracks_total > 0:
            mort_text = (
                f"משכנתא: {_fmt_money(s.tracks_total)} ₪ · "
                f"{_fmt_money(s.mortgage_monthly)} ₪/חודש   ›"
            )
        elif s.required_mortgage > 0:
            mort_text = (
                f"משכנתא: בנה תמהיל בסך {_fmt_money(s.required_mortgage)} ₪   ›"
            )
        else:
            mort_text = "משכנתא — פתח פרטים   ›"
        mort_btn = QPushButton(mort_text, root)
        mort_btn.setObjectName("SidebarNavButton")
        mort_btn.setToolTip("פתח את פרטי המשכנתא (תמהיל, לוח סילוקין, תנועות)")
        try:
            mort_btn.setMinimumHeight(48)
            mort_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        mort_btn.clicked.connect(self._open_mortgage)
        lay.addWidget(mort_btn, 0)

        # פירוט התשלומים בתהליך הרכישה
        breakdown_card = QWidget(root)
        breakdown_card.setObjectName("ContentPanel")
        try:
            breakdown_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            breakdown_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        bl = QVBoxLayout(breakdown_card)
        bl.setContentsMargins(16, 16, 16, 16)
        bl.setSpacing(8)
        bl.addWidget(QLabel("תשלומים ברכישה — סכום ושולם בפועל", breakdown_card), 0)

        table = QTableWidget(breakdown_card)
        table.setObjectName("ActionHistoryTableWidget")
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["רכיב", "סכום", "שולם בפועל"])
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

        # כל שורה: (תווית, סכום כולל, שולם בפועל)
        rows: List[tuple[str, float, float]] = []
        equity = float(m.equity)
        # הון עצמי: אם הוגדר חיפוש תנועות — שולם בפועל לפי התנועות (כולל העברות,
        # שכן מקדמה משולמת לרוב כהעברה); אחרת מניחים שההון העצמי שולם.
        eq_query = str(getattr(m, "equity_query", "") or "").strip()
        equity_paid = (
            query_paid_amount(eq_query, movements, include_transfers=True)
            if eq_query
            else equity
        )
        rows.append(("הון עצמי", equity, equity_paid))
        for c in m.one_time_costs:
            planned = float(c.amount)
            paid = cost_paid_amount(c, movements)
            total = planned if planned > 0 else paid
            if str(c.name).strip() or total or paid:
                rows.append((str(c.name), total, paid))
        # מימון: משכנתא — סכום = ההלוואה הדרושה; שולם = קרן שנפרעה עד היום.
        # ללא תאריך התחלה תקין לא ניתן לדעת כמה נפרע, ולכן 0.
        tracks_total = float(m.original_principal)
        repaid = 0.0
        if tracks_total > 0 and str(m.start_date or "").strip():
            repaid = max(0.0, tracks_total - mortgage_outstanding(m, None))
        rows.append(("מימון: משכנתא", float(s.required_mortgage), repaid))

        total_sum = sum(t for _, t, _ in rows)
        paid_sum = sum(p for _, _, p in rows)
        remaining = max(0.0, total_sum - paid_sum)

        table.setRowCount(len(rows) + 2)
        for i, (label, total, paid) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(label))
            table.setItem(i, 1, QTableWidgetItem(_fmt_money(total)))
            table.setItem(i, 2, QTableWidgetItem(_fmt_money(paid) if paid else "—"))
        # שורות סיכום
        table.setItem(len(rows), 0, QTableWidgetItem("סה״כ"))
        table.setItem(len(rows), 1, QTableWidgetItem(_fmt_money(total_sum)))
        table.setItem(len(rows), 2, QTableWidgetItem(_fmt_money(paid_sum)))
        table.setItem(len(rows) + 1, 0, QTableWidgetItem("נותר לתשלום"))
        table.setItem(len(rows) + 1, 1, QTableWidgetItem(""))
        table.setItem(len(rows) + 1, 2, QTableWidgetItem(_fmt_money(remaining)))
        bl.addWidget(table, 1)
        lay.addWidget(breakdown_card, 1)

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
