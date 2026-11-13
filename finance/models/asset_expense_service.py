from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from .mortgage_math import (
    average_monthly,
    cost_monthly_average,
    cost_paid_amount,
    query_paid_amount,
    yearly_cost_cycles,
)
from ..utils.safe import PARSE_ERRORS
from .category_tree import active_tree

DEFAULT_CAR_EXPENSE_CATEGORY = "רכב"


def expense_category_names(mortgage: Any) -> List[str]:
    """Movement categories counted for a car's monthly spend: exactly the
    categories selected for it (an older single-category setting is converted
    on read — never every descendant of a broad parent; see ``car_costs``)."""
    from .car_costs import car_category_selection

    return list(car_category_selection(mortgage, active_tree()).categories)


@dataclass(frozen=True)
class ExpenseSummary:
    """A monthly figure and its annual counterpart, with how many months of
    movement data backed the average (0 when derived from typed amounts)."""

    monthly: float
    yearly: float
    months_of_data: int = 0


@dataclass(frozen=True)
class HouseAllIn:
    """The house's total running cost: the mortgage payment (actual, from
    movements) plus the accompanying cost items."""

    house_monthly: float
    mortgage_monthly: float
    total_monthly: float
    total_yearly: float


class AssetExpenseService:
    """Movement-derived expense figures for assets — the house cost list, the
    car's category spend, and the mortgage's *actual* monthly payment.

    Qt-free and dependency-injected: give it anything exposing
    ``list_movements()`` and ``match_movements(mortgage)`` (e.g. a
    ``MortgageService``), so it unit-tests headless.
    """

    def __init__(self, mortgage_service: Any) -> None:
        self._svc = mortgage_service

    def _movements(self) -> List[Any]:
        try:
            return list(self._svc.list_movements())
        except PARSE_ERRORS:
            return []

    # ── house ────────────────────────────────────────────────────────────
    def house_cost_expenses(self, mortgage: Any) -> ExpenseSummary:
        """From the house's own cost items: each monthly item derived from its
        movement search (else its typed amount) + yearly items amortised. The
        monthly figure folds the yearly ones in (÷12); yearly = monthly × 12."""
        movements = self._movements()
        monthly = 0.0
        for c in getattr(mortgage, "monthly_costs", None) or []:
            q = str(getattr(c, "query", "") or "").strip()
            monthly += cost_monthly_average(c, movements) if q else float(c.amount)
        yearly = 0.0
        for c in getattr(mortgage, "yearly_costs", None) or []:
            q = str(getattr(c, "query", "") or "").strip()
            if q:
                cycles = yearly_cost_cycles(c, movements, n_cycles=1)
                yearly += float(cycles[0][1]) if cycles else 0.0
            else:
                yearly += float(getattr(c, "amount", 0.0) or 0.0)
        avg_month = monthly + yearly / 12.0
        return ExpenseSummary(monthly=avg_month, yearly=avg_month * 12.0)

    def mortgage_actual_monthly(self, mortgage: Any) -> float:
        """The mortgage payment as actually paid — matched movements averaged
        over the last 12 months with data. 0 until real payments appear."""
        try:
            paid = self._svc.match_movements(mortgage)
        except PARSE_ERRORS:
            return 0.0
        return average_monthly(paid)[0]

    def house_all_in(self, mortgage: Any) -> HouseAllIn:
        """Mortgage payment (actual) + הוצאות הבית → the total running cost."""
        house = self.house_cost_expenses(mortgage).monthly
        mort = self.mortgage_actual_monthly(mortgage)
        total = house + mort
        return HouseAllIn(
            house_monthly=house,
            mortgage_monthly=mort,
            total_monthly=total,
            total_yearly=total * 12.0,
        )

    def acquisition_paid(self, mortgage: Any) -> float:
        """Total actually paid toward the purchase: matched price payments
        (transfers included, since a down-payment is usually a transfer) plus
        matched one-time costs."""
        movements = self._movements()
        pq = str(getattr(mortgage, "price_query", "") or "").strip()
        price_paid = (
            query_paid_amount(pq, movements, include_transfers=True) if pq else 0.0
        )
        one_time = sum(
            cost_paid_amount(c, movements)
            for c in getattr(mortgage, "one_time_costs", None) or []
        )
        return float(price_paid + one_time)

    def financing_gap(self, mortgage: Any, residual: float) -> float:
        """How much of the bank-financed residual is still unpaid (never < 0)."""
        return max(0.0, float(residual) - self.acquisition_paid(mortgage))

    # ── car ──────────────────────────────────────────────────────────────
    def car_breakdown(self, mortgage: Any):
        """The car's movements by bucket (monthly / yearly item / excluded /
        for review) — the single source for the car's figures and lists."""
        from .car_costs import car_cost_breakdown

        return car_cost_breakdown(mortgage, self._movements(), active_tree())

    def car_expenses(self, mortgage: Any, *, months: int = 12) -> ExpenseSummary:
        """Monthly = the spend in the car's selected categories, EXCLUDING the
        movements a yearly item counts (so they're not double-counted) and the
        movements the user excluded. Yearly = that × 12 PLUS the yearly items
        (each item's latest renewal cycle, or its typed amount)."""
        movements = self._movements()
        yearly_costs = list(getattr(mortgage, "yearly_costs", None) or [])
        from .car_costs import car_cost_breakdown

        breakdown = car_cost_breakdown(mortgage, movements, active_tree())
        recurring, n = average_monthly(breakdown.monthly, months=months)
        yearly_total = 0.0
        for c in yearly_costs:
            q = str(getattr(c, "query", "") or "").strip()
            if q:
                cycles = yearly_cost_cycles(c, movements, n_cycles=1)
                yearly_total += float(cycles[0][1]) if cycles else 0.0
            else:
                yearly_total += float(getattr(c, "amount", 0.0) or 0.0)
        return ExpenseSummary(
            monthly=recurring, yearly=recurring * 12.0 + yearly_total, months_of_data=n
        )
