from types import SimpleNamespace

from finance.models.bank_movement import BankMovement, MovementType
from finance.models.movement_filters import movements_for_month


def _mv(amount, date, *, mtype=MovementType.ONE_TIME, category="", is_transfer=False):
    return BankMovement(
        amount=amount,
        date=date,
        account_name="בנק",
        category=category,
        type=mtype,
        is_transfer=is_transfer,
    )


def test_filters_by_type_and_month():
    movs = [
        _mv(-10, "2026-03-05"),
        _mv(-20, "2026-03-20", mtype=MovementType.MONTHLY),  # wrong type
        _mv(-30, "2026-04-05"),  # wrong month
    ]
    out = movements_for_month(movs, MovementType.ONE_TIME, 2026, 3)
    assert [m.amount for m in out] == [-10]


def test_excludes_transfers_and_transfer_category():
    movs = [
        _mv(-10, "2026-03-05"),
        _mv(-20, "2026-03-06", is_transfer=True),
        _mv(-30, "2026-03-07", category="העברה"),
        _mv(-40, "2026-03-08", category=" העברה "),  # trimmed → excluded
    ]
    out = movements_for_month(movs, MovementType.ONE_TIME, 2026, 3)
    assert [m.amount for m in out] == [-10]


def test_sorted_newest_first():
    movs = [
        _mv(-10, "2026-03-01"),
        _mv(-20, "2026-03-20"),
        _mv(-30, "2026-03-10"),
    ]
    out = movements_for_month(movs, MovementType.ONE_TIME, 2026, 3)
    assert [m.date for m in out] == ["2026-03-20", "2026-03-10", "2026-03-01"]


def test_empty_when_nothing_matches():
    assert movements_for_month([], MovementType.ONE_TIME, 2026, 3) == []


def test_duck_typed_objects_are_accepted():
    movs = [SimpleNamespace(amount=-5, date="2026-03-01", type=MovementType.ONE_TIME)]
    out = movements_for_month(movs, MovementType.ONE_TIME, 2026, 3)
    assert len(out) == 1
