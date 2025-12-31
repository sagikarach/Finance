from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.accounts import (
    MoneyAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
    BankAccount,
    BudgetAccount,
    latest_amount_from_history,
)
from ..utils.app_paths import accounts_data_dir
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
)


class AccountsProvider(ABC):
    @abstractmethod
    def list_accounts(self) -> List[MoneyAccount]:
        raise NotImplementedError


class JsonFileAccountsProvider(AccountsProvider):
    def __init__(
        self,
        bank_accounts_path: Optional[Union[str, Path]] = None,
        savings_accounts_path: Optional[Union[str, Path]] = None,
    ) -> None:
        key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
        suffix = f"_{key}" if key else ""
        if bank_accounts_path:
            self._bank_accounts_path = Path(bank_accounts_path)
        else:
            self._bank_accounts_path = (
                accounts_data_dir() / f"bank_accounts{suffix}.json"
            )

        if savings_accounts_path:
            self._savings_accounts_path = Path(savings_accounts_path)
        else:
            self._savings_accounts_path = (
                accounts_data_dir() / f"savings_accounts{suffix}.json"
            )

    def list_accounts(self) -> List[MoneyAccount]:
        accounts: List[MoneyAccount] = []

        accounts.extend(self._load_bank_accounts())

        accounts.extend(self._load_savings_accounts())

        return accounts

    def _load_bank_accounts(self) -> List[MoneyAccount]:
        accounts: List[MoneyAccount] = []

        if not self._bank_accounts_path.exists():
            return accounts

        try:
            with self._bank_accounts_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return accounts

        if not isinstance(data, list):
            return accounts

        for item in data:
            try:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue

                kind = str(item.get("kind", "") or "").strip().lower()
                is_liquid = bool(item.get("is_liquid", False))
                raw_history = item.get("history", [])
                account_history: List[MoneySnapshot] = []

                if isinstance(raw_history, list) and len(raw_history) > 0:
                    for row in raw_history:
                        try:
                            account_history.append(
                                MoneySnapshot(
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0.0)),
                                )
                            )
                        except Exception:
                            continue

                total_amount = float(item.get("total_amount", 0.0))
                if account_history and total_amount == 0.0:
                    latest = latest_amount_from_history(account_history)
                    if latest is not None:
                        total_amount = float(latest)

                active = bool(item.get("active", False))
                try:
                    baseline_amount = float(item.get("baseline_amount", 0.0) or 0.0)
                except Exception:
                    baseline_amount = 0.0

                if kind == "budget":
                    try:
                        monthly_budget = float(item.get("monthly_budget", 0.0) or 0.0)
                    except Exception:
                        monthly_budget = 0.0
                    try:
                        reset_day = int(item.get("reset_day", 1) or 1)
                    except Exception:
                        reset_day = 1
                    last_reset_period = str(
                        item.get("last_reset_period", "") or ""
                    ).strip()
                    accounts.append(
                        BudgetAccount(
                            name=name,
                            total_amount=float(total_amount),
                            is_liquid=False,
                            history=account_history,
                            active=active,
                            monthly_budget=float(monthly_budget),
                            reset_day=int(reset_day),
                            last_reset_period=last_reset_period,
                        )
                    )
                else:
                    accounts.append(
                        BankAccount(
                            name=name,
                            total_amount=float(total_amount),
                            is_liquid=is_liquid,
                            history=account_history,
                            active=active,
                            baseline_amount=float(baseline_amount),
                        )
                    )
            except Exception:
                continue
        return accounts

    def _load_savings_accounts(self) -> List[MoneyAccount]:
        accounts: List[MoneyAccount] = []

        if not self._savings_accounts_path.exists():
            return accounts

        try:
            with self._savings_accounts_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return accounts

        if not isinstance(data, list):
            return accounts

        for item in data:
            try:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue

                is_liquid = bool(item.get("is_liquid", False))
                raw_savings = item.get("savings", [])
                savings: List[Savings] = []

                if isinstance(raw_savings, list) and len(raw_savings) > 0:
                    for savings_item in raw_savings:
                        try:
                            savings_name = str(savings_item.get("name", "")).strip()
                            if not savings_name:
                                continue

                            savings_history = savings_item.get("history", [])
                            savings_history_list: List[MoneySnapshot] = []
                            if isinstance(savings_history, list):
                                for row in savings_history:
                                    try:
                                        savings_history_list.append(
                                            MoneySnapshot(
                                                date=str(row.get("date", "")),
                                                amount=float(row.get("amount", 0.0)),
                                            )
                                        )
                                    except Exception:
                                        continue

                            amount = float(savings_item.get("amount", 0.0))
                            if savings_history_list:
                                latest = latest_amount_from_history(
                                    savings_history_list
                                )
                                if latest is not None:
                                    amount = float(latest)

                            savings.append(
                                Savings(
                                    name=savings_name,
                                    amount=amount,
                                    history=savings_history_list,
                                )
                            )
                        except Exception:
                            continue

                total_amount = float(item.get("total_amount", 0.0))
                if savings and total_amount == 0.0:
                    total_amount = sum(s.amount for s in savings)

                accounts.append(
                    SavingsAccount(
                        name=name,
                        total_amount=float(total_amount),
                        is_liquid=is_liquid,
                        savings=savings,
                    )
                )
            except Exception:
                continue
        return accounts

    def save_savings_accounts(self, accounts: List[SavingsAccount]) -> None:
        self._savings_accounts_path.parent.mkdir(parents=True, exist_ok=True)

        json_data: List[Dict[str, Any]] = []
        for account in accounts:
            savings_list: List[Dict[str, Any]] = []
            account_dict: Dict[str, Any] = {
                "name": account.name,
                "is_liquid": account.is_liquid,
                "total_amount": account.total_amount,
                "savings": savings_list,
            }
            for savings_item in account.savings:
                savings_dict: Dict[str, Any] = {
                    "name": savings_item.name,
                    "amount": savings_item.amount,
                    "history": [
                        {"date": snapshot.date, "amount": snapshot.amount}
                        for snapshot in savings_item.history
                    ],
                }
                savings_list.append(savings_dict)
            json_data.append(account_dict)

        with self._savings_accounts_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    def save_bank_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._bank_accounts_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = []
        for account in accounts:
            if not isinstance(account, (BankAccount, BudgetAccount)):
                continue
            account_dict = {
                "name": account.name,
                "is_liquid": account.is_liquid,
                "total_amount": account.total_amount,
                "active": bool(getattr(account, "active", False)),
                "history": [
                    {"date": snap.date, "amount": snap.amount}
                    for snap in list(getattr(account, "history", []) or [])
                ],
            }
            if isinstance(account, BankAccount):
                account_dict["baseline_amount"] = float(
                    getattr(account, "baseline_amount", 0.0) or 0.0
                )
            if isinstance(account, BudgetAccount):
                account_dict["kind"] = "budget"
                account_dict["monthly_budget"] = float(account.monthly_budget)
                account_dict["reset_day"] = int(account.reset_day)
                account_dict["last_reset_period"] = str(account.last_reset_period or "")
            json_data.append(account_dict)

        with self._bank_accounts_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
