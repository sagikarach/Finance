from __future__ import annotations

import argparse
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List
import json
import sys
import uuid

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _parse_date_to_iso(value: Any) -> str:
    s = str(value or "").strip()
    for ch in (
        "\u200e",
        "\u200f",
        "\u202a",
        "\u202b",
        "\u202c",
        "\u202d",
        "\u202e",
    ):
        s = s.replace(ch, "")
    if not s:
        return ""

    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]

    try:
        if "/" in s:
            parts = [p.strip() for p in s.split("/")]
            if len(parts) == 3 and all(parts):
                dd, mm, yy = parts[0], parts[1], parts[2]
                if len(yy) == 4 and len(dd) in (1, 2) and len(mm) in (1, 2):
                    d = _date(int(yy), int(mm), int(dd))
                    return d.isoformat()
        if "." in s:
            parts = [p.strip() for p in s.split(".")]
            if len(parts) == 3 and all(parts):
                dd, mm, yy = parts[0], parts[1], parts[2]
                if len(yy) == 4 and len(dd) in (1, 2) and len(mm) in (1, 2):
                    d = _date(int(yy), int(mm), int(dd))
                    return d.isoformat()
    except Exception:
        pass

    for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%d/%m/%y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue

    return s


def _map_movement_type(value: Any):
    from finance.models.bank_movement import MovementType

    s = str(value or "").strip()
    if not s:
        return MovementType.ONE_TIME
    if "חודש" in s:
        return MovementType.MONTHLY
    if "שנת" in s:
        return MovementType.YEARLY
    if "חד" in s:
        return MovementType.ONE_TIME
    return MovementType.ONE_TIME


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _ensure_str(value: Any, default: str = "") -> str:
    s = str(value) if isinstance(value, (str, int, float)) else ""
    s = s.strip()
    return s if s else default


def _stable_movement_id(*parts: Any) -> str:
    text = "|".join(str(p or "").strip() for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, text))


def _dedupe_movements(movements: Iterable[object]) -> List[object]:
    by_id: Dict[str, object] = {}
    for m in movements:
        mid = str(getattr(m, "id", "") or "").strip()
        if not mid:
            continue
        by_id[mid] = m
    return list(by_id.values())


def _collect_from_firebase_combined(path: Path) -> List[object]:
    from finance.models.bank_movement import BankMovement

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return []

    incomes = data.get("incomes", [])
    expenses = data.get("expenses", [])
    out: List[BankMovement] = []

    if isinstance(incomes, list):
        for it in incomes:
            if not isinstance(it, dict):
                continue
            d = _parse_date_to_iso(it.get("date"))
            if not d:
                continue
            amt = abs(_to_float(it.get("amount"), 0.0))
            account_name = _ensure_str(it.get("destination"), "")
            if not account_name:
                account_name = _ensure_str(it.get("source"), "בנק")
            category = _ensure_str(it.get("source"), "") or _ensure_str(
                it.get("category"), "הכנסה"
            )
            mtype = _map_movement_type(it.get("type"))
            desc = _ensure_str(it.get("description"), "")
            mid = _ensure_str(it.get("id")) or _stable_movement_id(
                "firebase-income",
                account_name,
                d,
                desc,
                amt,
                category,
                getattr(mtype, "value", str(mtype)),
            )
            out.append(
                BankMovement(
                    id=mid,
                    date=d,
                    amount=float(amt),
                    account_name=account_name,
                    category=category,
                    type=mtype,
                    description=desc or None,
                    event_id=None,
                )
            )

    if isinstance(expenses, list):
        for it in expenses:
            if not isinstance(it, dict):
                continue
            d = _parse_date_to_iso(it.get("date"))
            if not d:
                continue
            amt = -abs(_to_float(it.get("amount"), 0.0))
            account_name = _ensure_str(it.get("expenseSource"), "")
            if not account_name:
                account_name = _ensure_str(it.get("source"), "") or _ensure_str(
                    it.get("destination"), ""
                )
            if not account_name:
                continue
            category = _ensure_str(it.get("category"), "שונות")
            mtype = _map_movement_type(it.get("expenseType") or it.get("type"))
            desc = _ensure_str(it.get("description"), "")
            mid = _ensure_str(it.get("id")) or _stable_movement_id(
                "firebase-expense",
                account_name,
                d,
                desc,
                abs(float(amt)),
                category,
                getattr(mtype, "value", str(mtype)),
            )
            is_transfer = bool(it.get("is_transfer", False))
            if not is_transfer:
                try:
                    if str(category or "").strip() == "העברה":
                        is_transfer = True
                except Exception:
                    pass
            out.append(
                BankMovement(
                    id=mid,
                    date=d,
                    amount=float(amt),
                    account_name=account_name,
                    category=category,
                    type=mtype,
                    is_transfer=is_transfer,
                    description=desc or None,
                    event_id=None,
                )
            )

    return list(_dedupe_movements(out))


def _merge_local(
    *,
    provider: object,
    imported: List[object],
    mode: str,
) -> List[object]:
    if mode == "replace":
        final_movements = list(imported)
    else:
        existing = provider.list_movements()  # type: ignore[attr-defined]
        by_id: Dict[str, object] = {str(getattr(m, "id", "")): m for m in existing}
        for m in imported:
            mid = str(getattr(m, "id", "") or "").strip()
            if mid and mid not in by_id:
                by_id[mid] = m
        final_movements = _dedupe_movements(by_id.values())
    provider.save_movements(list(final_movements))  # type: ignore[attr-defined]
    return list(final_movements)


def _recalc_accounts_from_provider() -> None:
    # Keep desktop consistent if user also writes local cache.
    from finance.data.bank_movement_provider import JsonFileBankMovementProvider
    from finance.data.provider import JsonFileAccountsProvider
    from finance.models.accounts_service import AccountsService

    provider = JsonFileBankMovementProvider()
    accounts_provider = JsonFileAccountsProvider()
    accounts_svc = AccountsService(accounts_provider)
    accounts = accounts_svc.load_accounts()

    # Reuse the existing balance recalculation logic from BankMovementService (already used elsewhere).
    try:
        from finance.models.bank_movement_service import BankMovementService
        from finance.data.action_history_provider import JsonFileActionHistoryProvider

        svc = BankMovementService(
            movement_provider=provider,
            history_provider=JsonFileActionHistoryProvider(),
        )
        updated = svc.recalculate_account_balances(accounts)
    except Exception:
        updated = accounts

    try:
        accounts_svc.save_all(updated)
    except Exception:
        pass


def main() -> int:
    from finance.data.bank_movement_provider import JsonFileBankMovementProvider
    from finance.models.firebase_session import (
        current_firebase_uid,
        current_firebase_workspace_id,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to firebase-combined.json",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push movements to Firebase (requires valid session + workspace).",
    )
    parser.add_argument(
        "--write-local",
        action="store_true",
        help="Also write movements to local cache file for the current workspace/uid key.",
    )
    parser.add_argument(
        "--mode",
        choices=("merge", "replace"),
        default="merge",
        help="When --write-local is used: merge into existing cache or replace it.",
    )
    args = parser.parse_args()

    src = Path(args.path).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"File not found: {src}")

    imported = list(_collect_from_firebase_combined(src))
    print(f"Parsed movements: {len(imported)}")

    if args.write_local:
        provider = JsonFileBankMovementProvider()
        final_movements = _merge_local(
            provider=provider, imported=imported, mode=str(args.mode)
        )
        print(f"Local movements saved: {len(final_movements)}")
        try:
            _recalc_accounts_from_provider()
        except Exception:
            pass

    if args.push:
        from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter
        from finance.models.bank_movement import BankMovement as _BankMovement

        w = FirebaseWorkspaceWriter()
        pushed = 0
        for m in imported:
            if not isinstance(m, _BankMovement):
                continue
            try:
                w.upsert_movement(m)
                pushed += 1
            except Exception:
                continue
        print(f"Pushed movements: {pushed}")

    wid = current_firebase_workspace_id()
    uid = current_firebase_uid()
    key = wid or uid or "(none)"
    print(f"Workspace/uid key: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
