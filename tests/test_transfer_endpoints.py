from finance.models.accounts import BankAccount, Savings, SavingsAccount
from finance.models.transfers import funding_endpoints, transfer_endpoints


def _bank(name, total, *, active):
    return BankAccount(name=name, total_amount=total, is_liquid=True, active=active)


def _savings(name, subs):
    return SavingsAccount(
        name=name,
        total_amount=0.0,
        is_liquid=True,
        savings=[Savings(name=n, amount=a) for n, a in subs],
    )


# ── funding_endpoints (asset funding picker) ─────────────────────────────
def test_funding_endpoints_includes_savings_and_active_banks_only():
    accts = [
        _bank("עו״ש", 1000.0, active=True),
        _bank("ישן", 500.0, active=False),  # inactive bank → excluded
        _savings("קופה", [("א", 300.0), ("ב", 200.0)]),
    ]
    out = funding_endpoints(accts)
    assert out == [
        ("עו״ש", "עו״ש", "", 1000.0),
        ("קופה / א", "קופה", "א", 300.0),
        ("קופה / ב", "קופה", "ב", 200.0),
    ]


def test_funding_endpoints_bank_default_inactive_excluded():
    # a bank with no explicit active flag defaults to inactive here → excluded
    accts = [BankAccount(name="x", total_amount=5.0, is_liquid=True)]
    assert funding_endpoints(accts) == []


# ── transfer_endpoints (move-between-accounts dialog) ────────────────────
def test_transfer_endpoints_index_based_active_banks_and_all_savings():
    accts = [
        _bank("עו״ש", 1000.0, active=True),
        _bank("ישן", 500.0, active=False),  # inactive → excluded
        _savings("קופה", [("א", 300.0)]),
    ]
    out = transfer_endpoints(accts)
    assert out == [
        ("עו״ש", "bank", 0, -1),
        ("קופה — א", "saving", 2, 0),
    ]


def test_transfer_endpoints_excludes_inactive_bank():
    # a real BankAccount defaults active=False → excluded; active=True → included
    assert transfer_endpoints([_bank("x", 5.0, active=False)]) == []
    assert transfer_endpoints([_bank("x", 5.0, active=True)]) == [("x", "bank", 0, -1)]
