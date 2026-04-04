from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from typing import List, Literal, Optional

from .accounts import (
    BankAccount,
    MoneyAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
)


TransferEndpointKind = Literal["bank", "saving"]


@dataclass(frozen=True)
class TransferEndpoint:
    kind: TransferEndpointKind
    account_index: int
    savings_index: int = -1


@dataclass(frozen=True)
class TransferRequest:
    source: TransferEndpoint
    target: TransferEndpoint
    amount: float


@dataclass(frozen=True)
class TransferError:
    message: str


@dataclass(frozen=True)
class TransferResult:
    accounts: List[MoneyAccount]
    error: Optional[TransferError] = None


def apply_transfer(
    accounts: List[MoneyAccount],
    request: TransferRequest,
    *,
    insufficient_funds_bank_msg: str = "אין מספיק כסף בחשבון המקור לביצוע ההעברה.",
    insufficient_funds_saving_msg: str = "אין מספיק כסף בחסכון המקור לביצוע ההעברה.",
) -> TransferResult:
    src = request.source
    dst = request.target
    amount = float(request.amount)

    if amount <= 0:
        return TransferResult(
            accounts=accounts,
            error=TransferError("סכום ההעברה חייב להיות גדול מאפס."),
        )

    if (
        src.account_index < 0
        or src.account_index >= len(accounts)
        or dst.account_index < 0
        or dst.account_index >= len(accounts)
    ):
        return TransferResult(accounts=accounts, error=TransferError("בחירה לא חוקית."))

    src_acc = accounts[src.account_index]

    if src.kind == "bank" and isinstance(src_acc, BankAccount):
        if amount > src_acc.total_amount:
            return TransferResult(
                accounts=accounts, error=TransferError(insufficient_funds_bank_msg)
            )
    elif src.kind == "saving" and isinstance(src_acc, SavingsAccount):
        try:
            src_saving = src_acc.savings[src.savings_index]
        except Exception:
            return TransferResult(
                accounts=accounts, error=TransferError("שגיאה בחסכון.")
            )
        if amount > src_saving.amount:
            return TransferResult(
                accounts=accounts, error=TransferError(insufficient_funds_saving_msg)
            )

    bank_deltas: dict[int, float] = {}
    saving_deltas: dict[tuple[int, int], float] = {}

    if src.kind == "bank":
        bank_deltas[src.account_index] = (
            bank_deltas.get(src.account_index, 0.0) - amount
        )
    else:
        saving_deltas[(src.account_index, src.savings_index)] = (
            saving_deltas.get((src.account_index, src.savings_index), 0.0) - amount
        )

    if dst.kind == "bank":
        bank_deltas[dst.account_index] = (
            bank_deltas.get(dst.account_index, 0.0) + amount
        )
    else:
        saving_deltas[(dst.account_index, dst.savings_index)] = (
            saving_deltas.get((dst.account_index, dst.savings_index), 0.0) + amount
        )

    try:
        today_str = _date.today().isoformat()
    except Exception:
        today_str = ""

    updated_accounts: List[MoneyAccount] = []
    for acc_idx, acc in enumerate(accounts):
        if isinstance(acc, BankAccount):
            delta = bank_deltas.get(acc_idx, 0.0)
            if delta != 0.0:
                new_total = acc.total_amount + delta
                new_history = list(acc.history)
                try:
                    new_history.append(MoneySnapshot(date=today_str, amount=new_total))
                except Exception:
                    pass
                updated_accounts.append(
                    BankAccount(
                        name=acc.name,
                        total_amount=new_total,
                        is_liquid=acc.is_liquid,
                        history=new_history,
                        active=getattr(acc, "active", False),
                        baseline_amount=float(getattr(acc, "baseline_amount", 0.0) or 0.0),
                    )
                )
            else:
                updated_accounts.append(acc)
            continue

        if isinstance(acc, SavingsAccount):
            has_delta = any(key[0] == acc_idx for key in saving_deltas.keys())
            if not has_delta:
                updated_accounts.append(acc)
                continue

            new_savings: List[Savings] = []
            for s_idx, s in enumerate(acc.savings):
                delta = saving_deltas.get((acc_idx, s_idx), 0.0)
                if delta != 0.0:
                    new_amount = s.amount + delta
                    new_history = list(s.history)
                    try:
                        new_history.append(
                            MoneySnapshot(date=today_str, amount=new_amount)
                        )
                    except Exception:
                        pass
                    new_savings.append(
                        Savings(
                            name=s.name,
                            amount=new_amount,
                            history=new_history,
                        )
                    )
                else:
                    new_savings.append(s)

            updated_accounts.append(
                SavingsAccount(
                    name=acc.name,
                    total_amount=0.0,
                    is_liquid=acc.is_liquid,
                    savings=new_savings,
                )
            )
            continue

        updated_accounts.append(acc)

    return TransferResult(accounts=updated_accounts, error=None)
