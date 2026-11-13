"""Expense details, with the two explicit "this was expected" decisions:

* "הוצאה צפויה" — this one movement only (not the merchant, not the category):
  no ordinary unusual-expense alert for it. Duplicate-charge checks still run.
* "שיוך להוראת קבע" — link the movement to an existing direct-debit plan's
  scheduled payment. Nothing new is generated and the plan's amount is never
  changed; the charge is then checked against the plan instead of the
  category, and a different amount / date / an extra charge is flagged.

Saving changes only those fields and goes through the normal save + sync.
"""

from __future__ import annotations

from typing import Any, List, Optional

from ..models.bank_movement import BankMovement
from ..qt import QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, Qt
from ..utils.safe import QT_ERRORS
from .dialog_utils import setup_standard_rtl_dialog, wrap_hebrew_rtl


def _fmt(amount: float) -> str:
    a = abs(float(amount))
    return f"{a:,.2f}" if round(a % 1, 2) else f"{a:,.0f}"


class ExpenseDetailsDialog(QDialog):
    def __init__(
        self,
        *,
        movement: BankMovement,
        plans: List[Any],
        movement_service: Any,
        parent: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self._m = movement
        self._service = movement_service
        self._plans = [p for p in plans if getattr(p, "is_direct_debit", False)]
        self.changed: Optional[BankMovement] = None
        lay = setup_standard_rtl_dialog(
            self, title="פרטי הוצאה", margins=(24, 20, 24, 20), spacing=10
        )
        self.setMinimumWidth(520)

        def line(label: str, value: str) -> None:
            row = QHBoxLayout()
            row.setSpacing(10)
            k = QLabel(f"{label}:", self)
            k.setObjectName("Subtitle")
            v = QLabel(wrap_hebrew_rtl(value), self)
            v.setWordWrap(True)
            row.addWidget(k, 0)
            row.addWidget(v, 1)
            lay.addLayout(row)

        from ..widgets.category_combo import category_label

        line("תאריך", str(movement.date))
        line("חשבון", str(movement.account_name))
        line("סכום", f"{_fmt(movement.amount)} ₪")
        line("קטגוריה", category_label(movement.category) or "—")
        line("סוג", str(getattr(movement.type, "value", movement.type)))
        line("תיאור", str(movement.description or ""))

        is_expense = float(movement.amount) < 0 and not movement.counts_as_transfer
        self._expected = QCheckBox("הוצאה צפויה — רק התנועה הזו", self)
        self._expected.setChecked(bool(movement.expected))
        self._expected.setEnabled(is_expense)
        lay.addWidget(self._expected)
        hint = QLabel(
            "לא תופיע עליה התראת ״הוצאה חריגה״. הוצאות אחרות מאותו בית עסק או "
            "מאותה קטגוריה לא מושפעות, ובדיקת חיוב כפול ממשיכה לפעול. אפשר לבטל בכל עת.",
            self,
        )
        hint.setObjectName("Subtitle")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        prow = QHBoxLayout()
        prow.addWidget(QLabel("שיוך להוראת קבע:", self), 0)
        self._plan = QComboBox(self)
        self._plan.addItem("ללא", "")
        for p in self._plans:
            self._plan.addItem(f"{p.name} · {_fmt(p.monthly_amount)} ₪ לחודש", p.id)
        idx = self._plan.findData(str(movement.plan_id or ""))
        if idx < 0 and movement.plan_id:  # linked to a plan that no longer exists
            self._plan.addItem("(הוראה שנמחקה)", str(movement.plan_id))
            idx = self._plan.count() - 1
        self._plan.setCurrentIndex(max(0, idx))
        self._plan.setEnabled(is_expense and bool(self._plans or movement.plan_id))
        prow.addWidget(self._plan, 1)
        lay.addLayout(prow)
        self._placement = QLabel("", self)
        self._placement.setObjectName("Subtitle")
        self._placement.setWordWrap(True)
        lay.addWidget(self._placement)
        self._plan.currentIndexChanged.connect(lambda _i: self._update_placement())
        self._update_placement()

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save = QPushButton("שמור", self)
        save.setObjectName("PrimaryButton")
        cancel = QPushButton("בטל", self)
        save.clicked.connect(self._save)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        lay.addLayout(buttons)

    def _selected_plan(self) -> Optional[Any]:
        pid = self._plan.currentData()
        return next((p for p in self._plans if p.id == pid), None)

    def _update_placement(self) -> None:
        plan = self._selected_plan()
        if plan is None:
            self._placement.setText(
                "השיוך לא יוצר תנועה חדשה ולא משנה את סכום ההוראה."
                if self._plans else "אין הוראות קבע — אפשר ליצור אחת במסך תשלומים."
            )
            return
        from ..models.plan_links import nearest_occurrence
        from datetime import date

        try:
            when = date.fromisoformat(str(self._m.date)[:10])
        except QT_ERRORS:
            when = None
        placed = nearest_occurrence(plan, when) if when else None
        parts: List[str] = []
        if placed is None:
            parts.append("התאריך לא מתאים לאף תשלום בלוח ההוראה — החיוב יסומן לבדיקה.")
        else:
            n, d = placed
            total = int(plan.payments_count or 0)
            where = f"תשלום {n} מתוך {total}" if n <= total else "אחרי סוף ההוראה"
            parts.append(f"{where} · מתוכנן ל־{d.day:02d}/{d.month:02d}/{d.year}.")
        expected = abs(float(plan.monthly_amount or 0))
        if abs(abs(float(self._m.amount)) - expected) > 1.0:
            parts.append(
                f"הסכום הצפוי {_fmt(expected)} ₪, בפועל {_fmt(self._m.amount)} ₪ — "
                "החיוב יסומן לבדיקה (סכום ההוראה לא ישתנה)."
            )
        parts.append("השיוך לא יוצר תנועה חדשה.")
        self._placement.setText(" ".join(parts))

    def _save(self) -> None:
        kwargs: dict = {}
        if bool(self._expected.isChecked()) != bool(self._m.expected):
            kwargs["expected"] = bool(self._expected.isChecked())
        if str(self._plan.currentData() or "") != str(self._m.plan_id or ""):
            kwargs["plan"] = self._selected_plan()  # None → unlink
        if kwargs:
            try:
                self.changed = self._service.update_expectation(self._m.id, **kwargs)
            except QT_ERRORS:
                self.changed = None
        self.accept()


def open_expense_details(movement_id: str, *, parent: Optional[Any] = None) -> bool:
    """Open the details of one movement (current workspace). True when the
    movement's expectation/plan link was changed."""
    from ..data.action_history_provider import JsonFileActionHistoryProvider
    from ..data.bank_movement_provider import JsonFileBankMovementProvider
    from ..data.installment_plan_provider import JsonFileInstallmentPlanProvider
    from ..models.bank_movement_service import BankMovementService

    svc = BankMovementService(JsonFileBankMovementProvider(), JsonFileActionHistoryProvider())
    m = next((x for x in svc.list_movements() if str(x.id) == str(movement_id)), None)
    if m is None:
        return False
    try:
        plans = list(JsonFileInstallmentPlanProvider().list_plans())
    except QT_ERRORS:
        plans = []
    dlg = ExpenseDetailsDialog(movement=m, plans=plans, movement_service=svc, parent=parent)
    try:
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    except QT_ERRORS:
        pass
    dlg.exec()
    return dlg.changed is not None
