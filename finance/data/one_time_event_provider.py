from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .json_io import atomic_write_json, read_json_list, workspace_json_path

from ..models.one_time_event import (
    OneTimeEvent,
    OneTimeEventStatus,
    generate_event_id,
    parse_one_time_event_status,
)


class OneTimeEventProvider(ABC):
    @abstractmethod
    def list_events(self) -> List[OneTimeEvent]:
        raise NotImplementedError

    @abstractmethod
    def save_events(self, events: List[OneTimeEvent]) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_event(self, event: OneTimeEvent) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_event(self, event_id: str) -> None:
        raise NotImplementedError


class JsonFileOneTimeEventProvider(OneTimeEventProvider):
    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self._explicit_path: Optional[Path] = Path(path) if path else None

    def _get_path(self) -> Path:
        return workspace_json_path("one_time_events", self._explicit_path)

    def list_events(self) -> List[OneTimeEvent]:
        return read_json_list(self._get_path(), self._deserialize)

    def save_events(self, events: List[OneTimeEvent]) -> None:
        p = self._get_path()
        payload = [self._serialize(e) for e in events]
        atomic_write_json(p, payload)

    def upsert_event(self, event: OneTimeEvent) -> None:
        events = self.list_events()
        updated: List[OneTimeEvent] = []
        found = False
        for e in events:
            if e.id == event.id:
                updated.append(event)
                found = True
            else:
                updated.append(e)
        if not found:
            updated.append(event)
        self.save_events(updated)

    def delete_event(self, event_id: str) -> None:
        events = [e for e in self.list_events() if e.id != event_id]
        self.save_events(events)

    @staticmethod
    def _serialize(event: OneTimeEvent) -> Dict[str, Any]:
        d = asdict(event)
        d["status"] = str(event.status.value)
        return d

    @staticmethod
    def _deserialize(item: Any) -> Optional[OneTimeEvent]:
        if not isinstance(item, dict):
            return None
        try:
            status = parse_one_time_event_status(
                item.get("status", OneTimeEventStatus.ACTIVE.value)
            )
            return OneTimeEvent(
                id=str(item.get("id", "")).strip() or generate_event_id(),
                name=str(item.get("name", "")),
                budget=float(item.get("budget", 0.0) or 0.0),
                status=status,
                start_date=str(item["start_date"]) if item.get("start_date") else None,
                end_date=str(item["end_date"]) if item.get("end_date") else None,
                notes=str(item["notes"]) if item.get("notes") else None,
            )
        except Exception:
            return None
