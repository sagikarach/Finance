from __future__ import annotations

from typing import List, Optional, Set

from .accounts import parse_iso_date
from .monthly_report import (
    MonthlyReport,
)
from ..data.bank_movement_provider import BankMovementProvider


class MonthlyReportService:
    def __init__(self, movement_provider: BankMovementProvider) -> None:
        self.movement_provider = movement_provider

    def get_monthly_report(
        self,
        year: int,
        month: int,
        account_names: Optional[List[str]] = None,
    ) -> Optional[MonthlyReport]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return None
        # The report knows how to build itself from the movements.
        return MonthlyReport.build(all_movements, year, month, account_names)

    def get_available_months(
        self, account_names: Optional[List[str]] = None
    ) -> List[tuple[int, int]]:
        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return []

        if account_names:
            account_set: Set[str] = set(account_names)
            movements = [m for m in all_movements if m.account_name in account_set]
        else:
            movements = all_movements

        from datetime import datetime as _dt
        month_keys: Set[tuple[int, int]] = set()
        for movement in movements:
            try:
                dt = parse_iso_date(movement.date)
                if dt == _dt.min:
                    continue
                month_key = (dt.year, dt.month)
                month_keys.add(month_key)
            except Exception:
                continue

        sorted_months = sorted(month_keys, key=lambda k: (k[0], k[1]), reverse=True)
        return sorted_months
