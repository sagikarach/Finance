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


# Who closed a RESOLVED/DISMISSED notification. ``None`` means unknown — every
# record written before this field existed — and is treated like a user
# decision (never reopened automatically).
CLOSED_BY_USER = "user"
CLOSED_BY_SYSTEM = "system"  # the condition stopped holding; may reopen later


def normalize_closed_by(value: object) -> Optional[str]:
    text = str(value or "").strip().lower()
    return text if text in (CLOSED_BY_USER, CLOSED_BY_SYSTEM) else None


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
    closed_by: Optional[str] = None  # CLOSED_BY_USER / CLOSED_BY_SYSTEM / None

    @property
    def is_closed(self) -> bool:
        return self.status in (NotificationStatus.RESOLVED, NotificationStatus.DISMISSED)

    @property
    def is_system_closed(self) -> bool:
        """Closed automatically (not by a person) — the only closed state that
        may be reopened automatically."""
        return self.is_closed and self.closed_by == CLOSED_BY_SYSTEM
