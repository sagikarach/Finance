from __future__ import annotations

from typing import Dict, List, Optional

from .bank_movement import BankMovement
from .accounts_service import AccountsService


def apply_movements_to_account_balances_once(
    *,
    local_by_id: Dict[str, BankMovement],
    remote_by_id: Dict[str, dict],
    applied_balance_ids: List[str],
    accounts_service: Optional[AccountsService] = None,
) -> List[str]:
    try:
        already = set(applied_balance_ids or [])
        to_apply = [
            mid
            for mid in remote_by_id.keys()
            if mid not in already
            and not bool(remote_by_id.get(mid, {}).get("deleted", False))
        ]
        if not to_apply:
            return list(already)

        movements = [local_by_id[mid] for mid in to_apply if mid in local_by_id]
        _apply_to_account_balances(
            movements=movements, accounts_service=accounts_service
        )
        return list(already | set(to_apply))
    except Exception:
        return list(applied_balance_ids or [])


def _apply_to_account_balances(
    *, movements: List[BankMovement], accounts_service: Optional[AccountsService] = None
) -> None:
    if not movements:
        return
    try:
        from datetime import date as _date

        today = _date.today().isoformat()
    except Exception:
        today = ""

    delta_by_account: Dict[str, float] = {}
    for m in movements:
        try:
            name = str(m.account_name or "").strip()
            if not name:
                continue
            delta_by_account[name] = delta_by_account.get(name, 0.0) + float(m.amount)
        except Exception:
            continue

    if not delta_by_account:
        return

    from ..data.provider import JsonFileAccountsProvider
    from ..models.accounts import BankAccount, MoneySnapshot, MoneyAccount

    svc = accounts_service
    if svc is None:
        provider = JsonFileAccountsProvider()
        svc = AccountsService(provider)
    accounts = svc.load_accounts()

    updated: List[MoneyAccount] = []
    for acc in accounts:
        if isinstance(acc, BankAccount) and acc.name in delta_by_account:
            delta = float(delta_by_account.get(acc.name, 0.0))
            try:
                current_total = float(acc.total_amount)
            except Exception:
                current_total = 0.0
            new_total = current_total + delta
            new_history = list(acc.history)
            if today:
                new_history.append(MoneySnapshot(date=today, amount=new_total))
            updated.append(
                BankAccount(
                    name=acc.name,
                    total_amount=new_total,
                    is_liquid=acc.is_liquid,
                    history=new_history,
                    active=acc.active,
                )
            )
        else:
            updated.append(acc)

    svc.save_all(updated)
