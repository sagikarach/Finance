from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Tuple

from .accounts import parse_iso_date
from .bank_movement import counts_as_transfer
from .budget_period import budget_period_end_key, next_month
from ..utils.safe import PARSE_ERRORS

MonthKey = Tuple[int, int]


def _month_key_fast(date_str: str) -> Optional[MonthKey]:
    """Fast (year, month) parse of an ISO-ish date string; None if it doesn't fit."""
    s = str(date_str or "").strip()
    if len(s) >= 7 and s[4] == "-" and s[7:8] in ("", "-"):
        try:
            y, m = int(s[0:4]), int(s[5:7])
            if 1 <= m <= 12:
                return (y, m)
        except PARSE_ERRORS:
            pass
    return None


@dataclass(frozen=True)
class BalanceTimeline:
    """A bank account's running balance across months: ``values`` is
    ``[baseline, after month_keys[0], …, after month_keys[-1], today]``
    (i.e. ``len(values) == len(month_keys) + 2``)."""

    month_keys: List[MonthKey]
    values: List[float]


@dataclass(frozen=True)
class BudgetSpend:
    """Spend per budget period (bucketed by the account's reset day)."""

    month_keys: List[MonthKey]
    spent: List[float]


def _contiguous_months(keys: List[MonthKey]) -> List[MonthKey]:
    """Fill the gap between the first and last key with every month in between."""
    if not keys:
        return []
    ordered = sorted(keys)
    out: List[MonthKey] = []
    cur = ordered[0]
    while True:
        out.append(cur)
        if cur == ordered[-1]:
            break
        cur = next_month(cur[0], cur[1])
    return out


def balance_timeline(account: Any, movements: List[Any]) -> BalanceTimeline:
    """Reconstruct an account's running-balance timeline from its movements.
    When the account has no stored baseline, infer it so the final balance
    matches ``total_amount`` (``baseline = total_amount − Σ movements``)."""
    acc_name = str(getattr(account, "name", "") or "").strip()
    baseline = float(getattr(account, "baseline_amount", 0.0) or 0.0)

    sums: dict[MonthKey, float] = {}
    for m in movements:
        try:
            if str(getattr(m, "account_name", "") or "").strip() != acc_name:
                continue
            ks = str(getattr(m, "date", "") or "")
            key = _month_key_fast(ks)
            if key is None:
                dt = parse_iso_date(ks)
                if dt == datetime.min:
                    continue
                key = (dt.year, dt.month)
            sums[key] = sums.get(key, 0.0) + float(getattr(m, "amount", 0.0) or 0.0)
        except PARSE_ERRORS:
            continue

    try:
        if float(baseline) == 0.0:
            inferred = float(getattr(account, "total_amount", 0.0) or 0.0) - sum(
                sums.values()
            )
            if abs(inferred) > 0.0001:
                baseline = inferred
    except PARSE_ERRORS:
        pass

    month_keys = _contiguous_months(list(sums.keys()))
    running = float(baseline)
    values = [running]
    for k in month_keys:
        running += sums.get(k, 0.0)
        values.append(running)
    values.append(running)  # "today"
    return BalanceTimeline(month_keys=month_keys, values=values)


def budget_spend_by_period(account: Any, movements: List[Any]) -> BudgetSpend:
    """Total non-transfer spend per budget period for ``account``, bucketed by
    its reset day (``budget_period_end_key``)."""
    acc_name = getattr(account, "name", None)
    spent = [
        m
        for m in (movements or [])
        if m.account_name == acc_name
        and float(getattr(m, "amount", 0.0) or 0.0) < 0.0
        and not counts_as_transfer(m)
    ]
    reset_day = max(1, min(28, int(getattr(account, "reset_day", 1) or 1)))
    by_period: dict[MonthKey, float] = {}
    for m in spent:
        end_key = budget_period_end_key(str(getattr(m, "date", "") or ""), reset_day)
        if end_key is None:
            continue
        by_period[end_key] = by_period.get(end_key, 0.0) + abs(
            float(getattr(m, "amount", 0.0) or 0.0)
        )
    month_keys = _contiguous_months(list(by_period.keys()))
    spent_vals = [float(by_period.get(k, 0.0)) for k in month_keys]
    return BudgetSpend(month_keys=month_keys, spent=spent_vals)
