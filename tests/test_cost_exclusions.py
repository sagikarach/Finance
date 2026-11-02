"""Excluding movements from an expense item's search (e.g. a one-off ועד בית
catch-up payment) — the item's figures skip them, and they persist."""

from types import SimpleNamespace

from finance.data.mortgage_provider import deserialize_cost, serialize_cost
from finance.models.asset_expense_service import AssetExpenseService
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.mortgage import CostItem
from finance.models.mortgage_math import (
    cost_matched_movements,
    cost_monthly_average,
    cost_paid_amount,
    yearly_cost_cycles,
)


def _mv(amount, date, desc):
    return BankMovement(
        amount=amount, date=date, account_name="בנק", category="מגורים",
        type=MovementType.ONE_TIME, description=desc,
    )


MOVES = [
    _mv(-300.0, "2026-07-01", "ועד בית"),
    _mv(-300.0, "2026-08-01", "ועד בית"),
    _mv(-1320.0, "2026-09-21", "השלמה ועד בית"),
]
CATCH_UP_ID = MOVES[2].id


def test_matches_without_exclusions_include_everything():
    cost = CostItem(name="ועד בית", query="ועד בית")
    assert len(cost_matched_movements(cost, MOVES)) == 3
    assert cost_monthly_average(cost, MOVES) == (300 + 300 + 1320) / 3


def test_excluded_movement_is_skipped_everywhere():
    cost = CostItem(name="ועד בית", query="ועד בית", excluded_movement_ids=[CATCH_UP_ID])
    assert [m.id for m in cost_matched_movements(cost, MOVES)] == [MOVES[0].id, MOVES[1].id]
    assert cost_monthly_average(cost, MOVES) == 300.0
    assert cost_paid_amount(cost, MOVES) == 600.0
    assert yearly_cost_cycles(cost, MOVES, n_cycles=1) == [(2026, 600.0)]
    # …but the full list (for the movements dialog) still shows it.
    assert len(cost_matched_movements(cost, MOVES, apply_exclusions=False)) == 3


def test_house_expenses_respect_exclusions():
    svc = SimpleNamespace(list_movements=lambda: MOVES, match_movements=lambda m: [])
    house = SimpleNamespace(
        monthly_costs=[CostItem(query="ועד בית", excluded_movement_ids=[CATCH_UP_ID])],
        yearly_costs=[],
    )
    assert AssetExpenseService(svc).house_cost_expenses(house).monthly == 300.0


def test_car_monthly_keeps_movement_excluded_from_yearly_item():
    moves = [
        _mv(-100.0, "2026-07-10", "דלק"),
        _mv(-2000.0, "2026-07-20", "ביטוח מקיף"),
        _mv(-50.0, "2026-07-25", "ביטוח מקיף שמשות"),  # not really the insurance
    ]
    moves = [BankMovement(**{**m.__dict__, "category": "רכב"}) for m in moves]
    svc = SimpleNamespace(list_movements=lambda: moves, match_movements=lambda m: [])
    car = SimpleNamespace(
        expense_category="רכב",
        yearly_costs=[CostItem(query="ביטוח מקיף", excluded_movement_ids=[moves[2].id])],
    )
    s = AssetExpenseService(svc).car_expenses(car)
    assert s.monthly == 150.0          # fuel + the excluded look-alike
    assert s.yearly == 150.0 * 12 + 2000.0


def test_exclusions_round_trip_and_old_data_loads():
    cost = CostItem(name="ועד בית", query="ועד בית", excluded_movement_ids=["a", "b"])
    assert deserialize_cost(serialize_cost(cost)) == cost
    old = deserialize_cost({"name": "ארנונה", "query": "עיריית לוד"})
    assert old is not None and old.excluded_movement_ids == []
