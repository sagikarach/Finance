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

from .mortgage import AssetKind, Mortgage, MortgageTrack
from .mortgage_math import (
    DEFAULT_ASSUMPTIONS,
    MortgageAssumptions,
    mortgage_initial_monthly,
    mortgage_outstanding,
    mortgage_total_interest,
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
