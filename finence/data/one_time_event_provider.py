from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.one_time_event import OneTimeEvent, OneTimeEventStatus
from ..utils.app_paths import accounts_data_dir
from ..models.firebase_session import current_firebase_uid, current_firebase_workspace_id


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
        key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
        suffix = f"_{key}" if key else ""
        self._path = (
            Path(path) if path else accounts_data_dir() / f"one_time_events{suffix}.json"
        )

    def list_events(self) -> List[OneTimeEvent]:
        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        out: List[OneTimeEvent] = []
        for item in data:
            evt = self._deserialize(item)
            if evt is not None:
                out.append(evt)
        return out

    def save_events(self, events: List[OneTimeEvent]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._serialize(e) for e in events]
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

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
            status_raw = item.get("status", OneTimeEventStatus.ACTIVE.value)
            try:
                status = OneTimeEventStatus(str(status_raw))
            except Exception:
                status = OneTimeEventStatus.ACTIVE
            return OneTimeEvent(
                id=str(item.get("id", "")) or OneTimeEvent().id,
                name=str(item.get("name", "")),
                budget=float(item.get("budget", 0.0) or 0.0),
                status=status,
                start_date=str(item["start_date"]) if item.get("start_date") else None,
                end_date=str(item["end_date"]) if item.get("end_date") else None,
                notes=str(item["notes"]) if item.get("notes") else None,
            )
        except Exception:
            return None
