from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

from ..models.mortgage import (
    AmortizationType,
    AssetKind,
    CostItem,
    FundingKind,
    FundingSource,
    Mortgage,
    MortgageTrack,
    TrackKind,
    generate_mortgage_id,
    generate_track_id,
)
from ..utils.app_paths import accounts_data_dir
from ..models.firebase_session import (
    current_firebase_uid,
    current_firebase_workspace_id,
)


class MortgageProvider(ABC):
    @abstractmethod
    def list_mortgages(self) -> List[Mortgage]:
        raise NotImplementedError

    @abstractmethod
    def save_mortgages(self, mortgages: List[Mortgage]) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_mortgage(self, mortgage: Mortgage) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_mortgage(self, mortgage_id: str) -> None:
        raise NotImplementedError


def _parse_track_kind(value: Any) -> TrackKind:
    try:
        return TrackKind(str(value))
    except Exception:
        return TrackKind.FIXED_UNLINKED


def _parse_amortization(value: Any) -> AmortizationType:
    try:
        return AmortizationType(str(value))
    except Exception:
        return AmortizationType.SPITZER


def _parse_asset_kind(value: Any) -> AssetKind:
    # ברירת מחדל: רכישה — כך רשומות קיימות (לפני התוספת) נשארות נכסי רכישה.
    if value is None:
        return AssetKind.PURCHASE
    try:
        return AssetKind(str(value))
    except Exception:
        return AssetKind.PURCHASE


def serialize_track(track: MortgageTrack) -> Dict[str, Any]:
    return {
        "id": str(track.id),
        "name": str(track.name or ""),
        "kind": str(getattr(track.kind, "value", track.kind)),
        "principal": float(track.principal),
        "annual_rate": float(track.annual_rate),
        "term_months": int(track.term_months),
        "amortization": str(getattr(track.amortization, "value", track.amortization)),
        "cpi_linked": bool(track.cpi_linked),
        "prime_spread": float(track.prime_spread),
        "reset_months": int(track.reset_months),
    }


def deserialize_track(item: Any) -> Optional[MortgageTrack]:
    if not isinstance(item, dict):
        return None
    try:
        return MortgageTrack(
            id=str(item.get("id", "")).strip() or generate_track_id(),
            name=str(item.get("name", "") or ""),
            kind=_parse_track_kind(item.get("kind")),
            principal=float(item.get("principal", 0.0) or 0.0),
            annual_rate=float(item.get("annual_rate", 0.0) or 0.0),
            term_months=int(item.get("term_months", 0) or 0),
            amortization=_parse_amortization(item.get("amortization")),
            cpi_linked=bool(item.get("cpi_linked", False)),
            prime_spread=float(item.get("prime_spread", 0.0) or 0.0),
            reset_months=int(item.get("reset_months", 0) or 0),
        )
    except Exception:
        return None


def serialize_cost(item: CostItem) -> Dict[str, Any]:
    return {
        "name": str(item.name or ""),
        "amount": float(item.amount),
        "query": str(getattr(item, "query", "") or ""),
    }


def deserialize_cost(item: Any) -> Optional[CostItem]:
    if not isinstance(item, dict):
        return None
    try:
        return CostItem(
            name=str(item.get("name", "") or ""),
            amount=float(item.get("amount", 0.0) or 0.0),
            query=str(item.get("query", "") or ""),
        )
    except Exception:
        return None


def _deserialize_costs(raw: Any) -> List[CostItem]:
    out: List[CostItem] = []
    if isinstance(raw, list):
        for c in raw:
            item = deserialize_cost(c)
            if item is not None:
                out.append(item)
    return out


def _parse_funding_kind(value: Any) -> FundingKind:
    try:
        return FundingKind(str(value))
    except Exception:
        return FundingKind.FUTURE


def serialize_funding(item: FundingSource) -> Dict[str, Any]:
    return {
        "name": str(item.name or ""),
        "amount": float(item.amount),
        "kind": str(getattr(item.kind, "value", item.kind)),
        "query": str(item.query or ""),
        "account_name": str(item.account_name or ""),
        "saving_name": str(item.saving_name or ""),
    }


def deserialize_funding(item: Any) -> Optional[FundingSource]:
    if not isinstance(item, dict):
        return None
    try:
        return FundingSource(
            name=str(item.get("name", "") or ""),
            amount=float(item.get("amount", 0.0) or 0.0),
            kind=_parse_funding_kind(item.get("kind")),
            query=str(item.get("query", "") or ""),
            account_name=str(item.get("account_name", "") or ""),
            saving_name=str(item.get("saving_name", "") or ""),
        )
    except Exception:
        return None


def _deserialize_funding(raw: Any) -> List[FundingSource]:
    out: List[FundingSource] = []
    if isinstance(raw, list):
        for f in raw:
            item = deserialize_funding(f)
            if item is not None:
                out.append(item)
    return out


def serialize_mortgage(mortgage: Mortgage) -> Dict[str, Any]:
    return {
        "id": str(mortgage.id),
        "name": str(mortgage.name or ""),
        "account_name": str(mortgage.account_name or ""),
        "vendor_query": str(mortgage.vendor_query or ""),
        "start_date": str(mortgage.start_date or ""),
        "tracks": [serialize_track(t) for t in mortgage.tracks],
        "excluded_movement_ids": list(
            getattr(mortgage, "excluded_movement_ids", []) or []
        ),
        "archived": bool(getattr(mortgage, "archived", False)),
        "property_price": float(getattr(mortgage, "property_price", 0.0) or 0.0),
        "price_query": str(getattr(mortgage, "price_query", "") or ""),
        "one_time_costs": [serialize_cost(c) for c in mortgage.one_time_costs],
        "monthly_costs": [serialize_cost(c) for c in mortgage.monthly_costs],
        "funding_sources": [serialize_funding(f) for f in mortgage.funding_sources],
        "kind": str(getattr(mortgage.kind, "value", mortgage.kind)),
        "current_value": float(getattr(mortgage, "current_value", 0.0) or 0.0),
        "sold": bool(getattr(mortgage, "sold", False)),
        "sale_price": float(getattr(mortgage, "sale_price", 0.0) or 0.0),
        "sale_date": str(getattr(mortgage, "sale_date", "") or ""),
    }


def deserialize_mortgage(item: Any) -> Optional[Mortgage]:
    if not isinstance(item, dict):
        return None
    try:
        tracks_raw = item.get("tracks") or []
        tracks: List[MortgageTrack] = []
        if isinstance(tracks_raw, list):
            for t in tracks_raw:
                track = deserialize_track(t)
                if track is not None:
                    tracks.append(track)

        excluded_raw = item.get("excluded_movement_ids") or []
        excluded: List[str] = []
        if isinstance(excluded_raw, list):
            excluded = [str(x) for x in excluded_raw if str(x).strip()]

        return Mortgage(
            id=str(item.get("id", "")).strip() or generate_mortgage_id(),
            name=str(item.get("name", "") or ""),
            account_name=str(item.get("account_name", "") or ""),
            vendor_query=str(item.get("vendor_query", "") or ""),
            start_date=str(item.get("start_date", "") or ""),
            tracks=tracks,
            excluded_movement_ids=excluded,
            archived=bool(item.get("archived", False)),
            property_price=float(item.get("property_price", 0.0) or 0.0),
            price_query=str(item.get("price_query", "") or ""),
            one_time_costs=_deserialize_costs(item.get("one_time_costs")),
            monthly_costs=_deserialize_costs(item.get("monthly_costs")),
            funding_sources=_deserialize_funding(item.get("funding_sources")),
            kind=_parse_asset_kind(item.get("kind")),
            current_value=float(item.get("current_value", 0.0) or 0.0),
            sold=bool(item.get("sold", False)),
            sale_price=float(item.get("sale_price", 0.0) or 0.0),
            sale_date=str(item.get("sale_date", "") or ""),
        )
    except Exception:
        return None


class JsonFileMortgageProvider(MortgageProvider):
    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self._explicit_path: Optional[Path] = Path(path) if path else None

    def _get_path(self) -> Path:
        if self._explicit_path is not None:
            return self._explicit_path
        key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
        suffix = f"_{key}" if key else ""
        return accounts_data_dir() / f"mortgages{suffix}.json"

    def list_mortgages(self) -> List[Mortgage]:
        p = self._get_path()
        if not p.exists():
            return []
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        out: List[Mortgage] = []
        for item in data:
            mortgage = deserialize_mortgage(item)
            if mortgage is not None:
                out.append(mortgage)
        return out

    def save_mortgages(self, mortgages: List[Mortgage]) -> None:
        import os

        p = self._get_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = [serialize_mortgage(m) for m in mortgages]
        tmp = p.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)

    def upsert_mortgage(self, mortgage: Mortgage) -> None:
        mortgages = self.list_mortgages()
        updated: List[Mortgage] = []
        found = False
        for m in mortgages:
            if m.id == mortgage.id:
                updated.append(mortgage)
                found = True
            else:
                updated.append(m)
        if not found:
            updated.append(mortgage)
        self.save_mortgages(updated)

    def delete_mortgage(self, mortgage_id: str) -> None:
        mortgage_id = str(mortgage_id or "").strip()
        if not mortgage_id:
            return
        mortgages = [m for m in self.list_mortgages() if m.id != mortgage_id]
        self.save_mortgages(mortgages)
