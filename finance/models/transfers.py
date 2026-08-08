from __future__ import annotations

from dataclasses import dataclass
from datetime import date as _date
from typing import List, Literal, Optional, Tuple

from .accounts import (
    BankAccount,
    MoneyAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
)
from .bank_movement import BankMovement, MovementType


TransferEndpointKind = Literal["bank", "saving"]


@dataclass(frozen=True)
class TransferEndpoint:
    kind: TransferEndpointKind
    account_index: int
    savings_index: int = -1


@dataclass(frozen=True)
class TransferError:
    message: str


@dataclass(frozen=True)
class TransferResult:
    accounts: List[MoneyAccount]
    error: Optional[TransferError] = None


@dataclass(frozen=True)
class TransferRequest:
    source: TransferEndpoint
    target: TransferEndpoint
    amount: float

    def apply(
        self,
        accounts: List[MoneyAccount],
        *,
        insufficient_funds_bank_msg: str = "אין מספיק כסף בחשבון המקור לביצוע ההעברה.",
        insufficient_funds_saving_msg: str = "אין מספיק כסף בחסכון המקור לביצוע ההעברה.",
    ) -> "TransferResult":
        """Apply this transfer to ``accounts`` and return the updated list (or an
        error). Pure: the input list is not mutated."""
        src = self.source
        dst = self.target
        amount = float(self.amount)

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
            return TransferResult(
                accounts=accounts, error=TransferError("בחירה לא חוקית.")
            )

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
                    accounts=accounts,
                    error=TransferError(insufficient_funds_saving_msg),
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
                        new_history.append(
                            MoneySnapshot(date=today_str, amount=new_total)
                        )
                    except Exception:
                        pass
                    updated_accounts.append(
                        BankAccount(
                            name=acc.name,
                            total_amount=new_total,
                            is_liquid=acc.is_liquid,
                            history=new_history,
                            active=getattr(acc, "active", False),
                            baseline_amount=float(
                                getattr(acc, "baseline_amount", 0.0) or 0.0
                            ),
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

    def endpoint_names(
        self, accounts: List[MoneyAccount]
    ) -> Optional[Tuple[str, str, str, str]]:
        """Resolve (source_name, target_name, source_type, target_type) for this
        transfer against ``accounts``. Savings endpoints use the
        ``"account -- saving"`` form so a specific envelope can be matched (e.g.
        by the asset funding view). Returns ``None`` if the endpoints are invalid."""
        try:
            if not (
                0 <= self.source.account_index < len(accounts)
                and 0 <= self.target.account_index < len(accounts)
            ):
                return None
            src_acc = accounts[self.source.account_index]
            dst_acc = accounts[self.target.account_index]

            src_name = src_acc.name
            dst_name = dst_acc.name
            src_type = "bank" if self.source.kind == "bank" else "saving"
            dst_type = "bank" if self.target.kind == "bank" else "saving"

            if self.source.kind == "saving" and isinstance(src_acc, SavingsAccount):
                try:
                    src_name = (
                        f"{src_acc.name} -- "
                        f"{src_acc.savings[self.source.savings_index].name}"
                    )
                except Exception:
                    pass
            if self.target.kind == "saving" and isinstance(dst_acc, SavingsAccount):
                try:
                    dst_name = (
                        f"{dst_acc.name} -- "
                        f"{dst_acc.savings[self.target.savings_index].name}"
                    )
                except Exception:
                    pass
            return (src_name, dst_name, src_type, dst_type)
        except Exception:
            return None

    def ledger_movements(
        self, accounts: List[MoneyAccount], *, today: str
    ) -> List[BankMovement]:
        """The transfer's ledger records: the outgoing movement (so views that
        aggregate money moved out of an account/saving can detect it) plus, when
        the target is a bank, the incoming movement (bank balances are derived
        from movements, so the credit must be recorded or it reverts on recalc).
        All flagged ``is_transfer`` so reports/charts ignore them."""
        names = self.endpoint_names(accounts)
        if names is None:
            return []
        src_name, dst_name, _src_type, dst_type = names
        amount = abs(float(self.amount))
        description = f"העברה מ{src_name} ל{dst_name}"

        movements = [
            BankMovement(
                amount=-amount,
                date=today,
                account_name=src_name,
                category="העברה",
                type=MovementType.ONE_TIME,
                is_transfer=True,
                description=description,
            )
        ]
        if dst_type == "bank":
            movements.append(
                BankMovement(
                    amount=amount,
                    date=today,
                    account_name=dst_name,
                    category="העברה",
                    type=MovementType.ONE_TIME,
                    is_transfer=True,
                    description=description,
                )
            )
        return movements


def funding_endpoints(
    accounts: List[MoneyAccount],
) -> List[Tuple[str, str, str, float]]:
    """יעדי מימון לבחירה: חסכונות בודדים + חשבונות בנק פעילים.

    כל פריט: ``(תווית, שם_חשבון, שם_חיסכון, יתרה)``. חשבון בנק נכלל רק כאשר
    ``active`` (ברירת מחדל: לא פעיל)."""
    out: List[Tuple[str, str, str, float]] = []
    for a in accounts:
        if isinstance(a, SavingsAccount):
            for sv in a.savings:
                out.append(
                    (
                        f"{a.name} / {sv.name}",
                        str(a.name),
                        str(sv.name),
                        float(getattr(sv, "amount", 0.0) or 0.0),
                    )
                )
        elif isinstance(a, BankAccount) and bool(getattr(a, "active", False)):
            out.append((str(a.name), str(a.name), "", float(a.total_amount)))
    return out


def transfer_endpoints(
    accounts: List[MoneyAccount],
) -> List[Tuple[str, str, int, int]]:
    """נקודות קצה להעברה בין חשבונות: חשבונות בנק פעילים + כל חיסכון.

    כל פריט: ``(תווית, סוג, אינדקס_חשבון, אינדקס_חיסכון)`` כאשר סוג הוא
    ``"bank"``/``"saving"``. חשבון בנק נכלל אלא אם ``active`` הוא False
    (ברירת מחדל: פעיל)."""
    endpoints: List[Tuple[str, str, int, int]] = []
    for acc_idx, acc in enumerate(accounts):
        if isinstance(acc, BankAccount):
            if not getattr(acc, "active", True):
                continue
            endpoints.append((acc.name, "bank", acc_idx, -1))
        elif isinstance(acc, SavingsAccount):
            for s_idx, s in enumerate(acc.savings):
                endpoints.append((f"{acc.name} — {s.name}", "saving", acc_idx, s_idx))
    return endpoints
