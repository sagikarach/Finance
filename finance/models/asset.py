"""Asset domain model (OOP).

The persisted record is :class:`~finance.models.mortgage.Mortgage` (a flat DTO
kept for storage/back-compat). The *domain* objects here wrap that record and
make each asset responsible for its own value/equity, replacing the old
``if kind == AssetKind.OTHER`` branching with polymorphism:

    Asset  (base)
    ├── HeldAsset      — value is the recorded current_value
    └── HousePurchase  — worth its property price, financed by a MortgageLoan
            has-a  MortgageLoan  — the loan (tracks); owns its amortization

Build one with :func:`build_asset`, which picks the subtype from the record's
kind. (A later step will rename the flat record to ``AssetRecord`` and move the
remaining fields onto these objects.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

from .mortgage import AssetKind, CostItem, Mortgage, MortgageTrack

if TYPE_CHECKING:  # annotations only — avoids any runtime import cost/cycle
    from .accounts import MoneyAccount
    from .mortgage import FundingSource
from .mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    cost_paid_amount,
    early_payoff_savings,
    months_after,
    months_between,
    mortgage_outstanding,
    mortgage_total_interest,
    track_schedule,
)


@dataclass(frozen=True)
class TrackStatusRow:
    """One track's current status row — plain data, no UI."""

    name: str
    kind: str
    principal: float
    annual_rate: float
    first_payment: float
    outstanding_now: float


@dataclass(frozen=True)
class LoanStatus:
    """A loan's current snapshot: headline stats + per-track rows."""

    principal: float
    outstanding: float
    monthly_now: float
    total_interest: float
    tracks: List["TrackStatusRow"]
    # ── תוספות תצוגה (התקדמות / פירוק התשלום / עלות כוללת) ──
    interest_now: float = 0.0  # מרכיב הריבית בתשלום הנוכחי
    principal_now: float = 0.0  # מרכיב הקרן בתשלום הנוכחי
    total_cost: float = 0.0  # קרן + סך ריבית לאורך חיי ההלוואה
    pct_paid: float = 0.0  # אחוז הקרן ששולם עד כה (0..1)
    elapsed_months: int = 0  # מספר התשלומים ששולמו
    total_months: int = 0  # אורך ההלוואה (המסלול הארוך ביותר)
    remaining_payments: int = 0  # תשלומים שנותרו
    payoff_year: int = 0  # שנת סיום (0 = לא ידוע)
    payoff_month: int = 0  # חודש סיום (1..12; 0 = לא ידוע)
    dated: bool = False  # קיים תאריך התחלה תקין
    linked_fraction: float = 0.0  # חלק היתרה הצמוד למדד (0..1)
    prepaid: float = 0.0  # סך הפירעונות החלקיים שבוצעו


@dataclass(frozen=True)
class MortgageLoan:
    """The loan financing a house purchase: a mix of tracks. Responsible for its
    own amortization economics (delegates the pure math to ``mortgage_math``)."""

    record: Mortgage

    @property
    def tracks(self) -> List[MortgageTrack]:
        return list(self.record.tracks)

    @property
    def original_principal(self) -> float:
        return float(self.record.original_principal)

    def outstanding(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return float(mortgage_outstanding(self.record, as_of_date, assumptions))

    def total_interest(
        self, *, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
    ) -> float:
        return float(mortgage_total_interest(self.record, assumptions))

    def status(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
        prepaid: float = 0.0,
    ) -> "LoanStatus":
        """Current snapshot of the loan: headline stats plus a per-track row
        (principal, rate, first payment, outstanding now). ``prepaid`` is the
        total of one-time partial payoffs the caller has linked (from real
        movements) — it reduces the balance and shortens term/interest. Pure —
        the page only renders it."""
        start = str(self.record.start_date or "").strip()
        dated = bool(months_after(start, 0) is not None)
        elapsed = months_between(start, as_of_date) if dated else 0
        monthly_now = 0.0
        interest_now = 0.0
        principal_now = 0.0
        linked_out = 0.0
        tracks: List[TrackStatusRow] = []
        for t in self.record.tracks:
            sched = track_schedule(t, assumptions)
            if not sched:
                continue
            idx = min(elapsed, len(sched) - 1)
            payment_now = sched[idx].payment if elapsed < len(sched) else 0.0
            monthly_now += payment_now
            if elapsed < len(sched):  # מסלול פעיל — צבור את פירוק התשלום הנוכחי
                interest_now += float(sched[idx].interest_part)
                principal_now += float(sched[idx].principal_part)
            out_now = (
                sched[elapsed - 1].remaining_balance
                if 0 < elapsed <= len(sched)
                else (float(t.principal) if elapsed <= 0 else 0.0)
            )
            if bool(t.cpi_linked):
                linked_out += float(out_now)
            tracks.append(
                TrackStatusRow(
                    name=str(t.name),
                    kind=str(getattr(t.kind, "value", t.kind)),
                    principal=float(t.principal),
                    annual_rate=float(t.annual_rate),
                    first_payment=float(sched[0].payment),
                    outstanding_now=float(out_now),
                )
            )
        principal = float(self.record.original_principal)
        outstanding = self.outstanding(as_of_date=as_of_date, assumptions=assumptions)
        total_interest = self.total_interest(assumptions=assumptions)
        total_months = max((int(t.term_months) for t in self.record.tracks), default=0)

        # פירעונות חלקיים שקושרו — מקטינים את היתרה ומקצרים את התקופה/הריבית.
        prepaid = max(0.0, float(prepaid))
        if prepaid > 0:
            outstanding = max(0.0, outstanding - prepaid)
            ep = early_payoff_savings(self.record, prepaid, assumptions)
            if ep is not None:
                total_months = int(ep.new_months)
                total_interest = float(ep.new_interest)

        pct_paid = (
            max(0.0, min(1.0, (principal - outstanding) / principal))
            if principal > 0 and dated
            else 0.0
        )
        remaining = max(0, total_months - elapsed) if dated else total_months
        payoff = months_after(start, total_months) if dated else None
        return LoanStatus(
            principal=principal,
            outstanding=outstanding,
            monthly_now=float(monthly_now),
            total_interest=total_interest,
            tracks=tracks,
            interest_now=float(interest_now),
            principal_now=float(principal_now),
            total_cost=principal + total_interest,
            pct_paid=float(pct_paid),
            elapsed_months=int(elapsed),
            total_months=int(total_months),
            remaining_payments=int(remaining),
            payoff_year=int(payoff[0]) if payoff else 0,
            payoff_month=int(payoff[1]) if payoff else 0,
            dated=dated,
            linked_fraction=float(linked_out / outstanding) if outstanding > 0 else 0.0,
            prepaid=prepaid,
        )

    def combined_schedule(
        self, *, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
    ) -> List[tuple]:
        """Merged amortization schedule across all tracks, summed per period:
        rows of (period, payment, principal_part, interest, remaining_balance)."""
        schedules = [track_schedule(t, assumptions) for t in self.record.tracks]
        max_len = max((len(s) for s in schedules), default=0)
        out: List[tuple] = []
        for period in range(1, max_len + 1):
            payment = principal_part = interest = remaining = 0.0
            for sched in schedules:
                if period - 1 < len(sched):
                    row = sched[period - 1]
                    payment += row.payment
                    principal_part += row.principal_part
                    interest += row.interest_part
                    remaining += row.remaining_balance
            out.append((period, payment, principal_part, interest, remaining))
        return out


@dataclass(frozen=True)
class Asset:
    """Base asset. Wraps the stored record and exposes shared identity/state;
    subclasses are responsible for their own value."""

    record: Mortgage

    @property
    def id(self) -> str:
        return str(self.record.id)

    @property
    def name(self) -> str:
        return str(self.record.name)

    @property
    def archived(self) -> bool:
        return bool(self.record.archived)

    @property
    def sold(self) -> bool:
        return bool(self.record.sold)

    @property
    def is_active(self) -> bool:
        return not (self.archived or self.sold)

    def current_value(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        raise NotImplementedError

    def outstanding_debt(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return 0.0

    def standalone_value(self) -> float:
        """Value counted as a self-contained holding (vs. tracked through
        debt/equity). House purchases report 0 here — they are tracked via
        their outstanding debt instead."""
        return 0.0

    def equity(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return self.current_value(
            as_of_date=as_of_date, assumptions=assumptions
        ) - self.outstanding_debt(as_of_date=as_of_date, assumptions=assumptions)


@dataclass(frozen=True)
class HeldAsset(Asset):
    """A plainly-held asset (``kind == OTHER``): worth its recorded value, no debt."""

    def current_value(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return float(self.record.current_value or 0.0)

    def standalone_value(self) -> float:
        return self.current_value()


@dataclass(frozen=True)
class HousePurchase(Asset):
    """A purchased property (``kind == PURCHASE``): worth its property price,
    financed by a mortgage. Owns the purchase economics; defers loan math to
    its :class:`MortgageLoan`."""

    @property
    def mortgage(self) -> MortgageLoan:
        return MortgageLoan(self.record)

    @property
    def property_price(self) -> float:
        return float(self.record.property_price or 0.0)

    def current_value(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return self.property_price

    def outstanding_debt(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return self.mortgage.outstanding(as_of_date=as_of_date, assumptions=assumptions)


@dataclass(frozen=True)
class CarAsset(Asset):
    """A car (``kind == CAR``): worth its manually-maintained ``current_value``
    (there is no reliable auto-source). ``property_price`` holds the original
    purchase price so the UI can show the value it has lost. No debt — a car is
    tracked as an owned, depreciating asset with recurring yearly costs."""

    @property
    def purchase_price(self) -> float:
        return float(self.record.property_price or 0.0)

    @property
    def expense_category(self) -> str:
        return str(getattr(self.record, "expense_category", "") or "").strip() or "רכב"

    def current_value(
        self,
        *,
        as_of_date: Optional[str] = None,
        assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    ) -> float:
        return float(self.record.current_value or 0.0)

    def standalone_value(self) -> float:
        return self.current_value()


@dataclass(frozen=True)
class FundingRow:
    """One row of the purchase funding (income side) table — plain data, no UI.
    ``spent`` is None when there is no actual-spent figure (rendered "—");
    ``is_total`` marks the summary row (spent column rendered blank)."""

    label: str
    kind: str
    amount: float
    available: float
    spent: Optional[float] = None
    is_total: bool = False


def funding_breakdown_rows(
    funding_sources: List[FundingSource],
    movements: list,
    accounts: List[MoneyAccount],
    *,
    tracks_total: float,
    residual: float,
    remaining_need: float,
    exp_paid: float,
    bank_account_name: str = "בנק",
) -> List[FundingRow]:
    """The funding-table rows for a house purchase: one row per funding source,
    then the mortgage (loan), then the bank account covering the residual, then
    a totals row. Pure — the page only renders these."""
    rows: List[FundingRow] = []
    inc_total = 0.0
    inc_avail = 0.0

    for f in funding_sources:
        avail = f.available(movements=movements, accounts=accounts)
        spent = f.spent(movements)
        inc_total += float(f.amount)
        inc_avail += avail
        rows.append(
            FundingRow(
                label=str(f.name),
                kind=str(getattr(f.kind, "value", f.kind)),
                amount=float(f.amount),
                available=float(avail),
                spent=spent,
            )
        )

    loan = float(tracks_total)
    inc_total += loan
    inc_avail += loan
    rows.append(FundingRow("משכנתא", "מימון", loan, loan, spent=None))

    inc_total += float(residual)
    inc_avail += float(remaining_need)
    rows.append(
        FundingRow(
            label=f"חשבון {bank_account_name}",
            kind="יתרה",
            amount=float(residual),
            available=float(remaining_need),
            spent=float(exp_paid),
        )
    )

    rows.append(
        FundingRow("סה״כ", "", float(inc_total), float(inc_avail), is_total=True)
    )
    return rows


@dataclass(frozen=True)
class ExpenseRow:
    """One row of the purchase expense (outgoing) table — plain data, no UI.
    ``is_total`` marks the summary row (its ``paid`` always renders as money,
    while per-item rows render "—" when nothing was paid)."""

    label: str
    amount: float
    paid: float
    is_total: bool = False


def expense_breakdown_rows(
    property_price: float,
    price_paid: float,
    one_time_costs: List[CostItem],
    movements: list,
) -> List[ExpenseRow]:
    """The expense-table rows for a house purchase: the property price, then one
    row per one-time cost (planned amount, or actual-paid when no plan), then a
    totals row. Cost rows keep order 1..n so the page's edit index = row - 1."""
    rows: List[ExpenseRow] = [
        ExpenseRow("מחיר הדירה", float(property_price), float(price_paid))
    ]
    exp_total = float(property_price)
    exp_paid = float(price_paid)
    for c in one_time_costs:
        planned = float(c.amount)
        paid = float(cost_paid_amount(c, movements))
        total = planned if planned > 0 else paid
        exp_total += total
        exp_paid += paid
        rows.append(ExpenseRow(str(c.name), total, paid))
    rows.append(ExpenseRow("סה״כ", exp_total, exp_paid, is_total=True))
    return rows


def build_asset(record: Mortgage) -> Asset:
    """Build the right :class:`Asset` subtype from a stored record's kind."""
    if record.kind == AssetKind.OTHER:
        return HeldAsset(record)
    if record.kind == AssetKind.CAR:
        return CarAsset(record)
    return HousePurchase(record)


def new_asset_record(
    kind: AssetKind,
    *,
    name: str,
    current_value: float = 0.0,
    account_name: str = "בנק",
) -> Mortgage:
    """Build a fresh stored record for a new asset of ``kind``. Centralises the
    per-kind construction that the UI used to branch on."""
    if kind == AssetKind.OTHER:
        return Mortgage(
            name=name, kind=AssetKind.OTHER, current_value=float(current_value or 0.0)
        )
    if kind == AssetKind.CAR:
        # property_price = original purchase price; current_value starts equal
        # (the user maintains it manually thereafter). expense_category drives
        # the average-monthly-cost figure (default: the "רכב" category).
        v = float(current_value or 0.0)
        return Mortgage(
            name=name,
            kind=AssetKind.CAR,
            account_name=account_name,
            property_price=v,
            current_value=v,
            expense_category="רכב",
        )
    return Mortgage(name=name, kind=AssetKind.PURCHASE, account_name=account_name)
