from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.installment_plan import InstallmentPlan
from ..utils.app_paths import accounts_data_dir
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
)


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
        key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
        suffix = f"_{key}" if key else ""
        self._path = (
            Path(path)
            if path
            else accounts_data_dir() / f"installment_plans{suffix}.json"
        )

    def list_plans(self) -> List[InstallmentPlan]:
        if not self._path.exists():
            return []
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        out: List[InstallmentPlan] = []
        for item in data:
            plan = self._deserialize(item)
            if plan is not None:
                out.append(plan)
        return out

    def save_plans(self, plans: List[InstallmentPlan]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._serialize(p) for p in plans]
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

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
                id=str(item.get("id", "")) or InstallmentPlan().id,
                name=str(item.get("name", "") or ""),
                vendor_query=str(item.get("vendor_query", "") or ""),
                account_name=str(item.get("account_name", "") or ""),
                start_date=str(item.get("start_date", "") or ""),
                payments_count=int(item.get("payments_count", 0) or 0),
                original_amount=float(item.get("original_amount", 0.0) or 0.0),
                excluded_movement_ids=excluded,
                archived=bool(item.get("archived", False)),
            )
        except Exception:
            return None
