from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DashboardMeta:
    total_all: float
    total_liquid: float
    avg_monthly_income: float
    avg_monthly_expense: float
    avg_months_count: int
    computed_at: str

    @staticmethod
    def now(
        *,
        total_all: float,
        total_liquid: float,
        avg_monthly_income: float,
        avg_monthly_expense: float,
        avg_months_count: int,
    ) -> "DashboardMeta":
        try:
            d = date.today().isoformat()
        except Exception:
            d = ""
        return DashboardMeta(
            total_all=float(total_all),
            total_liquid=float(total_liquid),
            avg_monthly_income=float(avg_monthly_income),
            avg_monthly_expense=float(avg_monthly_expense),
            avg_months_count=int(avg_months_count),
            computed_at=d,
        )
