from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .json_io import atomic_write_json, read_json_list, workspace_json_path
from ..utils.logging_setup import get_logger
from ..utils.safe import PARSE_ERRORS

_log = get_logger("data")

from ..models.installment_plan import InstallmentPlan, generate_installment_plan_id


class InstallmentPlanProvider(ABC):
    @abstractmethod
    def list_plans(self) -> List[InstallmentPlan]:
        raise NotImplementedError

    @abstractmethod
    def save_plans(self, plans: List[InstallmentPlan]) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_plan(self, plan: InstallmentPlan) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_plan(self, plan_id: str) -> None:
        raise NotImplementedError


class JsonFileInstallmentPlanProvider(InstallmentPlanProvider):
    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self._explicit_path: Optional[Path] = Path(path) if path else None

    def _get_path(self) -> Path:
        return workspace_json_path("installment_plans", self._explicit_path)

    def list_plans(self) -> List[InstallmentPlan]:
        return read_json_list(self._get_path(), self._deserialize)

    def save_plans(self, plans: List[InstallmentPlan]) -> None:
        p = self._get_path()
        payload = [self._serialize(p) for p in plans]
        atomic_write_json(p, payload)

    def upsert_plan(self, plan: InstallmentPlan) -> None:
        plans = self.list_plans()
        updated: List[InstallmentPlan] = []
        found = False
        for p in plans:
            if p.id == plan.id:
                updated.append(plan)
                found = True
            else:
                updated.append(p)
        if not found:
            updated.append(plan)
        self.save_plans(updated)

    def delete_plan(self, plan_id: str) -> None:
        plan_id = str(plan_id or "").strip()
        if not plan_id:
            return
        plans = [p for p in self.list_plans() if p.id != plan_id]
        self.save_plans(plans)

    @staticmethod
    def _serialize(plan: InstallmentPlan) -> Dict[str, Any]:
        d = asdict(plan)
        d["excluded_movement_ids"] = list(
            getattr(plan, "excluded_movement_ids", []) or []
        )
        d["archived"] = bool(getattr(plan, "archived", False))
        return d

    @staticmethod
    def _deserialize(item: Any) -> Optional[InstallmentPlan]:
        if not isinstance(item, dict):
            return None
        try:
            excluded_raw = item.get("excluded_movement_ids") or []
            excluded: list[str] = []
            if isinstance(excluded_raw, list):
                excluded = [str(x) for x in excluded_raw if str(x).strip()]
            return InstallmentPlan(
                id=str(item.get("id", "")).strip() or generate_installment_plan_id(),
                name=str(item.get("name", "") or ""),
                vendor_query=str(item.get("vendor_query", "") or ""),
                account_name=str(item.get("account_name", "") or ""),
                start_date=str(item.get("start_date", "") or ""),
                payments_count=int(item.get("payments_count", 0) or 0),
                original_amount=float(item.get("original_amount", 0.0) or 0.0),
                excluded_movement_ids=excluded,
                archived=bool(item.get("archived", False)),
            )
        except PARSE_ERRORS as exc:
            _log.debug("skipping malformed installment plan: %s", exc)
            return None
