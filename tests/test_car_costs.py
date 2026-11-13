"""Car ownership costs: only the categories selected for the car, cost items
first, user exclusions kept, each movement counted once (no Qt)."""

from __future__ import annotations

from finance.data.mortgage_provider import deserialize_mortgage, serialize_mortgage
from finance.models import category_tree as ct
from finance.models.asset_expense_service import AssetExpenseService
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.car_costs import (
    car_category_selection,
    car_cost_breakdown,
    default_car_categories,
)
from finance.models.category_tree import CategoryNode, CategoryTree, default_outcome_nodes
from finance.models.mortgage import AssetKind, CostItem, Mortgage

TREE = CategoryTree(default_outcome_nodes(), {"רכב": "רכב ותחבורה"})
FUEL, SERVICE, INSURANCE = "דלק", "טיפולים ותיקונים", "ביטוח רכב"
TAXI, RENTAL, PARENT = "תחבורה ציבורית ומוניות", "השכרת רכב", "רכב ותחבורה"


def mv(mid, amount, month, category, desc="x", *, transfer=False):
    return BankMovement(
        id=mid, amount=amount, date=f"2026-{month:02d}-10", account_name="בנק",
        category=category, type=MovementType.ONE_TIME, description=desc,
        is_transfer=transfer,
    )


def car(**kw):
    base = dict(id="car", name="i35", kind=AssetKind.CAR, expense_category="")
    base.update(kw)
    return Mortgage(**base)


class _Svc:
    def __init__(self, movements):
        self._m = movements

    def list_movements(self):
        return self._m

    def match_movements(self, _m):
        return []


MOVES = [
    mv("f1", -400, 1, FUEL, "פז"), mv("f2", -300, 2, FUEL, "פז"),
    mv("s1", -900, 2, SERVICE, "מוסך"),
    mv("t1", -50, 1, TAXI, "גט"), mv("t2", -60, 2, TAXI, "רב קו"),
    mv("r1", -700, 2, RENTAL, "שלמה סיקסט"),
    mv("p1", -31500, 1, PARENT, "קניית רכב"),
    mv("i1", -1200, 1, INSURANCE, "ביטוח מקיף"),
    mv("g1", -80, 1, "סופר ומכולת", "שופרסל"),
    mv("x1", -500, 2, FUEL, "העברה לפז", transfer=True),
]


def test_legacy_setting_excludes_public_transport_taxis_and_rental():
    sel = car_category_selection(car(), TREE)  # stored "" → default "רכב"
    assert sel.migrated
    assert set(sel.categories) == set(default_car_categories(TREE))
    assert TAXI not in sel.categories and RENTAL not in sel.categories
    assert sel.review == (PARENT,)  # broad parent kept for review, not counted
    bd = car_cost_breakdown(car(), MOVES, TREE)
    ids = {m.id for m in bd.monthly}
    assert ids == {"f1", "f2", "s1", "i1"}
    assert {m.id for m in bd.review} == {"p1"}  # shown, not counted


def test_only_selected_categories_count_and_a_parent_means_parent_only():
    c = car(expense_categories=[FUEL, PARENT])
    bd = car_cost_breakdown(c, MOVES, TREE)
    assert {m.id for m in bd.monthly} == {"f1", "f2", "p1"}  # no service/insurance/taxi
    assert bd.review == []


def test_cost_item_takes_precedence_and_nothing_is_counted_twice():
    item = CostItem(name="ביטוח", query="ביטוח מקיף", renewal_month=1)
    c = car(expense_categories=[FUEL, INSURANCE], yearly_costs=[item])
    bd = car_cost_breakdown(c, MOVES, TREE)
    assert {m.id for m in bd.cost_items} == {"i1"}
    assert "i1" not in {m.id for m in bd.monthly}
    all_ids = [m.id for m in bd.monthly + bd.cost_items + bd.excluded + bd.review]
    assert len(all_ids) == len(set(all_ids))
    ct.set_active_tree_override(TREE)
    cx = AssetExpenseService(_Svc(MOVES)).car_expenses(c)
    assert round(cx.monthly, 2) == 350.0  # fuel (400 + 300) / 2 months
    assert round(cx.yearly, 2) == round(350.0 * 12 + 1200.0, 2)  # + the item's cycle


def test_user_exclusions_are_kept_and_restorable():
    c = car(expense_categories=[FUEL, SERVICE], excluded_movement_ids=["s1"])
    bd = car_cost_breakdown(c, MOVES, TREE)
    assert {m.id for m in bd.monthly} == {"f1", "f2"}
    assert {m.id for m in bd.excluded} == {"s1"}  # still visible for inspection
    restored = car_cost_breakdown(car(expense_categories=[FUEL, SERVICE]), MOVES, TREE)
    assert "s1" in {m.id for m in restored.monthly}


def test_transfers_and_income_never_count():
    bd = car_cost_breakdown(car(expense_categories=[FUEL]), MOVES + [mv("in", 100, 1, FUEL)], TREE)
    assert {m.id for m in bd.monthly} == {"f1", "f2"}


def test_monthly_yearly_and_category_breakdown_agree():
    ct.set_active_tree_override(TREE)
    c = car(expense_categories=[FUEL, SERVICE])
    svc = AssetExpenseService(_Svc(MOVES))
    bd = svc.car_breakdown(c)
    cx = svc.car_expenses(c)
    total = sum(t for _c, t, _n in bd.monthly_by_category())
    assert round(total / cx.months_of_data, 2) == round(cx.monthly, 2)
    assert round(cx.yearly, 2) == round(cx.monthly * 12, 2)  # no yearly items
    assert [c for c, _t, _n in bd.monthly_by_category()] == [SERVICE, FUEL]


def test_old_settings_load_unchanged_and_new_field_round_trips():
    old = {"id": "car", "name": "i35", "kind": "רכב", "expense_category": "רכב"}
    loaded = deserialize_mortgage(old)
    assert loaded is not None and loaded.expense_categories is None  # never chosen
    assert loaded.expense_category == "רכב"  # stored value untouched
    again = deserialize_mortgage(serialize_mortgage(replace_list(loaded, [FUEL, "חניה פרטית"])))
    assert again is not None and again.expense_categories == [FUEL, "חניה פרטית"]


def replace_list(m, names):
    from dataclasses import replace

    return replace(m, expense_categories=names)


def test_custom_unknown_and_other_broad_references_are_not_guessed():
    custom = car_category_selection(car(expense_category="רכב משפחתי"), TREE)
    assert custom.categories == ("רכב משפחתי",) and not custom.review
    leaf = car_category_selection(car(expense_category=FUEL), TREE)
    assert leaf.categories == (FUEL,) and not leaf.review
    broad = car_category_selection(car(expense_category="מזון"), TREE)
    assert broad.categories == () and broad.review == ("מזון",)
    flat = car_category_selection(car(expense_category=""), CategoryTree([]))
    assert flat.categories == ("רכב",)  # no hierarchy: the old exact name


def test_renamed_ownership_subcategory_is_found_by_its_stable_id():
    nodes = [CategoryNode(n.id, "דלק וחשמל" if n.id == "transport.fuel" else n.name, n.parent_id)
             for n in default_outcome_nodes()]
    sel = car_category_selection(car(), CategoryTree(nodes, {"רכב": "רכב ותחבורה"}))
    assert "דלק וחשמל" in sel.categories


def test_snapshot_publishes_car_figures_for_mobile(monkeypatch):
    from finance.models.mortgage_service import MortgageService

    ct.set_active_tree_override(TREE)
    svc = MortgageService.__new__(MortgageService)
    monkeypatch.setattr(svc, "list_movements", lambda: MOVES, raising=False)
    monkeypatch.setattr(svc, "match_movements", lambda _m: [], raising=False)
    monkeypatch.setattr(svc, "paid_payments_count", lambda _m: 0, raising=False)
    monkeypatch.setattr(svc, "prepaid_amount", lambda _m: 0.0, raising=False)
    monkeypatch.setattr(svc, "remaining_debt", lambda _m: 0.0, raising=False)
    snap = svc.balance_snapshot(car(expense_categories=[FUEL]))
    assert round(snap["car_monthly_cost"], 2) == 350.0
    assert round(snap["car_yearly_cost"], 2) == 4200.0
    house = svc.balance_snapshot(Mortgage(id="h", name="house"))
    assert "car_monthly_cost" not in house



def test_purchase_price_is_never_an_operating_cost():
    ct.set_active_tree_override(TREE)
    svc = AssetExpenseService(_Svc(MOVES))
    for c in (car(), car(expense_categories=list(default_car_categories(TREE)))):
        bd = svc.car_breakdown(c)
        counted = {m.id for m in bd.monthly + bd.cost_items}
        assert "p1" not in counted  # ₪31,500 "קניית רכב" on the broad parent
        cx = svc.car_expenses(c)
        assert cx.yearly < 31500
