"""בדיקות לסריאליזציה של חשבונות (מקומי + מרוחק).

מוודאות שהמעבר ל-to_storage_dict/to_remote_dict/from_storage_dict שומר על
הפורמט הקיים בדיוק — כולל סבב מלא דרך ה-provider האמיתי (save → load) על
קבצים זמניים, כדי שלא ניפגע בנתוני החשבונות האמיתיים.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.data.provider import JsonFileAccountsProvider  # noqa: E402
from finance.models.accounts import (  # noqa: E402
    BankAccount,
    BudgetAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
    bank_entry_from_storage_dict,
)


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def test_provider_roundtrip_save_then_load() -> None:
    d = tempfile.mkdtemp()
    prov = JsonFileAccountsProvider(
        bank_accounts_path=os.path.join(d, "bank.json"),
        savings_accounts_path=os.path.join(d, "savings.json"),
    )
    bank = BankAccount(
        "בנק", 0.0, is_liquid=True,
        history=[MoneySnapshot("2026-06-01", 1000.0)], active=True, baseline_amount=500.0,
    )
    budget = BudgetAccount(
        "תקציב", 0.0, is_liquid=False,
        history=[MoneySnapshot("2026-06-01", 800.0)], active=True,
        monthly_budget=1000.0, reset_day=5, last_reset_period="2026-06",
    )
    sav = SavingsAccount(
        "חיסכון", 0.0, is_liquid=False,
        savings=[Savings("env", 0.0, [MoneySnapshot("2026-06-01", 250.0)])],
    )

    prov.save_bank_accounts([bank, budget])
    prov.save_savings_accounts([sav])
    by_name = {a.name: a for a in prov.list_accounts()}

    assert isinstance(by_name["בנק"], BankAccount)
    assert _approx(by_name["בנק"].total_amount, 1000.0)
    assert _approx(by_name["בנק"].baseline_amount, 500.0)
    assert by_name["בנק"].is_liquid is True

    assert isinstance(by_name["תקציב"], BudgetAccount)
    assert _approx(by_name["תקציב"].total_amount, 800.0)
    assert by_name["תקציב"].monthly_budget == 1000.0
    assert by_name["תקציב"].reset_day == 5
    assert by_name["תקציב"].last_reset_period == "2026-06"

    sa = by_name["חיסכון"]
    assert isinstance(sa, SavingsAccount)
    assert _approx(sa.total_amount, 250.0)
    assert sa.savings[0].name == "env"
    assert _approx(sa.savings[0].amount, 250.0)


def test_storage_format_matches_legacy() -> None:
    bank = BankAccount(
        "בנק", 0.0, is_liquid=True,
        history=[MoneySnapshot("2026-06-01", 1000.0)], active=True, baseline_amount=500.0,
    )
    assert bank.to_storage_dict() == {
        "name": "בנק",
        "is_liquid": True,
        "total_amount": 1000.0,
        "active": True,
        "history": [{"date": "2026-06-01", "amount": 1000.0}],
        "baseline_amount": 500.0,
    }
    budget = BudgetAccount(
        "תקציב", 0.0, is_liquid=False, history=[MoneySnapshot("2026-06-01", 800.0)],
        active=True, monthly_budget=1000.0, reset_day=5, last_reset_period="2026-06",
    )
    d = budget.to_storage_dict()
    assert d["kind"] == "budget" and d["monthly_budget"] == 1000.0 and d["reset_day"] == 5


def test_remote_format_bank_carries_only_structure() -> None:
    bank = BankAccount(
        "בנק", 0.0, is_liquid=True,
        history=[MoneySnapshot("2026-06-01", 1000.0)], active=True, baseline_amount=500.0,
    )
    assert bank.to_remote_dict() == {
        "kind": "bank",
        "name": "בנק",
        "is_liquid": True,
        "active": True,
        "baseline_amount": 500.0,
    }
    sav = SavingsAccount(
        "חיסכון", 0.0, is_liquid=False,
        savings=[Savings("env", 0.0, [MoneySnapshot("2026-06-01", 250.0)])],
    )
    r = sav.to_remote_dict()
    assert r["name"] == "חיסכון" and _approx(r["total_amount"], 250.0)
    assert r["savings"][0] == {"name": "env", "amount": 250.0, "history": [{"date": "2026-06-01", "amount": 250.0}]}


def test_legacy_bank_without_kind_total_zero_uses_history() -> None:
    acc = bank_entry_from_storage_dict({
        "name": "בנק", "is_liquid": True, "total_amount": 0, "active": True,
        "history": [{"date": "2026-06-01", "amount": 1234.0}], "baseline_amount": 0,
    })
    assert isinstance(acc, BankAccount)
    assert _approx(acc.total_amount, 1234.0)  # derived from history when total is 0


def test_legacy_budget_dispatch_by_kind() -> None:
    acc = bank_entry_from_storage_dict({
        "name": "תקציב", "kind": "budget", "total_amount": 800.0,
        "monthly_budget": 1000.0, "reset_day": 3,
    })
    assert isinstance(acc, BudgetAccount)
    assert acc.is_liquid is False
    assert acc.reset_day == 3


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
