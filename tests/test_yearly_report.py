"""בדיקות לדוח השנתי: הדוח בונה את עצמו מהתנועות.

ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.yearly_report import YearlyReport  # noqa: E402


def _approx(a, b, tol=0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _m(amount, date, category, mtype=MovementType.MONTHLY, is_transfer=False, account="בנק"):
    return BankMovement(amount, date, account, category, mtype, is_transfer=is_transfer)


def _sample():
    return [
        _m(5000.0, "2026-03-05", "משכורת"),
        _m(-1200.0, "2026-04-10", "שכירות"),
        _m(-300.0, "2026-05-12", "ביטוח", mtype=MovementType.YEARLY),
        _m(-999.0, "2026-06-15", "העברה", is_transfer=True),   # transfer -> excluded
        _m(-700.0, "2025-01-01", "שכירות"),                     # other year
    ]


def test_build_filters_year_and_transfers() -> None:
    r = YearlyReport.build(_sample(), 2026)
    assert r.summary.movement_count == 3
    assert _approx(r.summary.total_income, 5000.0)
    assert _approx(r.summary.total_outcome, 1500.0)
    assert _approx(r.summary.net_amount, 3500.0)


def test_build_movement_type_filter() -> None:
    r = YearlyReport.build(_sample(), 2026, movement_types={MovementType.MONTHLY})
    assert r.summary.movement_count == 2          # YEARLY insurance excluded
    assert _approx(r.summary.total_outcome, 1200.0)


def test_month_and_account_breakdowns() -> None:
    r = YearlyReport.build(_sample(), 2026)
    assert set(r.month_breakdowns.keys()) == {(2026, 3), (2026, 4), (2026, 5)}
    assert "בנק" in r.account_breakdowns
    assert _approx(r.account_breakdowns["בנק"].net_amount, 3500.0)


def test_category_breakdown_income_first() -> None:
    r = YearlyReport.build(_sample(), 2026)
    assert r.category_breakdowns[0].is_income is True
    assert r.category_breakdowns[0].category == "משכורת"


def test_forecast_savings_by_name_series_per_sub() -> None:
    from types import SimpleNamespace

    from finance.models.yearly_report_service import (
        forecast_savings_balance,
        forecast_savings_by_name,
    )

    acc = SimpleNamespace(
        savings=[
            SimpleNamespace(
                name="קרן",
                amount=1000.0,
                history=[
                    SimpleNamespace(date="2026-01-01", amount=900.0),
                    SimpleNamespace(date="2026-02-01", amount=950.0),
                ],
            )
        ]
    )
    out = forecast_savings_by_name(acc, horizon=3)
    assert set(out) == {"קרן"}
    assert out["קרן"] == forecast_savings_balance([900.0, 950.0], 1000.0, horizon=3)


def test_forecast_savings_by_name_skips_unparseable_dates() -> None:
    from types import SimpleNamespace

    from finance.models.yearly_report_service import (
        forecast_savings_balance,
        forecast_savings_by_name,
    )

    acc = SimpleNamespace(
        savings=[
            SimpleNamespace(
                name="x",
                amount=500.0,
                history=[
                    SimpleNamespace(date="not-a-date", amount=100.0),
                    SimpleNamespace(date="2026-01-01", amount=400.0),
                ],
            )
        ]
    )
    out = forecast_savings_by_name(acc)
    assert out["x"] == forecast_savings_balance([400.0], 500.0, horizon=6)


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
