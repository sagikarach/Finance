"""בדיקות לתשלומים (installments): התוכנית מחשבת את הסטטיסטיקה של עצמה.

ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.installment_plan import InstallmentPlan  # noqa: E402


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _pay(amount, date, desc="תשלום רהיטים"):
    return BankMovement(amount, date, "בנק", "ריהוט", MovementType.ONE_TIME, description=desc)


def test_plan_stats_counts_and_totals() -> None:
    plan = InstallmentPlan(
        name="ספה", vendor_query="רהיטים", account_name="בנק",
        start_date="2026-01-01", payments_count=4, original_amount=4000.0,
    )
    movements = [
        _pay(-1000.0, "2026-01-10"),
        _pay(-1000.0, "2026-02-10"),
        _pay(-1000.0, "2026-03-10"),
    ]
    stats = plan.stats(movements)
    assert stats.paid_count == 3
    assert stats.payments_left == 1          # 4 planned - 3 paid
    assert _approx(stats.total_paid, 3000.0)  # abs of each payment
    assert _approx(stats.overpaid, 0.0)


def test_plan_stats_overpaid() -> None:
    plan = InstallmentPlan(
        name="ספה", vendor_query="רהיטים", account_name="בנק",
        start_date="2026-01-01", payments_count=2, original_amount=1500.0,
    )
    movements = [_pay(-1000.0, "2026-01-10"), _pay(-1000.0, "2026-02-10")]
    stats = plan.stats(movements)
    assert _approx(stats.total_paid, 2000.0)
    assert _approx(stats.overpaid, 500.0)     # 2000 paid - 1500 original


def test_plan_matches_excludes_listed_ids() -> None:
    m1 = _pay(-1000.0, "2026-01-10")
    plan = InstallmentPlan(
        name="ספה", vendor_query="רהיטים", account_name="בנק",
        start_date="2026-01-01", payments_count=4,
        excluded_movement_ids=[m1.id],
    )
    matched = plan.matches([m1, _pay(-1000.0, "2026-02-10")])
    assert m1.id not in [m.id for m in matched]


def _run_all() -> int:
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failures}/{len(funcs)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
