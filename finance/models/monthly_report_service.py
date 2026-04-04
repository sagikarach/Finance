from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set

from .accounts import parse_iso_date
from .bank_movement import BankMovement, MovementType
from .monthly_report import (
    CategoryMonthlyBreakdown,
    MonthlyMovementSummary,
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

        if account_names:
            account_set: Set[str] = set(account_names)
            movements = [
                m
                for m in all_movements
                if m.account_name in account_set
                and self._is_in_month(m.date, year, month)
                and m.type == MovementType.MONTHLY
                and not self._is_transfer(m)
            ]
        else:
            movements = [
                m
                for m in all_movements
                if self._is_in_month(m.date, year, month)
                and m.type == MovementType.MONTHLY
                and not self._is_transfer(m)
            ]

        if not movements:
            summary = MonthlyMovementSummary(
                year=year,
                month=month,
                total_income=0.0,
                total_outcome=0.0,
                net_amount=0.0,
                movement_count=0,
                income_count=0,
                outcome_count=0,
            )
            return MonthlyReport(
                year=year,
                month=month,
                summary=summary,
                category_breakdowns=[],
                movements=[],
                account_breakdowns={},
            )

        summary = self._calculate_summary(movements, year, month)
        category_breakdowns = self._calculate_category_breakdowns(
            movements, year, month
        )
        account_breakdowns = self._calculate_account_breakdowns(movements, year, month)

        return MonthlyReport(
            year=year,
            month=month,
            summary=summary,
            category_breakdowns=category_breakdowns,
            movements=movements,
            account_breakdowns=account_breakdowns,
        )

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

    def _is_in_month(self, date_str: str, year: int, month: int) -> bool:
        try:
            dt = parse_iso_date(date_str)
            return dt.year == year and dt.month == month
        except Exception:
            return False

    def _is_transfer(self, movement: BankMovement) -> bool:
        try:
            if bool(getattr(movement, "is_transfer", False)):
                return True
        except Exception:
            pass
        try:
            if str(getattr(movement, "category", "") or "").strip() == "העברה":
                return True
        except Exception:
            pass
        return False

    def _calculate_summary(
        self, movements: List[BankMovement], year: int, month: int
    ) -> MonthlyMovementSummary:
        total_income = 0.0
        total_outcome = 0.0
        income_count = 0
        outcome_count = 0

        for movement in movements:
            try:
                amount = float(movement.amount)
                if amount > 0:
                    total_income += amount
                    income_count += 1
                elif amount < 0:
                    total_outcome += abs(amount)
                    outcome_count += 1
            except Exception:
                continue

        net_amount = total_income - total_outcome

        return MonthlyMovementSummary(
            year=year,
            month=month,
            total_income=total_income,
            total_outcome=total_outcome,
            net_amount=net_amount,
            movement_count=len(movements),
            income_count=income_count,
            outcome_count=outcome_count,
        )

    def _calculate_category_breakdowns(
        self, movements: List[BankMovement], year: int, month: int
    ) -> List[CategoryMonthlyBreakdown]:
        category_data: Dict[tuple[str, bool], List[float]] = defaultdict(list)

        for movement in movements:
            try:
                amount = float(movement.amount)
                is_income = amount > 0
                category = movement.category or "שונות"
                key = (category, is_income)
                category_data[key].append(abs(amount))
            except Exception:
                continue

        breakdowns: List[CategoryMonthlyBreakdown] = []
        for (category, is_income), amounts in category_data.items():
            total_amount = sum(amounts)
            breakdowns.append(
                CategoryMonthlyBreakdown(
                    category=category,
                    year=year,
                    month=month,
                    total_amount=total_amount,
                    movement_count=len(amounts),
                    is_income=is_income,
                )
            )

        breakdowns.sort(key=lambda x: (not x.is_income, -x.total_amount))
        return breakdowns

    def _calculate_account_breakdowns(
        self, movements: List[BankMovement], year: int, month: int
    ) -> Dict[str, MonthlyMovementSummary]:
        account_movements: Dict[str, List[BankMovement]] = defaultdict(list)

        for movement in movements:
            account_movements[movement.account_name].append(movement)

        account_breakdowns: Dict[str, MonthlyMovementSummary] = {}
        for account_name, account_movs in account_movements.items():
            summary = self._calculate_summary(account_movs, year, month)
            account_breakdowns[account_name] = summary

        return account_breakdowns
