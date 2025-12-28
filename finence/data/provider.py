from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union
import json

from ..models.accounts import (
    MoneyAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
    BankAccount,
    latest_amount_from_history,
)
from ..utils.app_paths import accounts_data_dir


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
        if bank_accounts_path:
            self._bank_accounts_path = Path(bank_accounts_path)
        else:
            self._bank_accounts_path = accounts_data_dir() / "bank_accounts.json"

        if savings_accounts_path:
            self._savings_accounts_path = Path(savings_accounts_path)
        else:
            self._savings_accounts_path = accounts_data_dir() / "savings_accounts.json"

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

                accounts.append(
                    BankAccount(
                        name=name,
                        total_amount=float(total_amount),
                        is_liquid=is_liquid,
                        history=account_history,
                        active=active,
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

        json_data = []
        for account in accounts:
            account_dict = {
                "name": account.name,
                "is_liquid": account.is_liquid,
                "total_amount": account.total_amount,
                "savings": [],
            }
            for savings_item in account.savings:
                savings_dict = {
                    "name": savings_item.name,
                    "amount": savings_item.amount,
                    "history": [
                        {"date": snapshot.date, "amount": snapshot.amount}
                        for snapshot in savings_item.history
                    ],
                }
                account_dict["savings"].append(savings_dict)  # type: ignore[attr-defined]
            json_data.append(account_dict)

        with self._savings_accounts_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    def save_bank_accounts(self, accounts: List[BankAccount]) -> None:
        self._bank_accounts_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = []
        for account in accounts:
            account_dict = {
                "name": account.name,
                "is_liquid": account.is_liquid,
                "total_amount": account.total_amount,
                "active": account.active,
                "history": [
                    {"date": snap.date, "amount": snap.amount}
                    for snap in account.history
                ],
            }
            json_data.append(account_dict)

        with self._bank_accounts_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
