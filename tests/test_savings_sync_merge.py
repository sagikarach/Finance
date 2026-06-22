"""בדיקות למיזוג חסכונות בעת pull מ-Firebase.

ניתן להריץ עם pytest או ישירות (``python tests/test_savings_sync_merge.py``).

מכסה את התיקון שבו pull מ-Firebase דרס שינוי מקומי חדש (למשל העברה שיצאה
מהיום וטרם הועלתה) עם נתון מרוחק ישן, וכך הכסף "חזר" לחסכון. הלוגיקה חיה
כעת כהתנהגות על המחלקות (SavingsAccount.merged_with_local / Savings.last_changed).
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.accounts import (  # noqa: E402
    MoneySnapshot,
    Savings,
    SavingsAccount,
)


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def _acc(envelopes):
    return SavingsAccount(
        name="קופת גמל", total_amount=0.0, is_liquid=False,
        savings=[Savings(n, a, h) for n, a, h in envelopes],
    )


def _merge(remote_envs, local_envs):
    return _acc(remote_envs).merged_with_local(_acc(local_envs)).savings


def test_local_newer_wins_over_stale_remote() -> None:
    today = date.today().isoformat()
    remote = [("שגיא", 83_620.0, [MoneySnapshot("2026-04-30", 83_620.0)])]
    local = [(
        "שגיא", 0.0,
        [MoneySnapshot("2026-04-30", 83_620.0), MoneySnapshot(today, 0.0)],
    )]
    merged = _merge(remote, local)
    assert len(merged) == 1
    assert _approx(merged[0].amount, 0.0)  # local (newer) wins -> money stays out


def test_remote_newer_wins_over_stale_local() -> None:
    older = (date.today() - timedelta(days=10)).isoformat()
    newer = (date.today() - timedelta(days=1)).isoformat()
    remote = [("חן", 90_000.0, [MoneySnapshot(newer, 90_000.0)])]
    local = [("חן", 80_000.0, [MoneySnapshot(older, 80_000.0)])]
    merged = _merge(remote, local)
    assert _approx(merged[0].amount, 90_000.0)  # remote (newer) wins


def test_new_envelopes_on_both_sides_preserved() -> None:
    remote = [("A", 1.0, [MoneySnapshot("2026-01-01", 1.0)])]
    local = [("B", 2.0, [MoneySnapshot("2026-01-01", 2.0)])]
    merged = _merge(remote, local)
    assert {e.name for e in merged} == {"A", "B"}


def test_tie_prefers_local() -> None:
    d = "2026-06-22"
    remote = [("שגיא", 100.0, [MoneySnapshot(d, 100.0)])]
    local = [("שגיא", 0.0, [MoneySnapshot(d, 0.0)])]
    merged = _merge(remote, local)
    assert _approx(merged[0].amount, 0.0)  # same date -> keep local edit


def test_last_changed_ignores_future() -> None:
    future = (date.today() + timedelta(days=300)).isoformat()
    today = date.today().isoformat()
    with_future = Savings("x", 0.0, [MoneySnapshot(today, 1.0), MoneySnapshot(future, 2.0)])
    only_today = Savings("x", 0.0, [MoneySnapshot(today, 1.0)])
    assert with_future.last_changed() == only_today.last_changed()


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
