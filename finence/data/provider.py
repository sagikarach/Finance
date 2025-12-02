from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union
import json

from ..models.accounts import MoneyAccount, MoneySnapshot, latest_amount_from_history


class AccountsProvider(ABC):
    @abstractmethod
    def list_accounts(self) -> List[MoneyAccount]:
        raise NotImplementedError


class JsonFileAccountsProvider(AccountsProvider):
    def __init__(
        self, path: Optional[Union[str, Path]] = None, auto_create_sample: bool = True
    ) -> None:
        self._path = Path(path) if path is not None else Path.cwd() / "accounts.json"
        self._auto_create_sample = auto_create_sample

    def list_accounts(self) -> List[MoneyAccount]:
        if not self._path.exists():
            if self._auto_create_sample:
                self._write_sample()
            else:
                return []

        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # On malformed JSON or IO errors, return empty so the UI still loads
            return []

        if not isinstance(data, list):
            return []

        accounts: List[MoneyAccount] = []
        for item in data:
            try:
                name = str(item.get("name", "")).strip()
                # History is optional; if present, amount should reflect the latest by date
                raw_history = item.get("history", [])
                history: List[MoneySnapshot] = []
                if isinstance(raw_history, list):
                    for row in raw_history:
                        try:
                            history.append(
                                MoneySnapshot(
                                    date=str(row.get("date", "")),
                                    amount=float(row.get("amount", 0.0)),
                                )
                            )
                        except Exception:
                            continue
                # if history exists, prefer latest; else fallback to item.amount
                amount = float(item.get("amount", 0.0))
                if history:
                    latest = latest_amount_from_history(history)
                    if latest is not None:
                        amount = float(latest)
                is_liquid = bool(item.get("is_liquid", False))
                if name:
                    accounts.append(
                        MoneyAccount(
                            name=name,
                            amount=amount,
                            is_liquid=is_liquid,
                            history=history,
                        )
                    )
            except Exception:
                # Skip invalid rows
                continue
        return accounts

    def _write_sample(self) -> None:
        sample = [
            {
                "name": "Checking",
                "is_liquid": True,
                "history": [
                    {"date": "2025-01-01", "amount": 2100.0},
                    {"date": "2025-02-01", "amount": 2450.0},
                ],
            },
            {
                "name": "Savings",
                "is_liquid": True,
                "history": [
                    {"date": "2025-01-01", "amount": 12000.0},
                    {"date": "2025-02-01", "amount": 12850.0},
                ],
            },
            {
                "name": "Brokerage",
                "is_liquid": False,
                "history": [
                    {"date": "2025-01-01", "amount": 20500.25},
                    {"date": "2025-02-01", "amount": 21350.25},
                ],
            },
            {
                "name": "Retirement",
                "is_liquid": False,
                "history": [
                    {"date": "2025-01-01", "amount": 39500.75},
                    {"date": "2025-02-01", "amount": 40210.75},
                ],
            },
        ]
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(sample, f, indent=2)
        except Exception:
            # Ignore write failures
            pass
