from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class NotificationType(str, Enum):
    UNEXPECTED_EXPENSE = "unexpected_expense"
    MISSING_SAVINGS_UPDATE = "missing_savings_update"
    MISSING_MONTHLY_UPLOAD = "missing_monthly_upload"
    EVENT_OVER_BUDGET = "event_over_budget"


class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class RuleType(str, Enum):
    UNEXPECTED_EXPENSE = "unexpected_expense"
    MISSING_SAVINGS_UPDATE = "missing_savings_update"
    MISSING_MONTHLY_UPLOAD = "missing_monthly_upload"
    EVENT_OVER_BUDGET = "event_over_budget"


@dataclass(frozen=True)
class NotificationRule:
    id: str
    type: RuleType
    enabled: bool = True
    schedule: str = "daily"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Notification:
    id: str
    key: str
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    created_at: str
    status: NotificationStatus = NotificationStatus.UNREAD
    due_at: Optional[str] = None
    source: str = "system"
    context: Dict[str, Any] = field(default_factory=dict)
