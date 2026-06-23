from __future__ import annotations

from dataclasses import replace
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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QSizePolicy,
    Qt,
    QDate,
)
from ..models.accounts import MoneyAccount, parse_iso_date
from ..ui.dialog_utils import setup_calendar_popup
from ..models.mortgage import (
    AmortizationType,
    AssetKind,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from ..models.mortgage_service import MortgageService
from ..models.asset import HousePurchase, MortgageLoan, build_asset
from ..models.mortgage_math import (
    purchase_summary,
)
from ..widgets.mortgage_balance_chart import MortgageBalanceChart
from .base_page import BasePage


# חשבון המקור של המשכנתא קבוע — תשלומי המשכנתא תמיד יורדים מחשבון "בנק".
_MORTGAGE_ACCOUNT_NAME = "בנק"


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


def _fmt_rate(value: float) -> str:
    try:
        return f"{float(value):.2f}%"
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


# ─────────────────────────── single-track editor ───────────────────────────


class MortgageTrackDialog(QDialog):
    def __init__(
        self,
        *,
        track: Optional[MortgageTrack] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("מסלול משכנתא")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        self._track: Optional[MortgageTrack] = track

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel("מסלול משכנתא", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם המסלול (לדוגמה: פריים)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._kind = QComboBox(self)
        self._kind.addItems([k.value for k in TrackKind])
        root.addWidget(QLabel("סוג מסלול", self))
        root.addWidget(self._kind)

        self._principal = QLineEdit(self)
        self._principal.setPlaceholderText("קרן (לדוגמה: 400000)")
        root.addWidget(QLabel("קרן", self))
        root.addWidget(self._principal)

        self._annual_rate = QLineEdit(self)
        self._annual_rate.setPlaceholderText("ריבית שנתית באחוזים (לדוגמה: 4.1)")
        root.addWidget(QLabel("ריבית שנתית (%)", self))
        root.addWidget(self._annual_rate)

        self._term = QSpinBox(self)
        self._term.setMinimum(1)
        self._term.setMaximum(600)
        self._term.setValue(240)
        root.addWidget(QLabel("מספר חודשים", self))
        root.addWidget(self._term)

        self._amortization = QComboBox(self)
        self._amortization.addItems([a.value for a in AmortizationType])
        root.addWidget(QLabel("שיטת החזר", self))
        root.addWidget(self._amortization)

        self._cpi_linked = QCheckBox("צמוד למדד", self)
        root.addWidget(self._cpi_linked)

        self._prime_spread = QLineEdit(self)
        self._prime_spread.setPlaceholderText("מרווח מהפריים (לדוגמה: -0.5)")
        root.addWidget(QLabel("מרווח פריים (P + ערך)", self))
        root.addWidget(self._prime_spread)

        self._reset = QSpinBox(self)
        self._reset.setMinimum(0)
        self._reset.setMaximum(600)
        self._reset.setValue(0)
        root.addWidget(QLabel("תקופת עדכון ריבית (חודשים, 0 = ללא)", self))
        root.addWidget(self._reset)

        self._kind.currentTextChanged.connect(self._on_kind_changed)

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

    def _on_kind_changed(self, text: str) -> None:
        is_prime = str(text) == TrackKind.PRIME.value
        # מרווח הפריים רלוונטי רק למסלול פריים; הריבית הקבועה לשאר המסלולים.
        self._prime_spread.setEnabled(is_prime)
        self._annual_rate.setEnabled(not is_prime)

    def _load_initial(self) -> None:
        t = self._track
        if t is None:
            return
        self._name.setText(str(t.name or ""))
        try:
            self._kind.setCurrentText(str(getattr(t.kind, "value", t.kind)))
        except Exception:
            pass
        self._principal.setText(str(float(t.principal)))
        self._annual_rate.setText(str(float(t.annual_rate)))
        self._term.setValue(max(1, int(t.term_months)))
        try:
            self._amortization.setCurrentText(
                str(getattr(t.amortization, "value", t.amortization))
            )
        except Exception:
            pass
        self._cpi_linked.setChecked(bool(t.cpi_linked))
        self._prime_spread.setText(str(float(t.prime_spread)))
        self._reset.setValue(max(0, int(t.reset_months)))

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "שם המסלול לא יכול להיות ריק")
            return
        try:
            kind = TrackKind(str(self._kind.currentText()))
        except Exception:
            kind = TrackKind.FIXED_UNLINKED
        principal = _parse_float(self._principal.text())
        if principal is None or principal <= 0:
            QMessageBox.warning(self, "שגיאה", "קרן חייבת להיות מספר חיובי")
            return
        annual_rate = _parse_float(self._annual_rate.text()) or 0.0
        prime_spread = _parse_float(self._prime_spread.text()) or 0.0
        try:
            amortization = AmortizationType(str(self._amortization.currentText()))
        except Exception:
            amortization = AmortizationType.SPITZER

        existing_id = self._track.id if self._track is not None else None
        self._track = MortgageTrack(
            **({"id": existing_id} if existing_id else {}),
            name=name,
            kind=kind,
            principal=float(principal),
            annual_rate=float(annual_rate),
            term_months=int(self._term.value()),
            amortization=amortization,
            cpi_linked=bool(self._cpi_linked.isChecked()),
            prime_spread=float(prime_spread),
            reset_months=int(self._reset.value()),
        )
        self.accept()

    def get_track(self) -> Optional[MortgageTrack]:
        return self._track


# ─────────────────────────── full mortgage editor ───────────────────────────


class MortgageDialog(QDialog):
    def __init__(
        self,
        *,
        accounts: List[MoneyAccount],
        mortgage: Optional[Mortgage] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("משכנתא")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            self.resize(560, 560)
        except Exception:
            pass

        self._mortgage: Optional[Mortgage] = mortgage
        self._tracks: List[MortgageTrack] = (
            list(mortgage.tracks) if mortgage is not None else []
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel("משכנתא", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם (לדוגמה: דירה ברחוב הרצל)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        # חשבון המקור קבוע ל-"בנק" — מוצג לקריאה בלבד.
        account_label = QLabel(
            f"חשבון מקור (לשיוך תנועות): {_MORTGAGE_ACCOUNT_NAME}", self
        )
        root.addWidget(account_label)

        self._vendor_query = QLineEdit(self)
        self._vendor_query.setPlaceholderText("טקסט לזיהוי תנועות (מופיע בתיאור)")
        root.addWidget(QLabel("חיפוש תנועות", self))
        root.addWidget(self._vendor_query)

        self._start_date = QDateEdit(self)
        self._start_date.setCalendarPopup(True)
        setup_calendar_popup(self._start_date)
        try:
            self._start_date.setDisplayFormat("yyyy-MM-dd")
        except Exception:
            pass
        root.addWidget(QLabel("תאריך התחלה", self))
        root.addWidget(self._start_date)

        tracks_header = QHBoxLayout()
        tracks_header.addWidget(QLabel("מסלולים (אפשר לבנות בהמשך)", self), 0)
        tracks_header.addStretch(1)
        add_track_btn = QToolButton(self)
        add_track_btn.setText("➕")
        add_track_btn.setToolTip("הוסף מסלול")
        add_track_btn.clicked.connect(self._on_add_track)
        edit_track_btn = QToolButton(self)
        edit_track_btn.setText("✎")
        edit_track_btn.setToolTip("ערוך מסלול")
        edit_track_btn.clicked.connect(self._on_edit_track)
        remove_track_btn = QToolButton(self)
        remove_track_btn.setText("🗑")
        remove_track_btn.setToolTip("מחק מסלול")
        remove_track_btn.clicked.connect(self._on_remove_track)
        tracks_header.addWidget(add_track_btn)
        tracks_header.addWidget(edit_track_btn)
        tracks_header.addWidget(remove_track_btn)
        root.addLayout(tracks_header)

        self._tracks_table = QTableWidget(self)
        self._tracks_table.setColumnCount(5)
        self._tracks_table.setHorizontalHeaderLabels(
            ["שם", "סוג", "קרן", "ריבית", "חודשים"]
        )
        self._tracks_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._tracks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tracks_table.setAlternatingRowColors(True)
        try:
            self._tracks_table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = self._tracks_table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass
        self._tracks_table.doubleClicked.connect(self._on_edit_track)
        root.addWidget(self._tracks_table, 1)

        self._total_label = QLabel("", self)
        root.addWidget(self._total_label)

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
        self._refresh_tracks_table()

    def _load_initial(self) -> None:
        m = self._mortgage
        if m is None:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
                pass
            return
        self._name.setText(str(m.name or ""))
        self._vendor_query.setText(str(m.vendor_query or ""))
        try:
            dt = parse_iso_date(str(m.start_date or ""))
            self._start_date.setDate(QDate(dt.year, dt.month, dt.day))
        except Exception:
            try:
                self._start_date.setDate(QDate.currentDate())
            except Exception:
                pass

    def _refresh_tracks_table(self) -> None:
        tbl = self._tracks_table
        tbl.setRowCount(len(self._tracks))
        for row, t in enumerate(self._tracks):
            tbl.setItem(row, 0, QTableWidgetItem(str(t.name)))
            tbl.setItem(
                row, 1, QTableWidgetItem(str(getattr(t.kind, "value", t.kind)))
            )
            tbl.setItem(row, 2, QTableWidgetItem(_fmt_money(t.principal)))
            tbl.setItem(row, 3, QTableWidgetItem(_fmt_rate(t.annual_rate)))
            tbl.setItem(row, 4, QTableWidgetItem(str(int(t.term_months))))
        total = sum(float(t.principal) for t in self._tracks)
        self._total_label.setText(f"סך הקרן: {_fmt_money(total)} ₪")

    def _selected_track_row(self) -> int:
        try:
            return int(self._tracks_table.currentRow())
        except Exception:
            return -1

    def _on_add_track(self) -> None:
        dlg = MortgageTrackDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        track = dlg.get_track()
        if track is not None:
            self._tracks.append(track)
            self._refresh_tracks_table()

    def _on_edit_track(self) -> None:
        row = self._selected_track_row()
        if row < 0 or row >= len(self._tracks):
            QMessageBox.information(self, "עריכה", "בחר מסלול לעריכה")
            return
        dlg = MortgageTrackDialog(track=self._tracks[row], parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        track = dlg.get_track()
        if track is not None:
            self._tracks[row] = track
            self._refresh_tracks_table()

    def _on_remove_track(self) -> None:
        row = self._selected_track_row()
        if row < 0 or row >= len(self._tracks):
            QMessageBox.information(self, "מחיקה", "בחר מסלול למחיקה")
            return
        del self._tracks[row]
        self._refresh_tracks_table()

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "שם המשכנתא לא יכול להיות ריק")
            return
        # המסלולים (תמהיל) אינם חובה — אפשר לתכנן רכישה תחילה ולבנות אותם בהמשך.
        start_date = ""
        try:
            start_date = self._start_date.date().toString("yyyy-MM-dd")
        except Exception:
            start_date = ""

        prev = self._mortgage
        existing_id = prev.id if prev is not None else None
        excluded = list(prev.excluded_movement_ids) if prev is not None else []
        archived = bool(prev.archived) if prev is not None else False
        # שמור את נתוני תרחיש הרכישה (אם קיימים) — נערכים בדיאלוג נפרד.
        property_price = float(prev.property_price) if prev is not None else 0.0
        price_query = str(prev.price_query) if prev is not None else ""
        one_time_costs = list(prev.one_time_costs) if prev is not None else []
        monthly_costs = list(prev.monthly_costs) if prev is not None else []
        funding_sources = list(prev.funding_sources) if prev is not None else []
        # נכס שנוצר/נערך במסך המשכנתא הוא תמיד מסוג רכישה.
        kind = prev.kind if prev is not None else AssetKind.PURCHASE
        current_value = float(prev.current_value) if prev is not None else 0.0
        # מצב המכירה נשמר מהרשומה הקודמת — עריכת המשכנתא אינה משנה אותו.
        sold = bool(prev.sold) if prev is not None else False
        sale_price = float(prev.sale_price) if prev is not None else 0.0
        sale_date = str(prev.sale_date) if prev is not None else ""
        self._mortgage = Mortgage(
            **({"id": existing_id} if existing_id else {}),
            name=name,
            account_name=_MORTGAGE_ACCOUNT_NAME,
            vendor_query=str(self._vendor_query.text() or "").strip(),
            start_date=start_date,
            tracks=list(self._tracks),
            excluded_movement_ids=excluded,
            archived=archived,
            property_price=property_price,
            price_query=price_query,
            one_time_costs=one_time_costs,
            monthly_costs=monthly_costs,
            funding_sources=funding_sources,
            kind=kind,
            current_value=current_value,
            sold=sold,
            sale_price=sale_price,
            sale_date=sale_date,
        )
        self.accept()

    def get_mortgage(self) -> Optional[Mortgage]:
        return self._mortgage


# ─────────────────────────── schedule viewer ───────────────────────────


class MortgageScheduleDialog(QDialog):
    def __init__(self, mortgage: Mortgage, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"לוח סילוקין — {mortgage.name}")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.resize(640, 620)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        table = QTableWidget(self)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["חודש", "תשלום", "קרן", "ריבית", "יתרה"]
        )
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        try:
            table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass

        rows = MortgageLoan(mortgage).combined_schedule()
        table.setRowCount(len(rows))
        for i, (period, payment, principal_part, interest, remaining) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(str(period)))
            table.setItem(i, 1, QTableWidgetItem(_fmt_money(payment)))
            table.setItem(i, 2, QTableWidgetItem(_fmt_money(principal_part)))
            table.setItem(i, 3, QTableWidgetItem(_fmt_money(interest)))
            table.setItem(i, 4, QTableWidgetItem(_fmt_money(remaining)))
        root.addWidget(table, 1)

        close_btn = QPushButton("סגור", self)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignHCenter)


class MortgagePaymentsDialog(QDialog):
    """תנועות בנק אמיתיות המשויכות למשכנתא, עם אפשרות החרגה."""

    def __init__(
        self,
        *,
        service: MortgageService,
        mortgage_id: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("תנועות משויכות")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.resize(620, 560)
        except Exception:
            pass

        self._service = service
        self._mortgage_id = str(mortgage_id or "").strip()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        self._summary = QLabel("", self)
        self._summary.setObjectName("StatTitle")
        root.addWidget(self._summary)

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["תאריך", "תיאור", "הוצאה", "הכנסה"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = self._table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass
        root.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        exclude_btn = QPushButton("החרג תנועה", self)
        exclude_btn.clicked.connect(self._on_exclude)
        close_btn = QPushButton("סגור", self)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(exclude_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._reload()

    def _current_mortgage(self) -> Optional[Mortgage]:
        for m in self._service.list_mortgages():
            if m.id == self._mortgage_id:
                return m
        return None

    def _reload(self) -> None:
        m = self._current_mortgage()
        if m is None:
            self._table.setRowCount(0)
            self._summary.setText("")
            return
        expenses = self._service.match_movements(m)
        incomes = self._service.match_income(m)
        total_paid = sum(abs(float(x.amount)) for x in expenses)
        total_in = sum(abs(float(x.amount)) for x in incomes)
        self._summary.setText(
            f"הוצאות: {len(expenses)} ({_fmt_money(total_paid)} ₪)   |   "
            f"הכנסות: {len(incomes)} ({_fmt_money(total_in)} ₪)"
        )
        # מיזוג ומיון לפי תאריך; הוצאות בעמודה אחת, הכנסות באחרת.
        from ..models.accounts import parse_iso_date

        rows = [(mv, False) for mv in expenses] + [(mv, True) for mv in incomes]
        rows.sort(key=lambda r: parse_iso_date(str(getattr(r[0], "date", "") or "")))
        self._table.setRowCount(len(rows))
        for row, (mv, is_income) in enumerate(rows):
            self._table.setItem(row, 0, QTableWidgetItem(str(mv.date)))
            self._table.setItem(row, 1, QTableWidgetItem(str(mv.description or "")))
            amt = _fmt_money(abs(float(mv.amount)))
            self._table.setItem(row, 2, QTableWidgetItem("" if is_income else amt))
            self._table.setItem(row, 3, QTableWidgetItem(amt if is_income else ""))
            try:
                for col in range(4):
                    it = self._table.item(row, col)
                    if it is not None:
                        it.setData(Qt.ItemDataRole.UserRole, str(mv.id))
            except Exception:
                pass

    def _selected_movement_id(self) -> Optional[str]:
        try:
            row = self._table.currentRow()
            if row < 0:
                return None
            item = self._table.item(row, 0)
            if item is None:
                return None
            mid = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
            return mid or None
        except Exception:
            return None

    def _on_exclude(self) -> None:
        mid = self._selected_movement_id()
        if not mid:
            QMessageBox.information(self, "החרגה", "בחר תנועה להחרגה")
            return
        self._service.exclude_movement(mortgage_id=self._mortgage_id, movement_id=mid)
        self._reload()


class HousePurchaseDialog(QDialog):
    """תרחיש רכישת דירה — מזומן נדרש, תשלום חודשי כולל, ועלות כוללת."""

    def __init__(
        self,
        *,
        service: MortgageService,
        mortgage_id: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("רכישת דירה")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self.resize(620, 680)
        except Exception:
            pass

        self._service = service
        self._mortgage_id = str(mortgage_id or "").strip()
        self._loading = True
        # תנועות בנק לשיוך עלויות (נטען פעם אחת).
        self._movements = service.list_movements()

        m = self._current_mortgage()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        title = QLabel("תרחיש רכישת דירה", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        # מחיר הדירה. ההון העצמי מנוהל כעת דרך "מקורות מימון" בעמוד הנכס,
        # והמשכנתא = עלות הרכישה − סך מקורות המימון.
        pe_row = QHBoxLayout()
        pe_row.setSpacing(8)
        self._price = QLineEdit(self)
        self._price.setPlaceholderText("מחיר הדירה")
        pe_row.addWidget(QLabel("מחיר דירה:", self))
        pe_row.addWidget(self._price, 1)
        root.addLayout(pe_row)

        # שיוך תנועות לתשלום מחיר הדירה (התשלום למוכר — לרוב העברה).
        pq_row = QHBoxLayout()
        pq_row.setSpacing(8)
        self._price_query = QLineEdit(self)
        self._price_query.setPlaceholderText("חיפוש תנועות לתשלום הדירה (אופציונלי)")
        pq_row.addWidget(QLabel("חיפוש תנועות (מחיר הדירה):", self))
        pq_row.addWidget(self._price_query, 1)
        root.addLayout(pq_row)

        hint = QLabel(
            "הון עצמי, מקורות מימון, הוצאות חד-פעמיות ועלויות חודשיות "
            "מנוהלים בעמוד הנכס.",
            self,
        )
        try:
            hint.setWordWrap(True)
        except Exception:
            pass
        root.addWidget(hint)
        root.addStretch(1)

        # סיכום
        self._summary = QLabel("", self)
        try:
            self._summary.setWordWrap(True)
            self._summary.setTextFormat(Qt.TextFormat.RichText)
        except Exception:
            pass
        root.addWidget(self._summary)

        buttons = QHBoxLayout()
        save_btn = QPushButton("שמור", self)
        save_btn.clicked.connect(self._on_save)
        close_btn = QPushButton("סגור", self)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(save_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._load_initial(m)
        self._loading = False
        self._recompute()

        # רענון חי של הסיכום.
        self._price.textChanged.connect(self._recompute)
        self._price_query.textChanged.connect(self._recompute)

    def _current_mortgage(self) -> Optional[Mortgage]:
        for m in self._service.list_mortgages():
            if m.id == self._mortgage_id:
                return m
        return None

    def _load_initial(self, m: Optional[Mortgage]) -> None:
        if m is None:
            return
        if m.property_price:
            self._price.setText(f"{float(m.property_price):.0f}")
        self._price_query.setText(str(getattr(m, "price_query", "") or ""))

    def _build_mortgage_from_inputs(self) -> Optional[Mortgage]:
        # רק מחיר הדירה ושיוך התנועות שלו נערכים כאן; כל השאר בעמוד הנכס.
        base = self._current_mortgage()
        if base is None:
            return None
        return replace(
            base,
            property_price=_parse_float(self._price.text()) or 0.0,
            price_query=str(self._price_query.text() or "").strip(),
        )

    def _recompute(self) -> None:
        if self._loading:
            return
        m = self._build_mortgage_from_inputs()
        if m is None:
            self._summary.setText("")
            return

        s = purchase_summary(m, movements=self._movements)
        ltv_txt = f"{s.ltv * 100:.0f}%"
        if s.ltv_exceeds_75:
            ltv_txt = f'<span style="color:#dc2626">{ltv_txt} (מעל 75%!)</span>'
        note = ""
        if s.tracks_total == 0:
            note = (
                '<br><span style="color:#2563eb">עדיין לא נבנה תמהיל — '
                "בנה מסלולים בכפתור ✎ במסך המשכנתא.</span>"
            )
        self._summary.setText(
            f"<b>עלות רכישה:</b> {_fmt_money(s.acquisition_cost)} ₪ "
            f"(מחיר {_fmt_money(s.property_price)} + עלויות {_fmt_money(s.one_time_total)})<br>"
            f"<b>משכנתא (תמהיל):</b> {_fmt_money(s.tracks_total)} ₪ "
            f"(יחס מימון {ltv_txt}){note}<br>"
            f"<b>תשלום חודשי כולל:</b> {_fmt_money(s.monthly_total)} ₪ "
            f"(משכנתא {_fmt_money(s.mortgage_monthly)} + נלוות {_fmt_money(s.monthly_costs_total)})"
        )

    def _on_save(self) -> None:
        m = self._build_mortgage_from_inputs()
        if m is None:
            self.reject()
            return
        self._service.upsert_mortgage(m)
        self.accept()


# ─────────────────────────── page ───────────────────────────


class MortgagePage(BasePage):
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
        kwargs.setdefault("page_title", "משכנתא")
        kwargs.setdefault("current_route", "mortgage")
        self._service = MortgageService()
        self._mortgages: List[Mortgage] = []
        self._selected_id: Optional[str] = None

        self._selector: Optional[QComboBox] = None
        self._edit_btn: Optional[QToolButton] = None
        self._schedule_btn: Optional[QToolButton] = None
        self._payments_btn: Optional[QToolButton] = None
        self._table: Optional[QTableWidget] = None
        self._chart: Optional[MortgageBalanceChart] = None
        self._card_principal: Optional[QLabel] = None
        self._card_outstanding: Optional[QLabel] = None
        self._card_payment: Optional[QLabel] = None
        self._card_interest: Optional[QLabel] = None

        super().__init__(*args, **kwargs)

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._load_and_refresh_accounts()
        # נכס שנבחר מרשימת הנכסים — בחר אותו כברירת מחדל.
        try:
            sel = self._app_context.get("selected_mortgage_id")
            if isinstance(sel, str) and sel.strip():
                self._selected_id = sel.strip()
        except Exception:
            pass
        self._reload()

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if self._chart is not None:
            try:
                self._chart.refresh_theme()
            except Exception:
                pass

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

        # Header card: selector + actions.
        header_card = QWidget(root)
        header_card.setObjectName("Sidebar")
        try:
            header_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_row = QHBoxLayout(header_card)
        header_row.setContentsMargins(16, 12, 16, 12)
        header_row.setSpacing(8)

        back_btn = QToolButton(header_card)
        back_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(back_btn, "arrow_left", size=20, is_dark=self._is_dark_theme())
        except Exception:
            back_btn.setText("←")
        back_btn.setToolTip("חזרה לעמוד הנכס")
        if self._navigate is not None:
            back_btn.clicked.connect(lambda: self._navigate("asset"))
        header_row.addWidget(back_btn, 0)

        self._selector = QComboBox(header_card)
        self._selector.setMinimumWidth(220)
        self._selector.currentIndexChanged.connect(self._on_selection_changed)
        header_row.addWidget(self._selector, 0)
        header_row.addStretch(1)

        # יצירת נכס חדש מתבצעת רק בעמוד "נכסים" — כאן רק עורכים נכס קיים.
        self._edit_btn = QToolButton(header_card)
        self._edit_btn.setObjectName("IconButton")
        self._edit_btn.setText("✎")
        self._edit_btn.setToolTip("ערוך משכנתא")
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        header_row.addWidget(self._edit_btn)

        delete_btn = QToolButton(header_card)
        delete_btn.setObjectName("IconButton")
        delete_btn.setText("🗑")
        delete_btn.setToolTip("מחק משכנתא")
        delete_btn.clicked.connect(self._on_delete_clicked)
        header_row.addWidget(delete_btn)

        self._schedule_btn = QToolButton(header_card)
        self._schedule_btn.setObjectName("IconButton")
        self._schedule_btn.setText("📋")
        self._schedule_btn.setToolTip("לוח סילוקין")
        self._schedule_btn.clicked.connect(self._on_show_schedule)
        header_row.addWidget(self._schedule_btn)

        self._payments_btn = QToolButton(header_card)
        self._payments_btn.setObjectName("IconButton")
        self._payments_btn.setText("💳")
        self._payments_btn.setToolTip("תנועות משויכות")
        self._payments_btn.clicked.connect(self._on_show_payments)
        header_row.addWidget(self._payments_btn)

        lay.addWidget(header_card, 0)

        # Stat cards row.
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        def build_card(title_text: str, style: str) -> QLabel:
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
            v = QLabel("", card)
            v.setObjectName("StatValueCard")
            cl.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
            cards_row.addWidget(card, 1)
            return v

        self._card_principal = build_card("סך הקרן", "StatCardPurple")
        self._card_outstanding = build_card("יתרה נוכחית", "StatCardYellow")
        self._card_payment = build_card("תשלום חודשי", "StatCardGreen")
        self._card_interest = build_card("סך ריבית צפויה", "StatCardRed")
        lay.addLayout(cards_row, 0)

        # Bottom row: balance-decline chart (left) + tracks table (right).
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        chart_card = QWidget(root)
        chart_card.setObjectName("ContentPanel")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            chart_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        chart_card_l = QVBoxLayout(chart_card)
        chart_card_l.setContentsMargins(8, 8, 8, 8)
        chart_card_l.setSpacing(0)
        chart_title = QLabel("יתרת קרן לאורך זמן", chart_card)
        chart_title.setObjectName("StatTitle")
        chart_card_l.addWidget(chart_title, 0)
        self._chart = MortgageBalanceChart(parent=chart_card)
        chart_card_l.addWidget(self._chart, 1)

        # Tracks summary table.
        table_card = QWidget(root)
        table_card.setObjectName("ContentPanel")
        try:
            table_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        table_card_l = QVBoxLayout(table_card)
        table_card_l.setContentsMargins(16, 16, 16, 16)
        table_card_l.setSpacing(8)

        self._table = QTableWidget(table_card)
        self._table.setObjectName("ActionHistoryTableWidget")
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["מסלול", "סוג", "קרן", "ריבית", "תשלום חודשי", "יתרה"]
        )
        self._table.setRowCount(0)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = self._table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh.setObjectName("ActionHistoryHeader")
        except Exception:
            pass
        table_card_l.addWidget(self._table, 1)

        bottom_row.addWidget(chart_card, 2)
        bottom_row.addWidget(table_card, 1)
        lay.addLayout(bottom_row, 1)

        self._reload()

    def _reload(self) -> None:
        try:
            # מסך זה מציג רק נכסי רכישה (משכנתא); נכסי "אחר" מנוהלים ברשימת הנכסים.
            self._mortgages = [
                m
                for m in self._service.list_mortgages()
                if isinstance(build_asset(m), HousePurchase)
            ]
        except Exception:
            self._mortgages = []
        if self._selected_id and not any(
            m.id == self._selected_id for m in self._mortgages
        ):
            self._selected_id = None
        if self._selected_id is None and self._mortgages:
            self._selected_id = self._mortgages[0].id

        if self._selector is not None:
            self._selector.blockSignals(True)
            self._selector.clear()
            for m in self._mortgages:
                label = m.name or "(ללא שם)"
                if bool(getattr(m, "archived", False)):
                    label = f"{label} (ארכיון)"
                self._selector.addItem(label, m.id)
            # restore selection
            idx = 0
            for i, m in enumerate(self._mortgages):
                if m.id == self._selected_id:
                    idx = i
                    break
            if self._mortgages:
                self._selector.setCurrentIndex(idx)
            self._selector.blockSignals(False)

        self._refresh_details()

    def _selected_mortgage(self) -> Optional[Mortgage]:
        mid = str(self._selected_id or "").strip()
        if not mid:
            return None
        for m in self._mortgages:
            if m.id == mid:
                return m
        return None

    def _refresh_details(self) -> None:
        m = self._selected_mortgage()
        has_sel = m is not None
        if self._edit_btn is not None:
            self._edit_btn.setEnabled(has_sel)
        if self._schedule_btn is not None:
            self._schedule_btn.setEnabled(has_sel)
        if self._payments_btn is not None:
            self._payments_btn.setEnabled(has_sel)

        if not has_sel or self._table is None:
            if self._table is not None:
                self._table.setRowCount(0)
            for card in (
                self._card_principal,
                self._card_outstanding,
                self._card_payment,
                self._card_interest,
            ):
                if card is not None:
                    card.setText("")
            if self._chart is not None:
                self._chart.set_mortgage(None)
            return

        assert m is not None
        # MortgageLoan.status owns the per-track computation; here we only render.
        st = MortgageLoan(m).status()

        if self._card_principal is not None:
            self._card_principal.setText(_fmt_money(st.principal))
        if self._card_outstanding is not None:
            self._card_outstanding.setText(_fmt_money(st.outstanding))
        if self._card_payment is not None:
            self._card_payment.setText(_fmt_money(st.monthly_now))
        if self._card_interest is not None:
            self._card_interest.setText(_fmt_money(st.total_interest))

        self._table.setRowCount(len(st.tracks))
        for row, tr in enumerate(st.tracks):
            self._table.setItem(row, 0, QTableWidgetItem(tr.name))
            self._table.setItem(row, 1, QTableWidgetItem(tr.kind))
            self._table.setItem(row, 2, QTableWidgetItem(_fmt_money(tr.principal)))
            self._table.setItem(row, 3, QTableWidgetItem(_fmt_rate(tr.annual_rate)))
            self._table.setItem(row, 4, QTableWidgetItem(_fmt_money(tr.first_payment)))
            self._table.setItem(
                row, 5, QTableWidgetItem(_fmt_money(tr.outstanding_now))
            )

        if self._chart is not None:
            self._chart.set_mortgage(m)

    def _on_selection_changed(self, index: int) -> None:
        if self._selector is None:
            return
        try:
            data = self._selector.itemData(index)
            self._selected_id = str(data or "").strip() or None
        except Exception:
            self._selected_id = None
        self._refresh_details()

    def _on_edit_clicked(self) -> None:
        m = self._selected_mortgage()
        if m is None:
            QMessageBox.information(self, "עריכה", "בחר משכנתא לעריכה")
            return
        dlg = MortgageDialog(accounts=self._accounts, mortgage=m, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dlg.get_mortgage()
        if updated is None:
            return
        self._service.upsert_mortgage(updated)
        self._selected_id = updated.id
        self._reload()

    def _on_delete_clicked(self) -> None:
        m = self._selected_mortgage()
        if m is None:
            QMessageBox.information(self, "מחיקה", "בחר משכנתא למחיקה")
            return
        res = QMessageBox.question(
            self,
            "מחיקה",
            f'למחוק את "{m.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        self._service.delete_mortgage(m.id)
        self._selected_id = None
        self._reload()

    def _on_show_schedule(self) -> None:
        m = self._selected_mortgage()
        if m is None:
            QMessageBox.information(self, "לוח סילוקין", "בחר משכנתא")
            return
        if not m.tracks:
            QMessageBox.information(self, "לוח סילוקין", "אין מסלולים להצגה")
            return
        MortgageScheduleDialog(m, parent=self).exec()

    def _on_show_payments(self) -> None:
        m = self._selected_mortgage()
        if m is None:
            QMessageBox.information(self, "תנועות", "בחר משכנתא")
            return
        MortgagePaymentsDialog(
            service=self._service, mortgage_id=m.id, parent=self
        ).exec()
        # ההחרגות עשויות להשתנות — רענן את הבחירה.
        self._reload()
