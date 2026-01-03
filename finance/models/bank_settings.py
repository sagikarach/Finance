from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .accounts import BankAccount


@dataclass(frozen=True)
class BankSettingsRowInput:
    name: str
    is_active: bool
    starter_amount_text: str
    current_account: Optional[BankAccount]


def apply_bank_settings(rows: List[BankSettingsRowInput]) -> List[BankAccount]:
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
        try:
            baseline_amount = float(getattr(account, "baseline_amount", 0.0) or 0.0)
        except Exception:
            baseline_amount = 0.0

        # Starter amount is a baseline (not "set current balance").
        if (is_being_activated or is_active) and amount_text:
            try:
                starter_amount = float(amount_text)
                if starter_amount >= 0:
                    baseline_amount = starter_amount
            except (ValueError, TypeError):
                pass

        updated_bank_accounts.append(
            BankAccount(
                name=account.name,
                total_amount=new_total,
                is_liquid=account.is_liquid,
                history=new_history,
                active=is_active,
                baseline_amount=float(baseline_amount),
            )
        )

    return updated_bank_accounts
