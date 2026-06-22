from __future__ import annotations

from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.accounts import (
    BankAccount,
    BudgetAccount,
    MoneyAccount,
    SavingsAccount,
    bank_entry_from_storage_dict,
)
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
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
        self._bank_accounts_path_override: Optional[Path] = (
            Path(bank_accounts_path) if bank_accounts_path else None
        )
        self._savings_accounts_path_override: Optional[Path] = (
            Path(savings_accounts_path) if savings_accounts_path else None
        )
        self._bank_accounts_path, self._savings_accounts_path = self._paths()

    def _paths(self) -> tuple[Path, Path]:
        if self._bank_accounts_path_override is not None:
            bank_path = self._bank_accounts_path_override
        else:
            key = (
                current_firebase_workspace_id() or current_firebase_uid() or ""
            ).strip()
            suffix = f"_{key}" if key else ""
            bank_path = accounts_data_dir() / f"bank_accounts{suffix}.json"

        if self._savings_accounts_path_override is not None:
            savings_path = self._savings_accounts_path_override
        else:
            key = (
                current_firebase_workspace_id() or current_firebase_uid() or ""
            ).strip()
            suffix = f"_{key}" if key else ""
            savings_path = accounts_data_dir() / f"savings_accounts{suffix}.json"

        return bank_path, savings_path

    def _ensure_paths(self) -> None:
        self._bank_accounts_path, self._savings_accounts_path = self._paths()

    def list_accounts(self) -> List[MoneyAccount]:
        accounts: List[MoneyAccount] = []
        self._ensure_paths()

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
                acc = bank_entry_from_storage_dict(item)
                if acc is not None:
                    accounts.append(acc)
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
                if not str(item.get("name", "")).strip():
                    continue
                accounts.append(SavingsAccount.from_storage_dict(item))
            except Exception:
                continue
        return accounts

    def save_savings_accounts(self, accounts: List[SavingsAccount]) -> None:
        self._ensure_paths()
        self._savings_accounts_path.parent.mkdir(parents=True, exist_ok=True)

        json_data: List[Dict[str, Any]] = [
            account.to_storage_dict() for account in accounts
        ]

        _target = self._savings_accounts_path
        _tmp = _target.with_suffix(".tmp")
        with _tmp.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(_tmp, _target)

    def save_bank_accounts(self, accounts: List[MoneyAccount]) -> None:
        self._ensure_paths()
        self._bank_accounts_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = [
            account.to_storage_dict()
            for account in accounts
            if isinstance(account, (BankAccount, BudgetAccount))
        ]

        _target = self._bank_accounts_path
        _tmp = _target.with_suffix(".tmp")
        with _tmp.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(_tmp, _target)
