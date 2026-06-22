"""בדיקות לחישוב היתרה הנוכחית של חשבון מ-history.

ניתן להריץ עם pytest (``python -m pytest tests/test_account_balance.py``)
או ישירות (``python tests/test_account_balance.py``).

מכסה את התיקון שבו snapshot עם תאריך עתידי (נקודת תחזית או טעות שנה כמו
2027 במקום 2026) לא ישתלט על היתרה המוצגת.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.accounts import (  # noqa: E402
    BankAccount,
    MoneySnapshot,
    latest_amount_from_history,
)


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def test_latest_ignores_future_dated_snapshot() -> None:
    future = (date.today() + timedelta(days=300)).isoformat()
    today = date.today().isoformat()
    hist = [
        MoneySnapshot(today, 232_555.92),
        MoneySnapshot(future, 117_921.23),  # date typo / projection
    ]
    assert _approx(latest_amount_from_history(hist), 232_555.92)


def test_latest_picks_most_recent_past() -> None:
    hist = [
        MoneySnapshot("2025-01-01", 100.0),
        MoneySnapshot("2026-06-22", 300.0),
        MoneySnapshot("2026-03-01", 200.0),
    ]
    assert _approx(latest_amount_from_history(hist), 300.0)


def test_all_future_falls_back_to_latest() -> None:
    f1 = (date.today() + timedelta(days=10)).isoformat()
    f2 = (date.today() + timedelta(days=20)).isoformat()
    hist = [MoneySnapshot(f1, 50.0), MoneySnapshot(f2, 75.0)]
    # every snapshot is future-dated -> fall back to the latest overall
    assert _approx(latest_amount_from_history(hist), 75.0)


def test_bank_account_total_ignores_future_snapshot() -> None:
    future = (date.today() + timedelta(days=300)).isoformat()
    today = date.today().isoformat()
    acc = BankAccount(
        name="בנק",
        total_amount=0.0,
        is_liquid=True,
        history=[
            MoneySnapshot(today, 232_555.92),
            MoneySnapshot(future, 117_921.23),
        ],
        baseline_amount=141_294.98,
    )
    # __post_init__ derives total_amount from the latest NON-future snapshot
    assert _approx(acc.total_amount, 232_555.92)


def test_empty_history_returns_none() -> None:
    assert latest_amount_from_history([]) is None


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
