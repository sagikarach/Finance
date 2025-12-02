from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .accounts import MoneyAccount


@dataclass
class UserProfile:
    full_name: str
    avatar_path: Optional[str] = None
    password: Optional[str] = None
    lock_enabled: bool = False
    accounts: List[MoneyAccount] = field(default_factory=list)
