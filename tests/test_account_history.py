from types import SimpleNamespace

from finance.models.account_history import (
    balance_timeline,
    budget_spend_by_period,
)


def _mv(amount, date, *, account="בנק", is_transfer=False):
    return SimpleNamespace(
        amount=amount, date=date, account_name=account, is_transfer=is_transfer
    )


# ── balance_timeline ────────────────────────────────────────────────────
def test_balance_timeline_running_balance_with_stored_baseline():
    acc = SimpleNamespace(name="בנק", baseline_amount=1000.0, total_amount=0.0)
    movs = [_mv(100.0, "2026-01-10"), _mv(-30.0, "2026-02-05")]
    tl = balance_timeline(acc, movs)
    assert tl.month_keys == [(2026, 1), (2026, 2)]
    # [baseline, after Jan, after Feb, today]
    assert tl.values == [1000.0, 1100.0, 1070.0, 1070.0]


def test_balance_timeline_infers_baseline_from_total_when_unset():
    # baseline 0 → inferred so final balance equals total_amount
    acc = SimpleNamespace(name="בנק", baseline_amount=0.0, total_amount=500.0)
    movs = [_mv(200.0, "2026-01-10"), _mv(-50.0, "2026-01-20")]
    tl = balance_timeline(acc, movs)
    assert round(tl.values[0], 2) == 350.0  # 500 - (200 - 50)
    assert round(tl.values[-1], 2) == 500.0


def test_balance_timeline_fills_month_gaps_contiguously():
    acc = SimpleNamespace(name="בנק", baseline_amount=0.0, total_amount=0.0)
    movs = [_mv(10.0, "2026-01-15"), _mv(10.0, "2026-04-15")]
    tl = balance_timeline(acc, movs)
    assert tl.month_keys == [(2026, 1), (2026, 2), (2026, 3), (2026, 4)]
    # baseline inferred = -20; Feb/Mar have no movements so balance flat
    assert tl.values == [-20.0, -10.0, -10.0, -10.0, 0.0, 0.0]


def test_balance_timeline_ignores_other_accounts():
    acc = SimpleNamespace(name="בנק", baseline_amount=0.0, total_amount=0.0)
    movs = [_mv(100.0, "2026-01-10", account="כרטיס")]
    tl = balance_timeline(acc, movs)
    assert tl.month_keys == []
    assert tl.values == [0.0, 0.0]


# ── budget_spend_by_period ──────────────────────────────────────────────
def test_budget_spend_buckets_before_reset_day_into_same_month():
    acc = SimpleNamespace(name="סיבוס", reset_day=10)
    movs = [_mv(-40.0, "2026-03-05", account="סיבוס"), _mv(-60.0, "2026-03-09", account="סיבוס")]  # both day<=10
    bs = budget_spend_by_period(acc, movs)
    assert bs.month_keys == [(2026, 3)]
    assert bs.spent == [100.0]


def test_budget_spend_after_reset_day_rolls_to_next_month():
    acc = SimpleNamespace(name="סיבוס", reset_day=10)
    movs = [_mv(-40.0, "2026-03-05", account="סיבוס"), _mv(-60.0, "2026-03-20", account="סיבוס")]  # 20 > 10 → April
    bs = budget_spend_by_period(acc, movs)
    assert bs.month_keys == [(2026, 3), (2026, 4)]
    assert bs.spent == [40.0, 60.0]


def test_budget_spend_excludes_income_and_transfers():
    acc = SimpleNamespace(name="סיבוס", reset_day=20)
    movs = [
        _mv(-50.0, "2026-03-15", account="סיבוס"),
        _mv(200.0, "2026-03-15", account="סיבוס"),  # income (positive) — excluded
        _mv(-30.0, "2026-03-15", account="סיבוס", is_transfer=True),  # transfer — excluded
    ]
    bs = budget_spend_by_period(acc, movs)
    assert bs.month_keys == [(2026, 3)]
    assert bs.spent == [50.0]


def test_budget_spend_empty_when_no_spend():
    acc = SimpleNamespace(name="סיבוס", reset_day=1)
    bs = budget_spend_by_period(acc, [_mv(100.0, "2026-03-15", account="סיבוס")])
    assert bs.month_keys == []
    assert bs.spent == []
