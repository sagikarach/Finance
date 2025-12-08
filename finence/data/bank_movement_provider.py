from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional, Union
import json

from ..models.bank_movement import BankMovement, MovementType


class BankMovementProvider(ABC):
    @abstractmethod
    def list_movements(self) -> List[BankMovement]:
        raise NotImplementedError

    @abstractmethod
    def save_movements(self, movements: List[BankMovement]) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_movement(self, movement: BankMovement) -> None:
        raise NotImplementedError


class JsonFileBankMovementProvider(BankMovementProvider):
    def __init__(self, movements_path: Optional[Union[str, Path]] = None) -> None:
        if movements_path:
            self._movements_path = Path(movements_path)
        else:
            self._movements_path = (
                Path.cwd() / "data" / "accounts" / "bank_movements.json"
            )
        # Categories are stored in a separate JSON file next to the movements file.
        self._categories_path = self._movements_path.with_name(
            "bank_movement_categories.json"
        )

    def list_movements(self) -> List[BankMovement]:
        movements: List[BankMovement] = []

        if not self._movements_path.exists():
            return movements

        try:
            with self._movements_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return movements

        if not isinstance(data, list):
            return movements

        for item in data:
            try:
                amount = float(item.get("amount", 0.0))
                date = str(item.get("date", "")).strip()
                account_name = str(item.get("account_name", "")).strip()
                category = str(item.get("category", "")).strip()
                type_value = item.get("type", MovementType.ONE_TIME.value)
                try:
                    movement_type = MovementType(type_value)
                except Exception:
                    movement_type = MovementType.ONE_TIME
                description_value = item.get("description")
                description = (
                    str(description_value)
                    if isinstance(description_value, str)
                    else None
                )

                if not date or not account_name:
                    continue

                movements.append(
                    BankMovement(
                        amount=amount,
                        date=date,
                        account_name=account_name,
                        category=category,
                        type=movement_type,
                        description=description,
                    )
                )
            except Exception:
                continue

        return movements

    def save_movements(self, movements: List[BankMovement]) -> None:
        self._movements_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = []
        for movement in movements:
            m_dict = asdict(movement)
            # Store enum as its string value
            m_dict["type"] = movement.type.value
            json_data.append(m_dict)

        with self._movements_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    def add_movement(self, movement: BankMovement) -> None:
        current = self.list_movements()
        current.append(movement)
        self.save_movements(current)

    # Category management
    def _load_categories_by_type(self) -> dict:
        """
        Load categories from disk.

        Old format (backwards compatible):
          ["קטגוריה1", "קטגוריה2"]
        New format:
          {"income": ["..."], "outcome": ["..."]}
        """
        if not self._categories_path.exists():
            return {"income": [], "outcome": []}
        try:
            with self._categories_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {"income": [], "outcome": []}

        # Old format: plain list shared by both income/outcome
        if isinstance(data, list):
            items = [str(x).strip() for x in data if isinstance(x, str) and x.strip()]
            return {"income": list(items), "outcome": list(items)}

        # New format: dict with income/outcome keys
        if not isinstance(data, dict):
            return {"income": [], "outcome": []}

        def _ensure_list(value) -> List[str]:
            if not isinstance(value, list):
                return []
            out: List[str] = []
            for item in value:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        out.append(text)
            return out

        income = _ensure_list(data.get("income", []))
        outcome = _ensure_list(data.get("outcome", []))
        return {"income": income, "outcome": outcome}

    def _save_categories_by_type(self, mapping: dict) -> None:
        """Persist categories mapping with separate income/outcome lists."""
        income = mapping.get("income") or []
        outcome = mapping.get("outcome") or []
        # Ensure plain lists of strings
        income_list = [str(x) for x in income if isinstance(x, str)]
        outcome_list = [str(x) for x in outcome if isinstance(x, str)]

        self._categories_path.parent.mkdir(parents=True, exist_ok=True)
        with self._categories_path.open("w", encoding="utf-8") as f:
            json.dump(
                {"income": income_list, "outcome": outcome_list},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def list_categories_for_type(self, is_income: bool) -> List[str]:
        """Return categories for income or outcome separately."""
        mapping = self._load_categories_by_type()
        key = "income" if is_income else "outcome"
        items = mapping.get(key, [])
        # Defensive copy
        return list(items)

    # Backwards-compatible helpers used nowhere else right now, kept just in case.
    def list_categories(self) -> List[str]:
        """
        Return a merged list of all categories (income + outcome).
        """
        mapping = self._load_categories_by_type()
        merged = set(mapping.get("income", [])) | set(mapping.get("outcome", []))
        return list(merged)

    def save_categories(self, categories: List[str]) -> None:
        """
        Backwards compatible: set the same categories for both income and outcome.
        """
        mapping = {"income": list(categories), "outcome": list(categories)}
        self._save_categories_by_type(mapping)

    def add_category_for_type(self, name: str, is_income: bool) -> None:
        """Add a new category for income or outcome if it does not already exist."""
        name = name.strip()
        if not name:
            return
        mapping = self._load_categories_by_type()
        key = "income" if is_income else "outcome"
        items = mapping.get(key)
        if items is None:
            items = []
            mapping[key] = items
        if name in items:
            return
        items.append(name)
        self._save_categories_by_type(mapping)

    def add_category(self, name: str) -> None:
        """
        Backwards compatible: add the category to both income and outcome
        lists.
        """
        name = name.strip()
        if not name:
            return
        mapping = self._load_categories_by_type()
        for key in ("income", "outcome"):
            items = mapping.get(key)
            if items is None:
                items = []
                mapping[key] = items
            if name not in items:
                items.append(name)
        self._save_categories_by_type(mapping)
