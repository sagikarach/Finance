"""בדיקות למקור מימון (FundingSource): המקור מחשב זמינות/ניצול בעצמו.

הלוגיקה הזו ישבה קודם בקובץ ה-UI (asset_detail_page) ועברה לדומיין.
ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.accounts import BankAccount, Savings, SavingsAccount  # noqa: E402
from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.mortgage import (  # noqa: E402
    FundingKind,
    FundingSource,
    account_transferred_out,
    endpoint_balance,
)


def _approx(a, b, tol=0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _bank(name, total):
    return BankAccount(name, total, is_liquid=True, active=True)


def _savings(name, envelopes):
    return SavingsAccount(name, 0.0, is_liquid=False, savings=[Savings(n, a) for n, a in envelopes])


def _transfer_out(amount, account_name):
    return BankMovement(-abs(amount), "2026-06-01", account_name, "העברה",
                        MovementType.ONE_TIME, is_transfer=True)


def test_endpoint_balance_account_and_saving() -> None:
    accounts = [_bank("בנק", 1000.0), _savings("חיסכון", [("שגיא", 250.0), ("חן", 90.0)])]
    assert _approx(endpoint_balance(accounts, "בנק"), 1000.0)
    assert _approx(endpoint_balance(accounts, "חיסכון", "שגיא"), 250.0)
    assert _approx(endpoint_balance(accounts, "לא-קיים"), 0.0)


def test_account_transferred_out_matches_target() -> None:
    movs = [
        _transfer_out(500.0, "בנק"),
        _transfer_out(200.0, "בנק"),
        _transfer_out(999.0, "אחר"),                 # different account
        BankMovement(-100.0, "2026-06-02", "בנק", "קניות", MovementType.ONE_TIME),  # not a transfer
    ]
    assert _approx(account_transferred_out(movs, "בנק"), 700.0)


def test_funding_source_account_available_and_spent() -> None:
    accounts = [_bank("בנק", 1000.0)]
    src = FundingSource(name="מהבנק", kind=FundingKind.ACCOUNT, account_name="בנק")
    assert _approx(src.available(movements=[], accounts=accounts), 1000.0)
    assert _approx(src.spent([_transfer_out(400.0, "בנק")]), 400.0)


def test_funding_source_future_is_unrealized() -> None:
    src = FundingSource(name="עתידי", kind=FundingKind.FUTURE, amount=5000.0)
    assert _approx(src.available(movements=[], accounts=[]), 0.0)
    assert src.spent([]) is None


def test_funding_breakdown_rows_structure_and_totals() -> None:
    from finance.models.asset import funding_breakdown_rows

    accounts = [_bank("בנק", 1000.0)]
    sources = [
        FundingSource(name="מתנה", kind=FundingKind.FUTURE, amount=200_000.0),
        FundingSource(name="מהבנק", kind=FundingKind.ACCOUNT, account_name="בנק"),
    ]
    rows = funding_breakdown_rows(
        sources, [], accounts,
        tracks_total=1_000_000.0, residual=50_000.0,
        remaining_need=40_000.0, exp_paid=10_000.0, bank_account_name="בנק",
    )
    # funding sources first (edit indices), then mortgage, bank, total
    assert [r.label for r in rows[:2]] == ["מתנה", "מהבנק"]
    assert rows[2].label == "משכנתא" and _approx(rows[2].amount, 1_000_000.0)
    assert rows[3].label == "חשבון בנק" and _approx(rows[3].available, 40_000.0)
    total = rows[-1]
    assert total.is_total is True
    # 200000 (gift) + 1000 (bank balance avail) ... amount totals: 200000+0+1000000+50000
    assert _approx(total.amount, 200_000.0 + 0.0 + 1_000_000.0 + 50_000.0)
    assert _approx(total.available, 0.0 + 1000.0 + 1_000_000.0 + 40_000.0)


def test_funding_breakdown_future_source_available_zero() -> None:
    from finance.models.asset import funding_breakdown_rows

    rows = funding_breakdown_rows(
        [FundingSource(name="עתידי", kind=FundingKind.FUTURE, amount=5000.0)],
        [], [],
        tracks_total=0.0, residual=0.0, remaining_need=0.0, exp_paid=0.0,
    )
    future_row = rows[0]
    assert _approx(future_row.amount, 5000.0)
    assert _approx(future_row.available, 0.0)   # future -> not yet available
    assert future_row.spent is None


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
