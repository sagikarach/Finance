from finance.models.accounts import BankAccount, SavingsAccount
from finance.models.accounts_service import AccountsService


class _FakeProvider:
    """Not a JsonFileAccountsProvider, so AccountsService.save_all no-ops
    (nothing is written to disk / Firebase during the test)."""

    def __init__(self, existing):
        self._existing = list(existing)

    def list_accounts(self):
        return list(self._existing)


def test_carries_disk_baseline_over_by_name():
    disk = [
        BankAccount(name="עו״ש", total_amount=100.0, is_liquid=True, baseline_amount=555.0)
    ]
    svc = AccountsService(_FakeProvider(disk))
    # the in-memory copy lost its baseline (0.0) — save must restore it from disk
    mem = [
        BankAccount(name="עו״ש", total_amount=250.0, is_liquid=True, baseline_amount=0.0),
        SavingsAccount(name="קופה", total_amount=0.0, is_liquid=True),
    ]
    merged = svc.save_preserving_bank_baselines(mem)

    bank = [a for a in merged if isinstance(a, BankAccount)][0]
    assert bank.total_amount == 250.0  # new value preserved
    assert bank.baseline_amount == 555.0  # baseline restored from disk
    assert any(isinstance(a, SavingsAccount) for a in merged)  # non-bank passthrough


def test_keeps_own_baseline_when_account_is_new_on_disk():
    svc = AccountsService(_FakeProvider([]))  # nothing persisted yet
    mem = [BankAccount(name="new", total_amount=10.0, is_liquid=True, baseline_amount=42.0)]
    merged = svc.save_preserving_bank_baselines(mem)
    assert merged[0].baseline_amount == 42.0
