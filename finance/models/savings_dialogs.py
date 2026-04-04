from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .accounts import MoneyAccount, SavingsAccount


@dataclass(frozen=True)
class SavingsAccountForm:
    name: str
    is_liquid: bool


@dataclass(frozen=True)
class SavingsAccountValidationContext:
    existing_names: List[str]
    current_name: Optional[str] = None


@dataclass(frozen=True)
class SavingsAccountValidationError:
    message: str


def validate_savings_account_form(
    form: SavingsAccountForm,
    ctx: SavingsAccountValidationContext,
) -> Optional[SavingsAccountValidationError]:
    name = form.name.strip()
    if not name:
        return SavingsAccountValidationError("שם לא יכול להיות ריק")

    if name.casefold() in {n.casefold() for n in ctx.existing_names}:
        return SavingsAccountValidationError(f"שם '{name}' כבר קיים. אנא בחר שם אחר.")

    return None


def form_to_new_savings_account(form: SavingsAccountForm) -> SavingsAccount:
    name = form.name.strip()
    return SavingsAccount(
        name=name,
        total_amount=0.0,
        is_liquid=form.is_liquid,
        savings=[],
    )


def form_to_updated_savings_account(
    original: SavingsAccount,
    form: SavingsAccountForm,
) -> SavingsAccount:
    name = form.name.strip()
    return SavingsAccount(
        name=name,
        total_amount=original.total_amount,
        is_liquid=form.is_liquid,
        savings=original.savings,
    )


def resolve_savings_account_to_remove(
    accounts: List[MoneyAccount],
    selected: SavingsAccount,
) -> Optional[MoneyAccount]:
    for acc in accounts:
        if acc is selected:
            return acc

    for acc in accounts:
        if isinstance(acc, SavingsAccount) and acc.name == selected.name:
            return acc

    return None


def remove_savings_account(
    accounts: List[MoneyAccount],
    selected: SavingsAccount,
) -> List[MoneyAccount]:
    target = resolve_savings_account_to_remove(accounts, selected)
    if target is None:
        return accounts
    return [acc for acc in accounts if acc is not target]
