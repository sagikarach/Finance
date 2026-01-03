from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, TYPE_CHECKING
import json
import sys
import uuid

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

if TYPE_CHECKING:
    from finance.models.accounts import MoneySnapshot
    from finance.models.bank_movement import BankMovement


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _to_iso_date(value: Any) -> str:
    s = str(value or "").strip()
    if not s:
        return ""
    for ch in ("\u200e", "\u200f", "\u202a", "\u202b", "\u202c", "\u202d", "\u202e"):
        s = s.replace(ch, "")
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    if "T" in s:
        s = s.split("T", 1)[0]
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
    for fmt in ("%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    return s


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _stable_id(*parts: Any) -> str:
    text = "|".join(str(p or "").strip() for p in parts)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, text))


def _normalize_history_rows(rows: Any) -> List[MoneySnapshot]:
    from finance.models.accounts import MoneySnapshot

    if not isinstance(rows, list):
        return []
    last_by_date: Dict[str, float] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        d = _to_iso_date(r.get("date"))
        if not d:
            continue
        bal = _to_float(r.get("balance"), _to_float(r.get("amount"), 0.0))
        last_by_date[d] = bal
    out = [MoneySnapshot(date=d, amount=a) for d, a in last_by_date.items()]
    out.sort(key=lambda s: s.date)
    return out


def _derive_saving_item_name(*, account_type: str, legacy_name: str) -> str:
    """
    Legacy file uses:
      - type: the 'saving account' name (product / bucket)
      - name: the specific saving under it (often includes person suffix)

    Examples:
      type="קופת גמל להשקעה", name="קופת גמל להשקעה - שגיא" -> "שגיא"
      type="פנסיה", name="פנסיה חן" -> "חן"
    """
    t = str(account_type or "").strip()
    n = str(legacy_name or "").strip()
    if not n:
        return "חיסכון"
    if t:
        prefix1 = f"{t} - "
        if n.startswith(prefix1):
            out = n[len(prefix1) :].strip()
            return out or n
        prefix2 = f"{t} "
        if n.startswith(prefix2):
            out = n[len(prefix2) :].strip()
            return out or n
        if n == t:
            return t
    return n


def _map_bank_name(name: str) -> str:
    n = str(name or "").strip()
    if not n:
        return ""
    if n == "עובר ושב":
        return "בנק"
    return n


def _is_bank_account_name(name: str) -> bool:
    return name in {"בנק", "מזומן", "ביט", "פייבוקס"}


def _transfer_movements_from_legacy(
    *, transfers: Any, known_savings_names: set[str]
) -> List[BankMovement]:
    from finance.models.bank_movement import BankMovement, MovementType

    if not isinstance(transfers, list):
        return []
    out: List[BankMovement] = []
    for t in transfers:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id", "") or "").strip() or _stable_id("transfer", t)
        d = _to_iso_date(t.get("date"))
        if not d:
            continue
        amount = abs(_to_float(t.get("amount"), 0.0))
        if amount <= 0:
            continue
        from_name = _map_bank_name(str(t.get("fromName", "") or "").strip())
        to_name = _map_bank_name(str(t.get("toName", "") or "").strip())
        if not from_name or not to_name:
            continue

        from_is_bank = _is_bank_account_name(from_name)
        to_is_bank = _is_bank_account_name(to_name)
        to_is_saving = to_name in known_savings_names
        from_is_saving = from_name in known_savings_names

        # Bank -> Bank: represent as 2 movements so derived balances remain correct.
        if from_is_bank and to_is_bank:
            out.append(
                BankMovement(
                    id=_stable_id("transfer", tid, "out"),
                    date=d,
                    amount=-amount,
                    account_name=from_name,
                    category="העברה",
                    type=MovementType.ONE_TIME,
                    is_transfer=True,
                    description=f"העברה ל{to_name}",
                    event_id=None,
                )
            )
            out.append(
                BankMovement(
                    id=_stable_id("transfer", tid, "in"),
                    date=d,
                    amount=amount,
                    account_name=to_name,
                    category="העברה",
                    type=MovementType.ONE_TIME,
                    is_transfer=True,
                    description=f"העברה מ{from_name}",
                    event_id=None,
                )
            )
            continue

        # Bank -> Saving: only the bank side affects bank derived balance; savings are imported separately.
        if from_is_bank and to_is_saving:
            out.append(
                BankMovement(
                    id=_stable_id("transfer", tid, "out"),
                    date=d,
                    amount=-amount,
                    account_name=from_name,
                    category="העברה",
                    type=MovementType.ONE_TIME,
                    is_transfer=True,
                    description=f"העברה לחיסכון: {to_name}",
                    event_id=None,
                )
            )
            continue

        # Saving -> Bank: only the bank side movement is needed for derived balance.
        if from_is_saving and to_is_bank:
            out.append(
                BankMovement(
                    id=_stable_id("transfer", tid, "in"),
                    date=d,
                    amount=amount,
                    account_name=to_name,
                    category="העברה",
                    type=MovementType.ONE_TIME,
                    is_transfer=True,
                    description=f"העברה מחיסכון: {from_name}",
                    event_id=None,
                )
            )
            continue

    return out


def _dedupe_by_id(movements: Iterable[BankMovement]) -> List[BankMovement]:
    out: Dict[str, BankMovement] = {}
    for m in movements:
        out[str(m.id)] = m
    return list(out.values())


def main() -> int:
    from finance.data.bank_movement_provider import JsonFileBankMovementProvider
    from finance.data.provider import JsonFileAccountsProvider
    from finance.models.accounts import (
        MoneyAccount,
        MoneySnapshot,
        Savings,
        SavingsAccount,
    )
    from finance.models.accounts_service import AccountsService
    from finance.models.bank_movement_service import BankMovementService
    from finance.models.firebase_session import (
        current_firebase_uid,
        current_firebase_workspace_id,
    )

    p = argparse.ArgumentParser()
    p.add_argument(
        "--src-file",
        type=str,
        default=str(Path.home() / "Desktop" / "data" / "savings-data.json"),
        help="Path to legacy savings-data.json",
    )
    p.add_argument(
        "--mode",
        choices=("merge", "replace"),
        default="merge",
        help="merge: merge into existing savings; replace: overwrite savings accounts",
    )
    p.add_argument(
        "--push",
        action="store_true",
        help="Also push accounts snapshot + new transfer movements/categories to Firebase (requires valid session).",
    )
    args = p.parse_args()

    src = Path(args.src_file).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"File not found: {src}")

    data = _read_json(src)
    legacy_accounts = data.get("accounts", []) if isinstance(data, dict) else []
    legacy_transfers = data.get("transfers", []) if isinstance(data, dict) else []

    imported_savings: List[SavingsAccount] = []
    known_names: set[str] = set()
    if isinstance(legacy_accounts, list):
        by_type: Dict[str, SavingsAccount] = {}
        for a in legacy_accounts:
            if not isinstance(a, dict):
                continue
            name = str(a.get("name", "") or "").strip()
            if not name:
                continue
            known_names.add(name)
            is_liquid = str(a.get("liquidity", "") or "").strip().lower() == "liquid"
            balance = _to_float(a.get("balance"), 0.0)
            hist = _normalize_history_rows(a.get("history", []))
            if not hist:
                start = _to_iso_date(a.get("startDate"))
                init_bal = _to_float(a.get("initialBalance"), balance)
                if start:
                    hist = [MoneySnapshot(date=start, amount=init_bal)]

            saving_account_name = str(a.get("type", "") or "").strip() or "חיסכון"
            saving_item_name = _derive_saving_item_name(
                account_type=saving_account_name, legacy_name=name
            )

            existing_acc = by_type.get(saving_account_name)
            if existing_acc is None:
                existing_acc = SavingsAccount(
                    name=saving_account_name,
                    total_amount=0.0,
                    is_liquid=bool(is_liquid),
                    savings=[],
                )

            # Merge/overwrite saving item by name within this savings account.
            new_item = Savings(
                name=saving_item_name,
                amount=float(balance),
                history=list(hist),
            )
            new_savings: List[Savings] = []
            replaced = False
            for s in list(existing_acc.savings):
                if str(getattr(s, "name", "") or "").strip() == saving_item_name:
                    new_savings.append(new_item)
                    replaced = True
                else:
                    new_savings.append(s)
            if not replaced:
                new_savings.append(new_item)

            by_type[saving_account_name] = SavingsAccount(
                name=existing_acc.name,
                total_amount=0.0,
                is_liquid=bool(existing_acc.is_liquid or is_liquid),
                savings=new_savings,
            )

        imported_savings = list(by_type.values())

    accounts_provider = JsonFileAccountsProvider()
    accounts_svc = AccountsService(accounts_provider)
    existing = accounts_svc.load_accounts()

    existing_non_savings: List[MoneyAccount] = [
        a for a in existing if not isinstance(a, SavingsAccount)
    ]
    existing_savings_by_name: Dict[str, SavingsAccount] = {
        a.name: a for a in existing if isinstance(a, SavingsAccount)
    }

    if args.mode == "replace":
        final_savings = imported_savings
    else:
        merged: Dict[str, SavingsAccount] = dict(existing_savings_by_name)
        for sa in imported_savings:
            merged[sa.name] = sa
        final_savings = list(merged.values())

    combined_accounts: List[MoneyAccount] = list(existing_non_savings) + list(
        final_savings
    )
    accounts_svc.save_all(combined_accounts)

    # Transfers -> bank movements (so bank derived balance matches legacy history)
    transfer_movements = _transfer_movements_from_legacy(
        transfers=legacy_transfers, known_savings_names=known_names
    )
    if transfer_movements:
        mv_provider = JsonFileBankMovementProvider()
        existing_movements = mv_provider.list_movements()
        by_id = {m.id: m for m in existing_movements}
        for m in transfer_movements:
            if m.id not in by_id:
                by_id[m.id] = m
        all_movements = _dedupe_by_id(by_id.values())
        mv_provider.save_movements(all_movements)

        # Ensure category exists in the per-type category lists
        try:
            income = set(mv_provider.list_categories_for_type(True))
            outcome = set(mv_provider.list_categories_for_type(False))
            for m in transfer_movements:
                if float(m.amount) > 0:
                    income.add("העברה")
                else:
                    outcome.add("העברה")
            mv_provider._save_categories_by_type(  # type: ignore[attr-defined]
                {"income": sorted(income), "outcome": sorted(outcome)}
            )
        except Exception:
            pass

        # Recompute balances (baseline + movements) after adding transfer movements.
        try:
            mv_svc = BankMovementService(
                mv_provider, history_provider=None, classifier=None
            )  # type: ignore[arg-type]
            recalced = mv_svc.recalculate_account_balances(accounts_svc.load_accounts())
            accounts_svc.save_all(recalced)
        except Exception:
            pass

        if args.push:
            from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter

            w = FirebaseWorkspaceWriter()
            for m in transfer_movements:
                try:
                    w.upsert_movement(m)
                except Exception:
                    continue
            try:
                income = mv_provider.list_categories_for_type(True)
                outcome = mv_provider.list_categories_for_type(False)
                w.upsert_categories(income=list(income), outcome=list(outcome))
            except Exception:
                pass
            try:
                w.upsert_accounts_snapshot(accounts_svc.load_accounts())
            except Exception:
                pass

    wid = current_firebase_workspace_id()
    uid = current_firebase_uid()
    key = wid or uid or "(none)"
    print(f"Savings accounts imported (grouped by type): {len(imported_savings)}")
    print(f"Transfer movements added: {len(transfer_movements)}")
    print(f"Workspace/uid key: {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
