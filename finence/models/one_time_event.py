from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional
import uuid


class OneTimeEventStatus(StrEnum):
    PLANNED = "מתוכנן"
    ACTIVE = "פעיל"
    FINISHED = "הסתיים"
    ARCHIVED = "בארכיון"


def generate_event_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class OneTimeEvent:
    id: str = field(default_factory=generate_event_id)
    name: str = ""
    budget: float = 0.0
    status: OneTimeEventStatus = OneTimeEventStatus.ACTIVE
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    notes: Optional[str] = None
