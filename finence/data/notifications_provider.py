from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.notifications import (
    Notification,
    NotificationRule,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
    RuleType,
)
from ..utils.app_paths import accounts_data_dir


class NotificationsProvider(ABC):
    @abstractmethod
    def list_notifications(self) -> List[Notification]:
        raise NotImplementedError

    @abstractmethod
    def save_notifications(self, notifications: List[Notification]) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_rules(self) -> List[NotificationRule]:
        raise NotImplementedError

    @abstractmethod
    def save_rules(self, rules: List[NotificationRule]) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, notif: Notification) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_status(self, *, key: str, status: NotificationStatus) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        raise NotImplementedError


class JsonFileNotificationsProvider(NotificationsProvider):
    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self._path = Path(path) if path else accounts_data_dir() / "notifications.json"

    def list_notifications(self) -> List[Notification]:
        data = self._read()
        raw = data.get("notifications", [])
        if not isinstance(raw, list):
            return []
        out: List[Notification] = []
        for item in raw:
            n = self._deserialize_notification(item)
            if n is not None:
                out.append(n)
        return out

    def save_notifications(self, notifications: List[Notification]) -> None:
        data = self._read()
        data["notifications"] = [self._serialize_notification(n) for n in notifications]
        self._write(data)

    def list_rules(self) -> List[NotificationRule]:
        data = self._read()
        raw = data.get("rules", [])
        if not isinstance(raw, list):
            return []
        out: List[NotificationRule] = []
        for item in raw:
            r = self._deserialize_rule(item)
            if r is not None:
                out.append(r)
        return out

    def save_rules(self, rules: List[NotificationRule]) -> None:
        data = self._read()
        data["rules"] = [self._serialize_rule(r) for r in rules]
        self._write(data)

    def upsert(self, notif: Notification) -> None:
        existing = self.list_notifications()
        by_key = {n.key: n for n in existing}
        if notif.key in by_key:
            return
        existing.append(notif)
        self.save_notifications(existing)

    def update_status(self, *, key: str, status: NotificationStatus) -> None:
        items = self.list_notifications()
        changed = False
        updated: List[Notification] = []
        for n in items:
            if n.key == key and n.status != status:
                n = Notification(
                    id=n.id,
                    key=n.key,
                    type=n.type,
                    title=n.title,
                    message=n.message,
                    severity=n.severity,
                    created_at=n.created_at,
                    status=status,
                    due_at=n.due_at,
                    source=n.source,
                    context=dict(n.context),
                )
                changed = True
            updated.append(n)
        if changed:
            self.save_notifications(updated)

    def is_enabled(self) -> bool:
        data = self._read()
        settings = data.get("settings", {})
        if isinstance(settings, dict):
            val = settings.get("enabled", True)
            return bool(val)
        return True

    def set_enabled(self, enabled: bool) -> None:
        data = self._read()
        settings = data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
        settings["enabled"] = bool(enabled)
        data["settings"] = settings
        self._write(data)

    def _read(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {"settings": {"enabled": True}, "rules": [], "notifications": []}
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if "settings" not in data:
                    data["settings"] = {"enabled": True}
                return data
        except Exception:
            pass
        return {"settings": {"enabled": True}, "rules": [], "notifications": []}

    def _write(self, data: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _serialize_notification(self, n: Notification) -> Dict[str, Any]:
        d = asdict(n)
        d["type"] = str(n.type.value)
        d["severity"] = str(n.severity.value)
        d["status"] = str(n.status.value)
        return d

    def _deserialize_notification(self, item: Any) -> Optional[Notification]:
        if not isinstance(item, dict):
            return None
        try:
            return Notification(
                id=str(item.get("id", "")),
                key=str(item.get("key", "")),
                type=NotificationType(str(item.get("type", ""))),
                title=str(item.get("title", "")),
                message=str(item.get("message", "")),
                severity=NotificationSeverity(str(item.get("severity", "info"))),
                created_at=str(item.get("created_at", "")),
                status=NotificationStatus(str(item.get("status", "unread"))),
                due_at=str(item["due_at"]) if item.get("due_at") is not None else None,
                source=str(item.get("source", "system")),
                context=dict(item.get("context", {}) or {}),
            )
        except Exception:
            return None

    def _serialize_rule(self, r: NotificationRule) -> Dict[str, Any]:
        d = asdict(r)
        d["type"] = str(r.type.value)
        return d

    def _deserialize_rule(self, item: Any) -> Optional[NotificationRule]:
        if not isinstance(item, dict):
            return None
        try:
            return NotificationRule(
                id=str(item.get("id", "")),
                type=RuleType(str(item.get("type", ""))),
                enabled=bool(item.get("enabled", True)),
                schedule=str(item.get("schedule", "daily")),
                params=dict(item.get("params", {}) or {}),
            )
        except Exception:
            return None
