"""בדיקות לדוח החודשי: הדוח בונה את עצמו מהתנועות.

ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.monthly_report import MonthlyReport  # noqa: E402


def _approx(a, b, tol=0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _m(amount, date, category, mtype=MovementType.MONTHLY, is_transfer=False, account="בנק"):
    return BankMovement(amount, date, account, category, mtype, is_transfer=is_transfer)


def _sample():
    return [
        _m(5000.0, "2026-06-05", "משכורת"),
        _m(-1200.0, "2026-06-10", "שכירות"),
        _m(-300.0, "2026-06-12", "שכירות"),
        _m(-999.0, "2026-06-15", "העברה", is_transfer=True),       # transfer -> excluded
        _m(-50.0, "2026-06-20", "מסעדה", mtype=MovementType.ONE_TIME),  # not monthly
        _m(-700.0, "2026-05-01", "שכירות"),                         # other month
    ]


def test_build_filters_and_summarizes() -> None:
    r = MonthlyReport.build(_sample(), 2026, 6)
    assert r.summary.movement_count == 3
    assert _approx(r.summary.total_income, 5000.0)
    assert _approx(r.summary.total_outcome, 1500.0)
    assert _approx(r.summary.net_amount, 3500.0)
    assert r.summary.income_count == 1 and r.summary.outcome_count == 2


def test_category_breakdown_merges_and_sorts_income_first() -> None:
    r = MonthlyReport.build(_sample(), 2026, 6)
    cats = r.category_breakdowns
    assert cats[0].is_income is True and cats[0].category == "משכורת"
    rent = [c for c in cats if c.category == "שכירות"][0]
    assert _approx(rent.total_amount, 1500.0) and rent.movement_count == 2


def test_account_filter_excludes_others() -> None:
    r = MonthlyReport.build(_sample(), 2026, 6, account_names=["לא-קיים"])
    assert r.summary.movement_count == 0
    assert r.category_breakdowns == []
    assert r.account_breakdowns == {}


def test_account_breakdown_present() -> None:
    r = MonthlyReport.build(_sample(), 2026, 6)
    assert "בנק" in r.account_breakdowns
    assert _approx(r.account_breakdowns["בנק"].net_amount, 3500.0)


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
