from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .accounts import (
    MoneyAccount,
    BankAccount,
    BudgetAccount,
    compute_total_amount,
    compute_total_liquid_amount,
)


@dataclass(frozen=True)
class AccountsOverview:
    accounts: List[MoneyAccount]
    total_all: float
    total_liquid: float

    @classmethod
    def for_home(cls, accounts: List[MoneyAccount]) -> "AccountsOverview":
        active_accounts = [
            acc
            for acc in accounts
            if not isinstance(acc, BudgetAccount)
            and (not isinstance(acc, BankAccount) or acc.active)
        ]
        total_all = compute_total_amount(active_accounts)
        total_liquid = compute_total_liquid_amount(active_accounts)
        return cls(
            accounts=active_accounts, total_all=total_all, total_liquid=total_liquid
        )

    @classmethod
    def for_bank_accounts(cls, accounts: List[MoneyAccount]) -> "AccountsOverview":
        bank_accounts: List[MoneyAccount] = [
            acc for acc in accounts if isinstance(acc, BankAccount) and acc.active
        ]
        total_all = compute_total_amount(bank_accounts)
        total_liquid = compute_total_liquid_amount(bank_accounts)
        return cls(
            accounts=bank_accounts, total_all=total_all, total_liquid=total_liquid
        )
