"""בדיקות למיזוג חסכונות בעת pull מ-Firebase.

ניתן להריץ עם pytest או ישירות (``python tests/test_savings_sync_merge.py``).

מכסה את התיקון שבו pull מ-Firebase דרס שינוי מקומי חדש (למשל העברה שיצאה
מהיום וטרם הועלתה) עם נתון מרוחק ישן, וכך הכסף "חזר" לחסכון.
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.accounts import MoneySnapshot, Savings  # noqa: E402
from finance.models.firebase_sync_accounts_meta import (  # noqa: E402
    _latest_snapshot_dt,
    _merge_savings_envelopes,
)


def _approx(a: float, b: float, tol: float = 0.005) -> bool:
    return abs(float(a) - float(b)) <= tol


def test_local_newer_wins_over_stale_remote() -> None:
    # The exact bug: local has today's transfer-out (0), remote is stale.
    today = date.today().isoformat()
    remote = [Savings("שגיא", 83_620.0, [MoneySnapshot("2026-04-30", 83_620.0)])]
    local = [
        Savings(
            "שגיא",
            0.0,
            [MoneySnapshot("2026-04-30", 83_620.0), MoneySnapshot(today, 0.0)],
        )
    ]
    merged = _merge_savings_envelopes(remote, local)
    assert len(merged) == 1
    assert _approx(merged[0].amount, 0.0)  # local (newer) wins -> money stays out


def test_remote_newer_wins_over_stale_local() -> None:
    # Cross-device: another device made a newer change and pushed it.
    older = (date.today() - timedelta(days=10)).isoformat()
    newer = (date.today() - timedelta(days=1)).isoformat()
    remote = [Savings("חן", 90_000.0, [MoneySnapshot(newer, 90_000.0)])]
    local = [Savings("חן", 80_000.0, [MoneySnapshot(older, 80_000.0)])]
    merged = _merge_savings_envelopes(remote, local)
    assert _approx(merged[0].amount, 90_000.0)  # remote (newer) wins


def test_new_envelopes_on_both_sides_preserved() -> None:
    remote = [Savings("A", 1.0, [MoneySnapshot("2026-01-01", 1.0)])]
    local = [Savings("B", 2.0, [MoneySnapshot("2026-01-01", 2.0)])]
    merged = _merge_savings_envelopes(remote, local)
    names = {e.name for e in merged}
    assert names == {"A", "B"}


def test_tie_prefers_local() -> None:
    d = "2026-06-22"
    remote = [Savings("שגיא", 100.0, [MoneySnapshot(d, 100.0)])]
    local = [Savings("שגיא", 0.0, [MoneySnapshot(d, 0.0)])]
    merged = _merge_savings_envelopes(remote, local)
    assert _approx(merged[0].amount, 0.0)  # same date -> keep local edit


def test_latest_snapshot_dt_ignores_future() -> None:
    future = (date.today() + timedelta(days=300)).isoformat()
    today = date.today().isoformat()
    hist = [MoneySnapshot(today, 1.0), MoneySnapshot(future, 2.0)]
    # the future point must not be treated as "most recent change"
    assert _latest_snapshot_dt(hist) == _latest_snapshot_dt([MoneySnapshot(today, 1.0)])


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
