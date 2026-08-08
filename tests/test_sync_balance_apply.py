"""Applying pulled movements to account balances — idempotently, once each.

Uses a real AccountsService pointed at tmp files (injected, so nothing touches
the real workspace) to check the delta math and the applied-ids bookkeeping."""

from finance.data.provider import JsonFileAccountsProvider
from finance.models.accounts import BankAccount
from finance.models.accounts_service import AccountsService
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.firebase_sync_balance_apply import (
    apply_movements_to_account_balances_once,
)


def _svc(tmp_path, *, start=1000.0):
    prov = JsonFileAccountsProvider(
        bank_accounts_path=tmp_path / "bank.json",
        savings_accounts_path=tmp_path / "sav.json",
    )
    prov.save_bank_accounts(
        [BankAccount(name="בנק", total_amount=start, is_liquid=True)]
    )
    return AccountsService(prov), prov


def _bank_total(prov):
    return [a for a in prov.list_accounts() if isinstance(a, BankAccount)][0].total_amount


def _mv(mid, amount):
    return BankMovement(
        amount=amount, date="2026-01-01", account_name="בנק",
        category="מזון", type=MovementType.ONE_TIME, id=mid,
    )


def test_apply_adjusts_matching_bank_balance(tmp_path):
    svc, prov = _svc(tmp_path)
    applied = apply_movements_to_account_balances_once(
        local_by_id={"a": _mv("a", -250.0)},
        remote_by_id={"a": {"amount": -250.0, "date": "2026-01-01", "account_name": "בנק"}},
        applied_balance_ids=[],
        accounts_service=svc,
    )
    assert "a" in applied
    assert _bank_total(prov) == 750.0


def test_apply_is_idempotent(tmp_path):
    svc, prov = _svc(tmp_path)
    local = {"a": _mv("a", -250.0)}
    remote = {"a": {"amount": -250.0, "date": "2026-01-01", "account_name": "בנק"}}
    first = apply_movements_to_account_balances_once(
        local_by_id=local, remote_by_id=remote, applied_balance_ids=[], accounts_service=svc
    )
    # replaying with 'a' already recorded must not double-apply the delta
    second = apply_movements_to_account_balances_once(
        local_by_id=local, remote_by_id=remote, applied_balance_ids=first, accounts_service=svc
    )
    assert set(second) == {"a"}
    assert _bank_total(prov) == 750.0


def test_apply_skips_deleted_remote(tmp_path):
    svc, prov = _svc(tmp_path)
    applied = apply_movements_to_account_balances_once(
        local_by_id={"a": _mv("a", -250.0)},
        remote_by_id={"a": {"deleted": True, "amount": -250.0}},
        applied_balance_ids=[],
        accounts_service=svc,
    )
    assert applied == []
    assert _bank_total(prov) == 1000.0  # untouched
