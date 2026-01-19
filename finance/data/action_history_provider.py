from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.action_history import (
    Action,
    ActionHistory,
    ActivateBankAccountAction,
    AddIncomeMovementAction,
    AddInstallmentPlanAction,
    AddOneTimeEventAction,
    AddOutcomeMovementAction,
    AddSavingAction,
    AddSavingsAccountAction,
    AssignMovementToOneTimeEventAction,
    DeactivateBankAccountAction,
    DeleteInstallmentPlanAction,
    DeleteMovementAction,
    DeleteOneTimeEventAction,
    DeleteSavingAction,
    DeleteSavingsAccountAction,
    EditInstallmentPlanAction,
    EditOneTimeEventAction,
    EditSavingAction,
    EditSavingsAccountAction,
    SetStarterAmountAction,
    TransferAction,
    UnassignMovementFromOneTimeEventAction,
    UploadOutcomeFileAction,
)
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
)
from ..utils.app_paths import accounts_data_dir


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
        self._explicit_history_path: Optional[Path] = (
            Path(history_path) if history_path else None
        )
        self._history_path: Path = Path("")
        self._last_key: str = ""
        self._ensure_path()

    def _ensure_path(self) -> None:
        if self._explicit_history_path is not None:
            self._history_path = self._explicit_history_path
            return

        wid = current_firebase_workspace_id()
        uid = current_firebase_uid()
        key = str(wid or uid or "").strip()
        if key == self._last_key and self._history_path:
            return
        self._last_key = key
        if key:
            self._history_path = accounts_data_dir() / f"action_history_{key}.json"
        else:
            self._history_path = accounts_data_dir() / "action_history.json"

    def list_history(self) -> List[ActionHistory]:
        self._ensure_path()
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
        self._ensure_path()
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
        self._ensure_path()
        current_history = self.list_history()
        current_history.append(action_history)
        self.save_history(current_history)
        try:
            from ..models.sync_gate import allow_firebase_push

            if not allow_firebase_push():
                return
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

            FirebaseWorkspaceWriter().upsert_action_history(action_history)
        except Exception:
            pass

    def _serialize_action(self, action: Action) -> dict:
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
                if isinstance(value, list):
                    action_dict[field_info.name] = value
                else:
                    action_dict[field_info.name] = value

        return action_dict

    def _deserialize_action(self, action_data: dict) -> Optional[Action]:
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
            "delete_movement": DeleteMovementAction,
            "upload_outcome_file": UploadOutcomeFileAction,
            "add_one_time_event": AddOneTimeEventAction,
            "edit_one_time_event": EditOneTimeEventAction,
            "delete_one_time_event": DeleteOneTimeEventAction,
            "assign_movement_to_one_time_event": AssignMovementToOneTimeEventAction,
            "unassign_movement_from_one_time_event": UnassignMovementFromOneTimeEventAction,
            "add_installment_plan": AddInstallmentPlanAction,
            "edit_installment_plan": EditInstallmentPlanAction,
            "delete_installment_plan": DeleteInstallmentPlanAction,
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
                elif "list[str]" in field_type_str or "List[str]" in field_type_str:
                    if isinstance(field_value, list):
                        kwargs[field_info.name] = field_value
                    elif isinstance(field_value, str):
                        try:
                            import json as _json

                            parsed = _json.loads(field_value)
                            if isinstance(parsed, list):
                                kwargs[field_info.name] = parsed
                            else:
                                try:
                                    import ast

                                    parsed = ast.literal_eval(field_value)
                                    if isinstance(parsed, list):
                                        kwargs[field_info.name] = parsed
                                    else:
                                        kwargs[field_info.name] = []
                                except Exception:
                                    kwargs[field_info.name] = []
                        except Exception:
                            try:
                                import ast

                                parsed = ast.literal_eval(field_value)
                                if isinstance(parsed, list):
                                    kwargs[field_info.name] = parsed
                                else:
                                    kwargs[field_info.name] = []
                            except Exception:
                                kwargs[field_info.name] = []
                    else:
                        kwargs[field_info.name] = (
                            list(field_value) if field_value else []
                        )
                elif "str" in field_type_str:
                    kwargs[field_info.name] = str(field_value)
                elif "list" in field_type_str or "List" in field_type_str:
                    if isinstance(field_value, list):
                        kwargs[field_info.name] = field_value
                    else:
                        kwargs[field_info.name] = (
                            list(field_value) if field_value else []
                        )
                else:
                    kwargs[field_info.name] = field_value

            return action_class(**kwargs)
        except Exception:
            return None
