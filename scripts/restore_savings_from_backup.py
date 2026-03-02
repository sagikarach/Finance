"""
Restore savings accounts from a mobile-app backup JSON into Firebase.

The backup stores individual Savings items (each with a name, type, balance,
history).  The desktop app groups them under parent SavingsAccount categories.

Grouping rules (type field → parent SavingsAccount name):
    פנסיה            → פנסיה          (is_liquid=False)
    קרן השתלמות      → קרן השתלמות   (is_liquid=False)
    קופת גמל         → קופת גמל      (is_liquid=True)
    קופת גמל להשקעה  → קופת גמל להשקעה (is_liquid=True)
    פיקדון           → פיקדון         (is_liquid=True)
    חיסכון לדירה     → פיקדון         (is_liquid=True)  ← user confirmed

Usage:
    cd /Users/sagikarach/private/Finance
    python scripts/restore_savings_from_backup.py
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from dataclasses import asdict
from datetime import date as _date
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path so we can import from finance/
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from finance.models.accounts import MoneySnapshot, Savings, SavingsAccount, parse_iso_date
from finance.models.firebase_client import FirestoreClient
from finance.models.firebase_session import FirebaseSessionStore
from finance.models.firebase_session_manager import FirebaseSessionManager
from finance.utils.app_paths import accounts_data_dir

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BACKUP_PATH = Path("/Users/sagikarach/Desktop/finence-data-backup-20250909/savings-data.json")
TARGET_WORKSPACE = "IFX9-ML92-5BIC"

# Maps backup `type` field → (parent SavingsAccount name, is_liquid)
TYPE_TO_ACCOUNT: dict[str, tuple[str, bool]] = {
    "פנסיה":            ("פנסיה",             False),
    "קרן השתלמות":      ("קרן השתלמות",       False),
    "קופת גמל":         ("קופת גמל",          True),
    "קופת גמל להשקעה":  ("קופת גמל להשקעה",   True),
    "פיקדון":           ("פיקדון",             True),
    "חיסכון לדירה":     ("פיקדון",             True),   # user confirmed
}


# ---------------------------------------------------------------------------
# Helper: normalise an ISO-8601 timestamp → YYYY-MM-DD
# ---------------------------------------------------------------------------
def _date_only(iso: str) -> str:
    """'2025-06-01T20:14:53.942Z'  →  '2025-06-01'"""
    return str(iso or "")[:10]


# ---------------------------------------------------------------------------
# Convert one backup item → Savings child
# ---------------------------------------------------------------------------
def _backup_item_to_savings(raw: dict) -> Savings:
    name = str(raw.get("name") or "").strip()
    root_balance = float(raw.get("balance") or 0.0)

    raw_history = raw.get("history") or []
    snapshots: list[MoneySnapshot] = []
    for entry in raw_history:
        d = _date_only(str(entry.get("date") or ""))
        amt = float(entry.get("balance") or 0.0)
        if not d:
            continue
        # Deduplicate by date – keep the last occurrence per day.
        snapshots = [s for s in snapshots if s.date != d]
        snapshots.append(MoneySnapshot(date=d, amount=amt))

    snapshots.sort(key=lambda s: parse_iso_date(s.date))

    # If the root balance differs from the latest history snapshot, append
    # today's date with the root balance so the app shows the correct value.
    today = _date.today().isoformat()
    latest_hist_amount = snapshots[-1].amount if snapshots else None
    if latest_hist_amount != root_balance:
        snapshots = [s for s in snapshots if s.date != today]
        snapshots.append(MoneySnapshot(date=today, amount=root_balance))

    # Savings.__post_init__ recalculates amount from latest history entry.
    return Savings(name=name, amount=root_balance, history=snapshots)


# ---------------------------------------------------------------------------
# Build grouped SavingsAccount list from backup
# ---------------------------------------------------------------------------
def _build_savings_accounts(raw_accounts: list[dict]) -> list[SavingsAccount]:
    # Use OrderedDict to preserve insertion order.
    groups: OrderedDict[str, tuple[bool, list[Savings]]] = OrderedDict()

    for raw in raw_accounts:
        item_type = str(raw.get("type") or "").strip()
        if item_type not in TYPE_TO_ACCOUNT:
            print(f"  ⚠ Unknown type '{item_type}' for '{raw.get('name')}' – skipping.")
            continue
        account_name, is_liquid = TYPE_TO_ACCOUNT[item_type]
        savings_child = _backup_item_to_savings(raw)
        if account_name not in groups:
            groups[account_name] = (is_liquid, [])
        groups[account_name][1].append(savings_child)

    result: list[SavingsAccount] = []
    for account_name, (is_liquid, children) in groups.items():
        # SavingsAccount.__post_init__ sums children → total_amount is set automatically.
        acc = SavingsAccount(name=account_name, total_amount=0.0, is_liquid=is_liquid, savings=children)
        result.append(acc)
    return result


# ---------------------------------------------------------------------------
# Serialise to the format expected by meta/accounts and local JSON
# ---------------------------------------------------------------------------
def _serialise_savings(accounts: list[SavingsAccount]) -> list[dict]:
    return [asdict(acc) for acc in accounts]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # --- 1. Load backup -------------------------------------------------------
    print(f"Reading backup from: {BACKUP_PATH}")
    backup = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
    raw_accounts = backup.get("accounts") or []
    print(f"  Found {len(raw_accounts)} savings items in backup.\n")

    # --- 2. Group into SavingsAccounts ----------------------------------------
    savings_accounts = _build_savings_accounts(raw_accounts)
    print("Grouped savings accounts:")
    for acc in savings_accounts:
        print(f"  [{acc.name}]  total: {acc.total_amount:,.2f} ₪  |  liquid: {acc.is_liquid}")
        for s in acc.savings:
            print(f"      • {s.name}: {s.amount:,.2f} ₪  ({len(s.history)} history entries)")

    # --- 3. Authenticate using the stored session -----------------------------
    store = FirebaseSessionStore()
    try:
        session = FirebaseSessionManager(store=store).get_valid_session()
    except RuntimeError as e:
        print(f"\n✗ Not logged in: {e}")
        print("  Open the app, go to Settings → שיתוף וסנכרון, connect to Firebase,")
        print("  then run this script again.")
        sys.exit(1)

    fs = FirestoreClient(project_id=session.project_id)
    id_token = session.id_token
    doc_path = f"workspaces/{TARGET_WORKSPACE}/meta/accounts"

    # --- 4. Read existing meta/accounts to preserve bank accounts -------------
    print(f"\nFetching existing {doc_path} …")
    existing_doc = fs.get_document(document_path=doc_path, id_token=id_token)
    existing_bank: list = []
    if isinstance(existing_doc, dict):
        _, parsed = fs.parse_any_doc(existing_doc)
        existing_bank = list(parsed.get("bank_accounts") or [])
        print(f"  Existing bank accounts preserved: {len(existing_bank)}")
    else:
        print("  No existing meta/accounts document found – bank_accounts will be empty.")

    # --- 5. Write to Firebase -------------------------------------------------
    new_savings_payload = _serialise_savings(savings_accounts)
    print(f"\nWriting {len(new_savings_payload)} savings account groups to Firebase …")
    fs.upsert_document(
        document_path=doc_path,
        id_token=id_token,
        fields={
            "bank_accounts": existing_bank,
            "savings_accounts": new_savings_payload,
            "version": 1,
        },
    )
    print("  ✓ Firebase write successful.")

    # --- 6. Save locally so the app reads it immediately without a pull ------
    local_path = accounts_data_dir() / f"savings_accounts_{TARGET_WORKSPACE}.json"
    print(f"\nSaving local cache to: {local_path}")
    local_payload = []
    for acc in savings_accounts:
        savings_list = [
            {
                "name": s.name,
                "amount": s.amount,
                "history": [{"date": h.date, "amount": h.amount} for h in s.history],
            }
            for s in acc.savings
        ]
        local_payload.append({
            "name": acc.name,
            "is_liquid": acc.is_liquid,
            "total_amount": acc.total_amount,
            "savings": savings_list,
        })
    local_path.write_text(json.dumps(local_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ✓ Local file written.")

    print("\n✓ Restore complete!")
    print(f"  Workspace        : {TARGET_WORKSPACE}")
    print(f"  Account groups   : {len(savings_accounts)}")
    print(f"  Total savings    : {sum(a.total_amount for a in savings_accounts):,.2f} ₪")


if __name__ == "__main__":
    main()
