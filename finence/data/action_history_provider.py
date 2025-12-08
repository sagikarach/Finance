from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.action_history import (
    ActionHistory,
    Action,
    TransferAction,
    AddSavingsAccountAction,
    EditSavingsAccountAction,
    DeleteSavingsAccountAction,
    AddSavingAction,
    EditSavingAction,
    DeleteSavingAction,
    ActivateBankAccountAction,
    DeactivateBankAccountAction,
    SetStarterAmountAction,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
)


class ActionHistoryProvider(ABC):
    @abstractmethod
    def list_history(self) -> List[ActionHistory]:
        raise NotImplementedError

    @abstractmethod
    def save_history(self, history: List[ActionHistory]) -> None:
        raise NotImplementedError

    @abstractmethod
    def add_action(self, action_history: ActionHistory) -> None:
        raise NotImplementedError


class JsonFileActionHistoryProvider(ActionHistoryProvider):
    def __init__(
        self,
        history_path: Optional[Union[str, Path]] = None,
    ) -> None:
        if history_path:
            self._history_path = Path(history_path)
        else:
            self._history_path = (
                Path.cwd() / "data" / "accounts" / "action_history.json"
            )

    def list_history(self) -> List[ActionHistory]:
        """Load action history from JSON file."""
        history: List[ActionHistory] = []

        if not self._history_path.exists():
            return history

        try:
            with self._history_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return history

        if not isinstance(data, list):
            return history

        for item in data:
            try:
                history_id = str(item.get("id", ""))
                timestamp = str(item.get("timestamp", ""))
                action_data = item.get("action", {})

                if not history_id or not timestamp or not action_data:
                    continue

                action = self._deserialize_action(action_data)
                if action is None:
                    continue

                history.append(
                    ActionHistory(
                        id=history_id,
                        timestamp=timestamp,
                        action=action,
                    )
                )
            except Exception:
                continue

        return history

    def save_history(self, history: List[ActionHistory]) -> None:
        """Save action history to JSON file."""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

        json_data = []
        for entry in history:
            entry_dict = {
                "id": entry.id,
                "timestamp": entry.timestamp,
                "action": self._serialize_action(entry.action),
            }
            json_data.append(entry_dict)

        with self._history_path.open("w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    def add_action(self, action_history: ActionHistory) -> None:
        """Add a new action to the history."""
        current_history = self.list_history()
        current_history.append(action_history)
        self.save_history(current_history)

    def _serialize_action(self, action: Action) -> dict:
        """Convert an Action object to a dictionary."""
        action_dict: dict = {
            "action_name": action.action_name,
            "success": action.success,
        }
        if action.error_message is not None:
            action_dict["error_message"] = action.error_message

        for field_info in fields(action):
            if field_info.name in ("action_name", "success", "error_message"):
                continue
            value = getattr(action, field_info.name, None)
            if value is not None:
                action_dict[field_info.name] = value

        return action_dict

    def _deserialize_action(self, action_data: dict) -> Optional[Action]:
        """Convert a dictionary to an Action object."""
        if not isinstance(action_data, dict):
            return None

        action_name = action_data.get("action_name", "")
        if not action_name:
            action_name = action_data.get("type", "")

        action_class_map: Dict[str, type[Action]] = {
            "transfer": TransferAction,
            "add_savings_account": AddSavingsAccountAction,
            "edit_savings_account": EditSavingsAccountAction,
            "delete_savings_account": DeleteSavingsAccountAction,
            "add_saving": AddSavingAction,
            "edit_saving": EditSavingAction,
            "delete_saving": DeleteSavingAction,
            "activate_bank_account": ActivateBankAccountAction,
            "deactivate_bank_account": DeactivateBankAccountAction,
            "set_starter_amount": SetStarterAmountAction,
            "add_income_movement": AddIncomeMovementAction,
            "add_outcome_movement": AddOutcomeMovementAction,
        }

        action_class = action_class_map.get(action_name)
        if action_class is None:
            return None

        try:
            kwargs: Dict[str, Any] = {
                "action_name": action_name,
                "success": bool(action_data.get("success", True)),
            }
            if "error_message" in action_data:
                kwargs["error_message"] = action_data.get("error_message")

            for field_info in fields(action_class):
                if field_info.name in ("action_name", "success", "error_message"):
                    continue

                field_value = action_data.get(field_info.name)
                if field_value is None:
                    continue

                field_type_str = str(field_info.type)
                if "float" in field_type_str:
                    kwargs[field_info.name] = float(field_value)
                elif "bool" in field_type_str:
                    kwargs[field_info.name] = bool(field_value)
                elif "str" in field_type_str:
                    kwargs[field_info.name] = str(field_value)
                else:
                    kwargs[field_info.name] = field_value

            return action_class(**kwargs)
        except Exception:
            return None
