"""בדיקות התנהגות לליבת השירותים: העברות וחישוב יתרות.

נכתבו כדי לנעול את ההתנהגות הקיימת לפני מעבר לעיצוב מונחה-עצמים (OOP),
כך שריפקטור חייב לשמר אותן. ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.accounts import (  # noqa: E402
    BankAccount,
    BudgetAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
)
from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.bank_movement_service import BankMovementService  # noqa: E402
from finance.models.transfers import (  # noqa: E402
    TransferEndpoint,
    TransferRequest,
    apply_transfer,
)


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


class _FakeMovementProvider:
    def __init__(self, movements):
        self._movements = list(movements)

    def list_movements(self):
        return list(self._movements)


def _bank(name, total, **kw):
    return BankAccount(name=name, total_amount=total, is_liquid=kw.get("is_liquid", True),
                       active=kw.get("active", True),
                       baseline_amount=kw.get("baseline_amount", 0.0))


def _savings(name, envelopes):
    return SavingsAccount(name=name, total_amount=0.0, is_liquid=False,
                          savings=[Savings(n, a) for n, a in envelopes])


# ----- transfers -------------------------------------------------------------

def test_transfer_bank_to_saving() -> None:
    accounts = [_bank("בנק", 1000.0), _savings("חיסכון", [("env", 500.0)])]
    req = TransferRequest(
        source=TransferEndpoint(kind="bank", account_index=0),
        target=TransferEndpoint(kind="saving", account_index=1, savings_index=0),
        amount=300.0,
    )
    res = apply_transfer(accounts, req)
    assert res.error is None
    assert _approx(res.accounts[0].total_amount, 700.0)
    assert _approx(res.accounts[1].total_amount, 800.0)


def test_transfer_saving_to_bank() -> None:
    accounts = [_bank("בנק", 1000.0), _savings("חיסכון", [("env", 500.0)])]
    req = TransferRequest(
        source=TransferEndpoint(kind="saving", account_index=1, savings_index=0),
        target=TransferEndpoint(kind="bank", account_index=0),
        amount=200.0,
    )
    res = apply_transfer(accounts, req)
    assert res.error is None
    assert _approx(res.accounts[0].total_amount, 1200.0)
    assert _approx(res.accounts[1].total_amount, 300.0)


def test_transfer_insufficient_saving_funds_errors() -> None:
    accounts = [_bank("בנק", 1000.0), _savings("חיסכון", [("env", 100.0)])]
    req = TransferRequest(
        source=TransferEndpoint(kind="saving", account_index=1, savings_index=0),
        target=TransferEndpoint(kind="bank", account_index=0),
        amount=500.0,
    )
    res = apply_transfer(accounts, req)
    assert res.error is not None


def test_transfer_nonpositive_amount_errors() -> None:
    accounts = [_bank("בנק", 1000.0), _savings("חיסכון", [("env", 100.0)])]
    req = TransferRequest(
        source=TransferEndpoint(kind="bank", account_index=0),
        target=TransferEndpoint(kind="saving", account_index=1, savings_index=0),
        amount=0.0,
    )
    res = apply_transfer(accounts, req)
    assert res.error is not None


# ----- balance recalculation -------------------------------------------------

def _svc(movements):
    return BankMovementService(
        movement_provider=_FakeMovementProvider(movements), history_provider=None
    )


def test_recalc_bank_is_baseline_plus_movements() -> None:
    movs = [
        BankMovement(500.0, "2026-06-01", "בנק", "משכורת", MovementType.ONE_TIME),
        BankMovement(-200.0, "2026-06-02", "בנק", "קניות", MovementType.ONE_TIME),
    ]
    acc = BankAccount("בנק", 0.0, is_liquid=True, active=True, baseline_amount=1000.0)
    out = _svc(movs).recalculate_account_balances([acc])
    # 1000 baseline + 500 - 200 = 1300
    assert _approx(out[0].total_amount, 1300.0)


def test_recalc_bank_includes_incoming_transfer_credit() -> None:
    # Regression for the saving->bank transfer that must credit the bank.
    movs = [
        BankMovement(2000.0, "2026-06-19", "בנק", "העברה", MovementType.ONE_TIME, is_transfer=True),
    ]
    acc = BankAccount("בנק", 0.0, is_liquid=True, active=True, baseline_amount=100.0)
    out = _svc(movs).recalculate_account_balances([acc])
    assert _approx(out[0].total_amount, 2100.0)


def test_recalc_budget_remaining_for_period() -> None:
    today = date.today().isoformat()
    movs = [BankMovement(-200.0, today, "תקציב", "קניות", MovementType.ONE_TIME)]
    acc = BudgetAccount("תקציב", 0.0, is_liquid=False, active=True,
                        monthly_budget=1000.0, reset_day=1)
    out = _svc(movs).recalculate_account_balances([acc])
    assert _approx(out[0].total_amount, 800.0)  # 1000 budget - 200 spent


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
