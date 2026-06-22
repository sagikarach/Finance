"""בדיקות לאירועים חד-פעמיים: האירוע מחשב את הסיכומים של עצמו.

ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.one_time_event import OneTimeEvent  # noqa: E402


def _approx(a, b, tol=0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _mv(amount, date, event_id=None, category="אוכל"):
    return BankMovement(
        amount, date, "בנק", category, MovementType.ONE_TIME, event_id=event_id
    )


def test_event_totals_only_owned_movements() -> None:
    ev = OneTimeEvent(name="חתונה", budget=10_000.0)
    movements = [
        _mv(-3000.0, "2026-03-01", event_id=ev.id, category="אולם"),
        _mv(-1000.0, "2026-03-02", event_id=ev.id, category="צילום"),
        _mv(500.0, "2026-03-03", event_id=ev.id, category="מתנה"),
        _mv(-9999.0, "2026-03-04", event_id="other"),  # not this event
    ]
    t = ev.totals(movements)
    assert _approx(t.expenses, 4000.0)
    assert _approx(t.income, 500.0)
    assert _approx(t.net, -3500.0)
    assert _approx(t.remaining, 6000.0)        # 10000 budget - 4000 spent
    assert t.percent_used is not None and _approx(t.percent_used, 0.4)
    assert _approx(t.by_category_expense["אולם"], 3000.0)


def test_event_totals_respects_date_window() -> None:
    ev = OneTimeEvent(name="טיול", budget=0.0, start_date="2026-06-01", end_date="2026-06-30")
    movements = [
        _mv(-100.0, "2026-05-31", event_id=ev.id),   # before window -> excluded
        _mv(-200.0, "2026-06-15", event_id=ev.id),   # in window
        _mv(-300.0, "2026-07-01", event_id=ev.id),   # after window -> excluded
    ]
    t = ev.totals(movements)
    assert _approx(t.expenses, 200.0)
    assert t.percent_used is None                # budget is 0 -> undefined


def test_event_owns_and_in_range() -> None:
    ev = OneTimeEvent(name="x", budget=0.0, start_date="2026-06-01", end_date="2026-06-30")
    inside = _mv(-1.0, "2026-06-10", event_id=ev.id)
    assert ev.owns(inside) is True
    assert ev.owns(_mv(-1.0, "2026-06-10", event_id="other")) is False
    assert ev.in_range(_mv(-1.0, "2026-07-10")) is False


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
