from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from statistics import median, pstdev
from typing import Dict, List, Optional

from ..data.bank_movement_provider import (
    BankMovementProvider,
    JsonFileBankMovementProvider,
)


def _month_key(date_str: object) -> str:
    s = str(date_str or "")
    return s[:7] if len(s) >= 7 else ""


def _shift_month(base: date, delta_months: int) -> tuple[int, int]:
    y = int(base.year)
    m0 = int(base.month) - 1
    n = y * 12 + m0 + int(delta_months)
    ny = n // 12
    nm0 = n % 12
    return int(ny), int(nm0 + 1)


def _clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _map_linear_0_1(x: float, in_lo: float, in_hi: float) -> float:
    """
    Maps x from [in_lo,in_hi] to [0,1] and clamps.
    """
    if float(in_hi) == float(in_lo):
        return 0.5
    return _clamp((float(x) - float(in_lo)) / (float(in_hi) - float(in_lo)), 0.0, 1.0)


@dataclass(frozen=True)
class GradeResult:
    grade: float
    grade_version: int
    computed_at: str
    months_used: List[str]
    components: Dict[str, float]
    explanations: List[str]


class UserGradeService:
    def __init__(
        self, *, movement_provider: Optional[BankMovementProvider] = None
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()

    def compute(self) -> GradeResult:
        movements = list(self._movement_provider.list_movements())

        today = date.today()
        anchor_y, anchor_m = _shift_month(today, -2)
        anchor = date(anchor_y, anchor_m, 1)
        months: List[str] = [
            f"{_shift_month(anchor, -i)[0]:04d}-{_shift_month(anchor, -i)[1]:02d}"
            for i in range(6)
        ]

        income_by: Dict[str, float] = {m: 0.0 for m in months}
        expense_by: Dict[str, float] = {m: 0.0 for m in months}
        expense_cnt: Dict[str, int] = {m: 0 for m in months}
        any_cnt: Dict[str, int] = {m: 0 for m in months}

        for mv in movements:
            try:
                if bool(getattr(mv, "is_transfer", False)):
                    continue
            except Exception:
                pass

            mm = _month_key(getattr(mv, "date", ""))
            if mm not in income_by:
                continue

            try:
                amt = float(getattr(mv, "amount", 0.0) or 0.0)
            except Exception:
                amt = 0.0

            if amt > 0:
                income_by[mm] += amt
                any_cnt[mm] += 1
            elif amt < 0:
                expense_by[mm] += abs(amt)
                expense_cnt[mm] += 1
                any_cnt[mm] += 1

        expense_vals = [expense_by[m] for m in months if float(expense_by[m]) > 0.0]
        baseline = float(median(expense_vals)) if expense_vals else 0.0

        month_scores: List[tuple[str, float]] = []
        for m in months:
            inc = float(income_by[m])
            exp = float(expense_by[m])
            net = inc - exp

            savings_rate = net / max(inc, 1.0)
            net_score = _map_linear_0_1(savings_rate, -0.2, 0.2)

            if baseline <= 0.0:
                control_score = 0.5
            else:
                overs = max(0.0, exp - baseline) / max(baseline, 1.0)
                control_score = 1.0 - _clamp(overs, 0.0, 1.0)

            completeness = 1.0 if int(expense_cnt[m]) > 0 else 0.4

            month_score = 0.45 * net_score + 0.25 * control_score + 0.20 * completeness
            month_scores.append((m, float(month_score)))

        if len(expense_vals) >= 2 and sum(expense_vals) > 0.0:
            mean_exp = float(sum(expense_vals)) / float(len(expense_vals))
            vol = float(pstdev(expense_vals)) / max(mean_exp, 1.0)
            stability = 1.0 - _clamp(vol / 0.6, 0.0, 1.0)
        else:
            stability = 0.5

        raw_score = 100.0 * (
            sum(ms for _, ms in month_scores) / max(len(month_scores), 1)
        )
        raw_score = _clamp(raw_score * (0.9 + 0.1 * stability), 0.0, 100.0)

        months_with_expense = sum(1 for m in months if int(expense_cnt[m]) > 0)
        months_with_any = sum(1 for m in months if int(any_cnt[m]) > 0)
        total_moves = sum(int(any_cnt[m]) for m in months)

        conf_exp_months = _clamp(
            float(months_with_expense) / 3.0, 0.0, 1.0
        )  # 3 months => full
        conf_any_months = _clamp(
            float(months_with_any) / 6.0, 0.0, 1.0
        )  # 6 months => full
        conf_moves = (
            1.0 - math.exp(-float(total_moves) / 40.0) if total_moves > 0 else 0.0
        )

        confidence = _clamp(
            0.6 * conf_exp_months + 0.2 * conf_any_months + 0.2 * conf_moves, 0.0, 1.0
        )

        grade = _clamp(raw_score * confidence, 0.0, 100.0)

        explanations: List[str] = []
        try:
            best_month = max(month_scores, key=lambda x: x[1])[0]
            explanations.append(f"חודש חזק: {best_month}")
        except Exception:
            pass
        if baseline > 0.0:
            explanations.append(f"בסיס הוצאות חודשי (מדיאן): {baseline:.0f}")
        explanations.append(f"יציבות הוצאות: {stability:.2f}")
        explanations.append(f"בטחון נתונים: {confidence:.2f}")

        return GradeResult(
            grade=float(round(grade, 2)),
            grade_version=2,
            computed_at=today.isoformat(),
            months_used=list(months),
            components={
                "stability": float(round(stability, 6)),
                "baseline_expense": float(round(baseline, 2)),
                "raw_score": float(round(raw_score, 2)),
                "confidence": float(round(confidence, 6)),
                "months_with_expense": float(months_with_expense),
                "months_with_any": float(months_with_any),
                "total_moves": float(total_moves),
            },
            explanations=explanations[:3],
        )
