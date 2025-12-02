from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .accounts import MoneyAccount


@dataclass
class UserProfile:
    full_name: str
    avatar_path: Optional[str] = None
    accounts: List[MoneyAccount] = field(default_factory=list)


