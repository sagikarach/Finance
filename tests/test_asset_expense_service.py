from types import SimpleNamespace

from finance.models.bank_movement import BankMovement, MovementType
from finance.models.mortgage import CostItem
from finance.models.asset_expense_service import AssetExpenseService


def _mv(amount, year, month, *, category="", desc=""):
    return BankMovement(
        amount=amount,
        date=f"{year}-{month:02d}-15",
        account_name="בנק",
        category=category,
        type=MovementType.ONE_TIME,
        description=desc,
    )


class _FakeService:
    """Stands in for MortgageService: fixed movements + controllable matches."""

    def __init__(self, movements, matched=None):
        self._movements = movements
        self._matched = matched if matched is not None else []

    def list_movements(self):
        return self._movements

    def match_movements(self, mortgage):
        return self._matched


def _house(monthly=None, yearly=None):
    return SimpleNamespace(
        monthly_costs=monthly or [], yearly_costs=yearly or [], expense_category=""
    )


def test_house_monthly_from_movement_search_averages_over_months():
    # ארנונה: 100, 200, 300 across three months -> avg 200/mo
    movs = [
        _mv(-100, 2026, 1, desc="ארנונה"),
        _mv(-200, 2026, 2, desc="ארנונה"),
        _mv(-300, 2026, 3, desc="ארנונה"),
    ]
    exp = AssetExpenseService(_FakeService(movs))
    s = exp.house_cost_expenses(_house(monthly=[CostItem(name="ארנונה", query="ארנונה")]))
    assert round(s.monthly, 2) == 200.0
    assert round(s.yearly, 2) == 2400.0


def test_house_typed_amount_when_no_search():
    exp = AssetExpenseService(_FakeService([]))
    s = exp.house_cost_expenses(_house(monthly=[CostItem(name="ועד", amount=50.0)]))
    assert round(s.monthly, 2) == 50.0
    assert round(s.yearly, 2) == 600.0


def test_house_yearly_item_folds_into_monthly():
    # a yearly item paid once (1200) amortises to 100/mo on top of monthly costs
    movs = [_mv(-1200, 2026, 3, desc="ביטוח מבנה")]
    exp = AssetExpenseService(_FakeService(movs))
    m = _house(
        monthly=[CostItem(name="ועד", amount=50.0)],
        yearly=[CostItem(name="ביטוח מבנה", query="ביטוח מבנה", renewal_month=1)],
    )
    s = exp.house_cost_expenses(m)
    assert round(s.monthly, 2) == 150.0  # 50 + 1200/12
    assert round(s.yearly, 2) == 1800.0


def test_house_empty_is_zero():
    s = AssetExpenseService(_FakeService([])).house_cost_expenses(_house())
    assert s.monthly == 0.0 and s.yearly == 0.0


def test_mortgage_actual_monthly_averages_matched_payments():
    matched = [_mv(-5000, 2026, 1), _mv(-5000, 2026, 2), _mv(-5000, 2026, 3)]
    exp = AssetExpenseService(_FakeService([], matched=matched))
    assert round(exp.mortgage_actual_monthly(_house()), 2) == 5000.0


def test_mortgage_actual_zero_when_no_matches():
    assert AssetExpenseService(_FakeService([], matched=[])).mortgage_actual_monthly(_house()) == 0.0


def test_house_all_in_is_mortgage_plus_house():
    movs = [_mv(-300, 2026, 1, desc="ארנונה")]
    matched = [_mv(-5000, 2026, 1)]
    exp = AssetExpenseService(_FakeService(movs, matched=matched))
    m = _house(monthly=[CostItem(name="ארנונה", query="ארנונה")])
    ai = exp.house_all_in(m)
    assert round(ai.house_monthly, 2) == 300.0
    assert round(ai.mortgage_monthly, 2) == 5000.0
    assert round(ai.total_monthly, 2) == 5300.0
    assert round(ai.total_yearly, 2) == 63600.0


def test_car_excludes_yearly_items_from_monthly_and_adds_them_annually():
    # רכב category: fuel 400/mo (2 months) + one insurance 1200 (a yearly item)
    movs = [
        _mv(-400, 2026, 1, category="רכב", desc="דלק"),
        _mv(-400, 2026, 2, category="רכב", desc="דלק"),
        _mv(-1200, 2026, 1, category="רכב", desc="ביטוח מקיף"),
    ]
    exp = AssetExpenseService(_FakeService(movs))
    m = SimpleNamespace(
        monthly_costs=[],
        yearly_costs=[CostItem(name="ביטוח מקיף", query="ביטוח מקיף", renewal_month=1)],
        expense_category="רכב",
    )
    car = exp.car_expenses(m)
    # monthly recurring excludes the insurance -> just fuel: (400+400)/2 = 400
    assert round(car.monthly, 2) == 400.0
    # yearly = recurring*12 + the yearly item cycle (1200)
    assert round(car.yearly, 2) == 6000.0
    assert car.months_of_data == 2
