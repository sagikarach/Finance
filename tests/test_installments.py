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


# ── הוראת קבע (direct debit) ─────────────────────────────────────────────
from datetime import date  # noqa: E402

from finance.data.installment_plan_provider import JsonFileInstallmentPlanProvider  # noqa: E402
from finance.models.installment_plan import KIND_DIRECT_DEBIT  # noqa: E402


def _debit(**kw) -> InstallmentPlan:
    base = dict(
        name="חוג", account_name="בנק", start_date="2026-01-15",
        payments_count=6, monthly_amount=250.0, charge_day=10,
        kind=KIND_DIRECT_DEBIT, original_amount=1500.0,
    )
    base.update(kw)
    return InstallmentPlan(**base)  # type: ignore[arg-type]


def test_direct_debit_schedule_same_day_each_month() -> None:
    sched = _debit().schedule(today=date(2026, 1, 1))
    # Start is the 15th, charge day the 10th → first charge next month.
    assert [p.date for p in sched] == [
        date(2026, 2, 10), date(2026, 3, 10), date(2026, 4, 10),
        date(2026, 5, 10), date(2026, 6, 10), date(2026, 7, 10),
    ]
    assert all(_approx(p.amount, 250.0) for p in sched)
    assert [p.number for p in sched] == [1, 2, 3, 4, 5, 6]


def test_direct_debit_day_31_clamps_to_month_end() -> None:
    sched = _debit(start_date="2027-01-01", charge_day=31, payments_count=3).schedule()
    assert [p.date for p in sched] == [date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31)]


def test_direct_debit_year_rollover() -> None:
    sched = _debit(start_date="2026-11-10", payments_count=3).schedule()
    assert [p.date for p in sched] == [date(2026, 11, 10), date(2026, 12, 10), date(2027, 1, 10)]


def test_direct_debit_stats_follow_calendar_not_movements() -> None:
    plan = _debit()
    # Movements are ignored — a direct debit is counted by its schedule.
    stats = plan.stats([_pay(-999.0, "2026-02-10", desc="חוג")], today=date(2026, 4, 10))
    assert stats.paid_count == 3  # Feb, Mar, Apr 10 (inclusive)
    assert stats.payments_left == 3
    assert _approx(stats.total_paid, 750.0)
    assert stats.matched_movements == []


def test_installment_plan_has_no_schedule() -> None:
    plan = InstallmentPlan(name="ספה", vendor_query="רהיטים", start_date="2026-01-01", payments_count=3)
    assert plan.schedule() == []
    assert not plan.is_direct_debit


def test_direct_debit_round_trips_through_json(tmp_path) -> None:
    provider = JsonFileInstallmentPlanProvider(tmp_path / "plans.json")
    provider.upsert_plan(_debit())
    (loaded,) = provider.list_plans()
    assert loaded.is_direct_debit
    assert _approx(loaded.monthly_amount, 250.0)
    assert loaded.charge_day == 10
    # Plans saved before this feature have no kind → installments.
    assert JsonFileInstallmentPlanProvider._deserialize({"name": "x"}).kind == "installments"  # type: ignore[union-attr]


# ── הוראת קבע → real bank movements ───────────────────────────────────────
from finance.data.action_history_provider import JsonFileActionHistoryProvider  # noqa: E402
from finance.data.bank_movement_provider import JsonFileBankMovementProvider  # noqa: E402
from finance.models.bank_movement import MovementType as _MT  # noqa: E402
from finance.models.installment_plan import direct_debit_movement_id  # noqa: E402
from finance.models.installments_service import InstallmentsService  # noqa: E402


def _svc(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "sbx"))
    plans = JsonFileInstallmentPlanProvider(tmp_path / "plans.json")
    moves = JsonFileBankMovementProvider(tmp_path / "moves.json")
    svc = InstallmentsService(
        plans_provider=plans,
        movements_provider=moves,
        history_provider=JsonFileActionHistoryProvider(tmp_path / "history.json"),
    )
    return svc, plans, moves


def test_due_movements_are_monthly_expenses_with_fixed_ids() -> None:
    plan = _debit(category="חוגים")
    due = plan.due_movements(today=date(2026, 3, 10))
    assert [(m.date, m.amount) for m in due] == [("2026-02-10", -250.0), ("2026-03-10", -250.0)]
    assert all(m.type == _MT.MONTHLY and m.account_name == "בנק" and m.category == "חוגים" for m in due)
    assert [m.id for m in due] == [direct_debit_movement_id(plan.id, 1), direct_debit_movement_id(plan.id, 2)]
    assert _debit(auto_post=False).due_movements(today=date(2026, 3, 10)) == []
    assert _debit(archived=True).due_movements(today=date(2026, 3, 10)) == []
    assert _debit(posted_count=1).due_movements(today=date(2026, 3, 10))[0].date == "2026-03-10"


def test_posting_is_idempotent_and_advances_posted_count(tmp_path, monkeypatch) -> None:
    svc, plans, moves = _svc(tmp_path, monkeypatch)
    plans.upsert_plan(_debit())
    assert svc.post_due_direct_debits(today=date(2026, 3, 10)) == 2
    assert svc.post_due_direct_debits(today=date(2026, 3, 10)) == 0  # nothing new
    assert len(moves.list_movements()) == 2
    assert plans.list_plans()[0].posted_count == 2
    assert svc.post_due_direct_debits(today=date(2026, 4, 10)) == 1  # next month
    assert len(moves.list_movements()) == 3


def test_deleted_posted_movement_is_not_recreated(tmp_path, monkeypatch) -> None:
    svc, plans, moves = _svc(tmp_path, monkeypatch)
    plans.upsert_plan(_debit())
    svc.post_due_direct_debits(today=date(2026, 3, 10))
    moves.save_movements(moves.list_movements()[1:])  # user deletes one
    assert svc.post_due_direct_debits(today=date(2026, 3, 10)) == 0
    assert len(moves.list_movements()) == 1


def test_already_present_charge_is_not_duplicated(tmp_path, monkeypatch) -> None:
    # Another device posted charge 1 (same fixed id) before we synced.
    svc, plans, moves = _svc(tmp_path, monkeypatch)
    plan = _debit()
    plans.upsert_plan(plan)
    moves.save_movements(plan.due_movements(today=date(2026, 2, 10)))
    assert svc.post_due_direct_debits(today=date(2026, 3, 10)) == 1
    assert len(moves.list_movements()) == 2
