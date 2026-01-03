from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class SidebarState:
    app_context: Optional[Dict[str, Any]]

    def get_bool(self, key: str) -> Optional[bool]:
        ctx = self.app_context
        if not isinstance(ctx, dict):
            return None
        val = ctx.get(key)
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            v = val.strip().lower()
            if v in ("1", "true", "yes", "on"):
                return True
            if v in ("0", "false", "no", "off"):
                return False
        return None

    def set_bool(self, key: str, value: bool) -> None:
        ctx = self.app_context
        if not isinstance(ctx, dict):
            return
        ctx[key] = "true" if bool(value) else "false"

    @staticmethod
    def key_bank_expanded() -> str:
        return "sidebar.bank.expanded"

    @staticmethod
    def key_savings_expanded() -> str:
        return "sidebar.savings.expanded"

    @staticmethod
    def key_yearly_expanded() -> str:
        return "sidebar.yearly.expanded"
