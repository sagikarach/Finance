from __future__ import annotations

from datetime import date
from typing import Dict

from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..models.accounts_service import AccountsService
from ..models.overview import AccountsOverview
from ..models.dashboard_meta import DashboardMeta


def _month_key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


def _shift_month(base: date, delta_months: int) -> tuple[int, int]:
    y = int(base.year)
    m0 = int(base.month) - 1
    n = y * 12 + m0 + int(delta_months)
    ny = n // 12
    nm0 = n % 12
    return int(ny), int(nm0 + 1)


class DashboardMetaService:
    def __init__(
        self,
        *,
        accounts_provider: AccountsProvider | None = None,
        movement_provider: BankMovementProvider | None = None,
    ) -> None:
        self._accounts_provider = accounts_provider or JsonFileAccountsProvider()
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._accounts_service = AccountsService(self._accounts_provider)

    def compute(self) -> DashboardMeta:
        accounts = self._accounts_service.load_accounts()
        overview = AccountsOverview.for_home(accounts)

        try:
            movements = list(self._movement_provider.list_movements())
        except Exception:
            movements = []

        today = date.today()
        # Requirement: exclude current month + previous month (2 months),
        # then average exactly 6 months back from there (including the anchor month).
        anchor_y, anchor_m = _shift_month(today, -2)
        months = [
            _month_key(*_shift_month(date(anchor_y, anchor_m, 1), -i)) for i in range(6)
        ]

        income_by_month: Dict[str, float] = {}
        expense_by_month: Dict[str, float] = {}

        for m in movements:
            try:
                if bool(getattr(m, "deleted", False)):
                    continue
            except Exception:
                pass
            try:
                if bool(getattr(m, "is_transfer", False)):
                    continue
            except Exception:
                pass
            try:
                dt = getattr(m, "date", None)
                if isinstance(dt, str):
                    mm = dt[:7]
                else:
                    mm = str(dt)[:7]
            except Exception:
                mm = ""
            if not mm or len(mm) < 7:
                continue
            if mm not in months:
                continue

            try:
                amt = float(getattr(m, "amount", 0.0) or 0.0)
            except Exception:
                amt = 0.0

            if amt > 0:
                income_by_month[mm] = income_by_month.get(mm, 0.0) + amt
            elif amt < 0:
                expense_by_month[mm] = expense_by_month.get(mm, 0.0) + abs(amt)

        cnt = 6
        avg_inc = sum(income_by_month.get(m, 0.0) for m in months) / float(cnt)
        avg_exp = sum(expense_by_month.get(m, 0.0) for m in months) / float(cnt)

        return DashboardMeta.now(
            total_all=overview.total_all,
            total_liquid=overview.total_liquid,
            avg_monthly_income=avg_inc,
            avg_monthly_expense=avg_exp,
            avg_months_count=cnt,
        )
