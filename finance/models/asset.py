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
from typing import List, Optional

from .mortgage import AssetKind, CostItem, Mortgage, MortgageTrack
from .mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    cost_paid_amount,
    mortgage_initial_monthly,
    mortgage_outstanding,
    mortgage_total_interest,
    track_schedule,
)


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

    def initial_monthly(
        self, *, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
    ) -> float:
        return float(mortgage_initial_monthly(self.record, assumptions))

    def total_interest(
        self, *, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
    ) -> float:
        return float(mortgage_total_interest(self.record, assumptions))

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

    def realized_value(self) -> float:
        """Cash realized if the asset was sold, else 0."""
        return float(self.record.sale_price or 0.0) if self.sold else 0.0

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
    return Mortgage(name=name, kind=AssetKind.PURCHASE, account_name=account_name)
