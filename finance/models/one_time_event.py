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


def parse_one_time_event_status(raw: object) -> OneTimeEventStatus:
    text = str(raw or "").strip()
    if not text:
        return OneTimeEventStatus.ACTIVE
    try:
        return OneTimeEventStatus(text)
    except Exception:
        pass
    upper = text.upper()
    if upper in ("PLANNED", "PLAN"):
        return OneTimeEventStatus.PLANNED
    if upper in ("ACTIVE", "IN_PROGRESS"):
        return OneTimeEventStatus.ACTIVE
    if upper in ("FINISHED", "DONE", "COMPLETED"):
        return OneTimeEventStatus.FINISHED
    if upper in ("ARCHIVED", "ARCHIVE"):
        return OneTimeEventStatus.ARCHIVED
    return OneTimeEventStatus.ACTIVE


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
