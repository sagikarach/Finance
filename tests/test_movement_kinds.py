from types import SimpleNamespace

from finance.models.bank_movement import (
    BankMovement,
    ExpenseMovement,
    IncomeMovement,
    MovementKind,
    MovementType,
    TransferMovement,
    build_movement,
    counts_as_transfer,
    deserialize_bank_movement,
)


def _bm(amount, **kw):
    return BankMovement(
        amount=amount,
        date="2026-01-01",
        account_name="בנק",
        category=kw.pop("category", "מזון"),
        type=MovementType.ONE_TIME,
        **kw,
    )


def test_kind_income_expense_by_sign():
    assert _bm(100).kind == MovementKind.INCOME
    assert _bm(-100).kind == MovementKind.EXPENSE


def test_kind_transfer_from_flag_category_or_endpoints():
    assert _bm(-100, is_transfer=True).kind == MovementKind.TRANSFER
    assert _bm(-100, category="העברה").kind == MovementKind.TRANSFER
    assert _bm(-100, transfer_from="בנק", transfer_to="קופה").kind == MovementKind.TRANSFER


def test_build_movement_returns_kind_specific_view():
    assert isinstance(build_movement(_bm(100)), IncomeMovement)
    assert isinstance(build_movement(_bm(-100)), ExpenseMovement)
    assert isinstance(build_movement(_bm(-100, is_transfer=True)), TransferMovement)


def test_income_and_expense_views_expose_category():
    inc = build_movement(_bm(100, category="משכורת"))
    assert isinstance(inc, IncomeMovement) and inc.category == "משכורת"


def test_transfer_view_exposes_both_accounts_from_structured_fields():
    t = build_movement(
        _bm(-500, is_transfer=True, transfer_from="בנק", transfer_to="קופה")
    )
    assert isinstance(t, TransferMovement)
    assert t.from_account == "בנק"
    assert t.to_account == "קופה"


def test_transfer_view_infers_side_for_legacy_rows():
    # a legacy transfer without structured fields: the affected account is the
    # source when money left it, the target when money arrived
    out = build_movement(_bm(-500, category="העברה"))
    assert out.from_account == "בנק" and out.to_account == ""
    inc = build_movement(_bm(500, category="העברה"))
    assert inc.to_account == "בנק" and inc.from_account == ""


def test_deserialize_reads_transfer_endpoints():
    m = deserialize_bank_movement(
        {
            "amount": -500,
            "date": "2026-01-01",
            "account_name": "בנק",
            "category": "העברה",
            "is_transfer": True,
            "transfer_from": "בנק",
            "transfer_to": "קופה",
        }
    )
    assert m is not None
    assert m.transfer_from == "בנק" and m.transfer_to == "קופה"
    assert m.kind == MovementKind.TRANSFER


def test_counts_as_transfer_helper_handles_all_signals_and_duck_types():
    # the reporting consumers pass duck-typed objects; the one helper must work
    assert counts_as_transfer(SimpleNamespace(is_transfer=True))
    assert counts_as_transfer(SimpleNamespace(category="העברה"))  # category-only!
    assert counts_as_transfer(SimpleNamespace(transfer_from="בנק"))
    assert not counts_as_transfer(SimpleNamespace(category="מזון", amount=-10))
    # and on a real record
    assert counts_as_transfer(_bm(-10, category="העברה"))
    assert not counts_as_transfer(_bm(-10, category="מזון"))


def test_transfer_creation_populates_both_endpoints():
    from finance.models.accounts import BankAccount
    from finance.models.transfers import TransferEndpoint, TransferRequest

    accounts = [
        BankAccount(name="בנק", total_amount=1000.0, is_liquid=True),
        BankAccount(name="קופה", total_amount=0.0, is_liquid=True),
    ]
    req = TransferRequest(
        source=TransferEndpoint(kind="bank", account_index=0),
        target=TransferEndpoint(kind="bank", account_index=1),
        amount=500.0,
    )
    movs = req.ledger_movements(accounts, today="2026-01-01")
    assert movs, "expected transfer ledger movements"
    for m in movs:
        assert m.transfer_from == "בנק" and m.transfer_to == "קופה"
        assert m.kind == MovementKind.TRANSFER
