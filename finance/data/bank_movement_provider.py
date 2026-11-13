from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
import os
from pathlib import Path
from typing import List, Optional, Union
import json

from ..models.bank_movement import BankMovement, deserialize_bank_movement
from ..models.category_tree import SCHEMA_VERSION, CategoryTree
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
)
from ..utils.app_paths import accounts_data_dir
from ..utils.logging_setup import get_logger

_log = get_logger("data")


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

    # Category listing is part of the provider contract; the JSON provider
    # overrides these, other providers inherit the empty defaults.
    def list_categories_for_type(self, is_income: bool) -> List[str]:
        return []

    def list_categories(self) -> List[str]:
        return []


class JsonFileBankMovementProvider(BankMovementProvider):
    def __init__(self, movements_path: Optional[Union[str, Path]] = None) -> None:
        self._movements_path_override: Optional[Path] = (
            Path(movements_path) if movements_path else None
        )
        self._movements_path, self._categories_path = self._paths()

    def _paths(self) -> tuple[Path, Path]:
        if self._movements_path_override is not None:
            movements_path = self._movements_path_override
            categories_path = movements_path.with_name("bank_movement_categories.json")
            return movements_path, categories_path
        else:
            wid = current_firebase_workspace_id()
            uid = current_firebase_uid()
            key = wid or uid
            if key:
                movements_path = accounts_data_dir() / f"bank_movements_{key}.json"
                categories_path = (
                    accounts_data_dir() / f"bank_movement_categories_{key}.json"
                )
            else:
                movements_path = accounts_data_dir() / "bank_movements.json"
                categories_path = accounts_data_dir() / "bank_movement_categories.json"
            return movements_path, categories_path

    def _ensure_paths(self) -> None:
        self._movements_path, self._categories_path = self._paths()

    def list_movements(self) -> List[BankMovement]:
        movements: List[BankMovement] = []
        self._ensure_paths()

        if not self._movements_path.exists():
            return movements

        try:
            with self._movements_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            _log.warning("could not read %s: %s", self._movements_path, exc)
            return movements

        if not isinstance(data, list):
            return movements

        for item in data:
            mv = deserialize_bank_movement(item)
            if mv is not None:
                movements.append(mv)

        return movements

    def save_movements(self, movements: List[BankMovement]) -> None:
        self._ensure_paths()
        self._movements_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = []
        for movement in movements:
            m_dict = asdict(movement)
            m_dict["type"] = movement.type.value
            json_data.append(m_dict)

        _target = self._movements_path
        _tmp = _target.with_suffix(".tmp")
        try:
            with _tmp.open("w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(_tmp, _target)
        except Exception:
            try:
                _tmp.unlink(missing_ok=True)
            except OSError:
                _log.debug("could not remove temp file %s", _tmp)
            raise

    def add_movement(self, movement: BankMovement) -> None:
        current = self.list_movements()
        current.append(movement)
        self.save_movements(current)

    def _load_categories_by_type(self) -> dict:
        self._ensure_paths()
        if not self._categories_path.exists():
            return {"income": [], "outcome": []}
        try:
            with self._categories_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            _log.warning("could not read %s: %s", self._categories_path, exc)
            return {"income": [], "outcome": []}

        if isinstance(data, list):
            items = [str(x).strip() for x in data if isinstance(x, str) and x.strip()]
            return {"income": list(items), "outcome": list(items)}

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

    def _load_categories_raw(self) -> dict:
        self._ensure_paths()
        if not self._categories_path.exists():
            return {}
        try:
            with self._categories_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_categories_raw(self, data: dict) -> None:
        self._ensure_paths()
        target = self._categories_path
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                _log.debug("could not remove temp file %s", tmp)
            raise

    def _save_categories_by_type(self, mapping: dict) -> None:
        income = mapping.get("income") or []
        outcome = mapping.get("outcome") or []
        data = self._load_categories_raw()  # keep the hierarchy keys
        data["income"] = [str(x) for x in income if isinstance(x, str)]
        data["outcome"] = [str(x) for x in outcome if isinstance(x, str)]
        self._write_categories_raw(data)

    @property
    def categories_path(self) -> Path:
        self._ensure_paths()
        return self._categories_path

    def load_category_tree(self) -> "CategoryTree":
        return CategoryTree.from_storage(self._load_categories_raw())

    def save_category_tree(
        self, tree: "CategoryTree", *, outcome_names: Optional[List[str]] = None
    ) -> None:
        """Persist the hierarchy (and, if given, the flat outcome list) in one
        atomic write."""
        data = self._load_categories_raw()
        data.setdefault("income", [])
        if outcome_names is not None:
            data["outcome"] = list(outcome_names)
        else:
            data.setdefault("outcome", [])
        data["outcome_tree"] = tree.nodes_to_list()
        data["legacy_aliases"] = dict(tree.legacy_aliases)
        data["schema_version"] = SCHEMA_VERSION
        self._write_categories_raw(data)

    def list_categories_for_type(self, is_income: bool) -> List[str]:
        mapping = self._load_categories_by_type()
        key = "income" if is_income else "outcome"
        items = mapping.get(key, [])
        return list(items)

    def list_categories(self) -> List[str]:
        mapping = self._load_categories_by_type()
        merged = set(mapping.get("income", [])) | set(mapping.get("outcome", []))
        return list(merged)

    def add_category_for_type(self, name: str, is_income: bool) -> None:
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

    def add_expense_category(self, name: str, parent_name: str = "") -> None:
        """Add an expense category: under ``parent_name`` (a hierarchy node,
        one atomic write of the tree + flat list) or top-level (flat list)."""
        from ..models.category_create import add_child_category

        name = str(name or "").strip()
        parent_name = str(parent_name or "").strip()
        if not name:
            return
        tree = self.load_category_tree()
        if not parent_name or not tree or tree.by_name(parent_name) is None:
            self.add_category_for_type(name, False)
            return
        if tree.by_name(name) is not None:
            return
        new_tree = add_child_category(tree, name, parent_name)
        outcome = self.list_categories_for_type(False)
        ordered = new_tree.assignable_names()
        self.save_category_tree(
            new_tree, outcome_names=ordered + [n for n in outcome if n not in ordered]
        )

    def add_category(self, name: str) -> None:
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
