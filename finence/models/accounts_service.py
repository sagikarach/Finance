from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from .accounts import BankAccount, MoneyAccount, SavingsAccount
from .bank_settings import BankSettingsRowInput, apply_bank_settings
from .savings_dialogs import (
    SavingsAccountForm,
    form_to_new_savings_account,
    form_to_updated_savings_account,
    remove_savings_account,
)
from .transfers import TransferRequest, TransferResult, apply_transfer


@dataclass
class AccountsService:
    provider: AccountsProvider

    def load_accounts(self) -> List[MoneyAccount]:
        return self.provider.list_accounts()

    def add_savings_account(
        self,
        accounts: List[MoneyAccount],
        form: SavingsAccountForm,
    ) -> List[MoneyAccount]:
        new_acc = form_to_new_savings_account(form)
        return accounts + [new_acc]

    def edit_savings_account(
        self,
        accounts: List[MoneyAccount],
        original: SavingsAccount,
        form: SavingsAccountForm,
    ) -> List[MoneyAccount]:
        updated = form_to_updated_savings_account(original, form)
        out: List[MoneyAccount] = []
        replaced = False
        for acc in accounts:
            if acc is original and not replaced:
                out.append(updated)
                replaced = True
            else:
                out.append(acc)
        if not replaced:
            name = original.name
            out = [
                updated if isinstance(acc, SavingsAccount) and acc.name == name else acc
                for acc in out
            ]
        return out

    def delete_savings_account(
        self,
        accounts: List[MoneyAccount],
        selected: SavingsAccount,
    ) -> List[MoneyAccount]:
        return remove_savings_account(accounts, selected)

    def apply_transfer_request(
        self,
        accounts: List[MoneyAccount],
        request: TransferRequest,
    ) -> TransferResult:
        return apply_transfer(accounts, request)

    def apply_bank_settings_rows(
        self,
        rows: List[BankSettingsRowInput],
    ) -> List[MoneyAccount]:
        updated_bank_accounts = apply_bank_settings(rows)
        existing = self.provider.list_accounts()
        savings_only = [acc for acc in existing if isinstance(acc, SavingsAccount)]
        merged: List[MoneyAccount] = []
        merged.extend(updated_bank_accounts)
        merged.extend(savings_only)
        return merged

    def save_all(self, accounts: List[MoneyAccount]) -> None:
        if not isinstance(self.provider, JsonFileAccountsProvider):
            return

        savings_accounts = [acc for acc in accounts if isinstance(acc, SavingsAccount)]
        bank_accounts = [acc for acc in accounts if isinstance(acc, BankAccount)]

        try:
            self.provider.save_savings_accounts(savings_accounts)  # type: ignore[arg-type]
        except Exception:
            pass
        try:
            self.provider.save_bank_accounts(bank_accounts)  # type: ignore[arg-type]
        except Exception:
            pass
