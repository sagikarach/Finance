from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from typing import List, Optional

from .accounts import BankAccount, MoneySnapshot


@dataclass(frozen=True)
class BankSettingsRowInput:
    name: str
    is_active: bool
    starter_amount_text: str
    current_account: Optional[BankAccount]


def apply_bank_settings(rows: List[BankSettingsRowInput]) -> List[BankAccount]:
    today_str = _date.today().isoformat()
    updated_bank_accounts: List[BankAccount] = []

    for row in rows:
        is_active = row.is_active
        amount_text = row.starter_amount_text.strip()
        current_account = row.current_account

        if current_account is not None:
            account = current_account
            was_inactive = not account.active
            is_being_activated = is_active and was_inactive
        else:
            account = BankAccount(
                name=row.name,
                total_amount=0.0,
                is_liquid=row.name == "מזומן",
                history=[],
                active=False,
            )
            is_being_activated = is_active

        new_history = list(account.history)
        new_total = account.total_amount

        if is_being_activated and amount_text:
            try:
                starter_amount = float(amount_text)
                if starter_amount > 0:
                    new_history.append(
                        MoneySnapshot(date=today_str, amount=starter_amount)
                    )
                    new_total = starter_amount
            except (ValueError, TypeError):
                pass

        updated_bank_accounts.append(
            BankAccount(
                name=account.name,
                total_amount=new_total,
                is_liquid=account.is_liquid,
                history=new_history,
                active=is_active,
            )
        )

    return updated_bank_accounts
