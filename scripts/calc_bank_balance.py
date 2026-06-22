"""Compute a bank account's balance from first principles and reconcile it
against the stored value.

The app derives every bank balance the same way ``recalculate_account_balances``
does:

    balance = baseline_amount  +  sum(all movements for that account)

where "all movements" INCLUDES transfer movements (``is_transfer=True``), since
a transfer in/out of a bank is recorded as a normal ``BankMovement`` under the
bank's name. This script makes that math explicit and shows a breakdown:

    init (baseline)
  + regular movements (income/expenses, is_transfer=False)
  + transfer movements (is_transfer=True)            <- in & out
  ------------------------------------------------
  = computed balance        vs.  stored total_amount

It reads the raw per-workspace JSON files directly (no provider caching / no
workspace-resolution surprises). Defaults to the active workspace; override with
--workspace.

Usage:
  python scripts/calc_bank_balance.py                 # all bank accounts, active workspace
  python scripts/calc_bank_balance.py --account בנק    # one account
  python scripts/calc_bank_balance.py --account בנק --list-transfers
  python scripts/calc_bank_balance.py --workspace IFX9-ML92-5BIC
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _round(x: float) -> float:
    return round(float(x or 0.0), 2)


def _read_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return data
    # tolerate wrapped shapes
    for key in ("accounts", "bank_accounts", "movements"):
        if isinstance(data, dict) and isinstance(data.get(key), list):
            return data[key]
    return []


def main() -> int:
    from finance.utils.app_paths import accounts_data_dir

    p = argparse.ArgumentParser()
    p.add_argument(
        "--workspace",
        default=None,
        help="Workspace id suffix (e.g. IFX9-ML92-5BIC). Default: active workspace.",
    )
    p.add_argument(
        "--account",
        default=None,
        help="Only this bank account name (e.g. בנק). Default: all bank accounts.",
    )
    p.add_argument(
        "--list-transfers",
        action="store_true",
        help="List every transfer movement that affects each account.",
    )
    args = p.parse_args()

    # Resolve workspace key.
    key = args.workspace
    if key is None:
        try:
            from finance.models.firebase_session import (
                current_firebase_workspace_id,
                current_firebase_uid,
            )

            key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
        except Exception:
            key = ""
    suffix = f"_{key}" if key else ""

    d = accounts_data_dir()
    accounts_path = d / f"bank_accounts{suffix}.json"
    movements_path = d / f"bank_movements{suffix}.json"

    print(f"workspace : {key or '(none)'}")
    print(f"accounts  : {accounts_path}")
    print(f"movements : {movements_path}")
    print()

    accounts = _read_json_list(accounts_path)
    movements = _read_json_list(movements_path)

    # Bucket movements by account name → (regular_sum, transfer_sum, transfers[]).
    regular: Dict[str, float] = {}
    transfer: Dict[str, float] = {}
    transfer_rows: Dict[str, List[dict]] = {}
    for m in movements:
        name = str(m.get("account_name", "") or "").strip()
        if not name:
            continue
        amt = float(m.get("amount", 0.0) or 0.0)
        if bool(m.get("is_transfer", False)):
            transfer[name] = transfer.get(name, 0.0) + amt
            transfer_rows.setdefault(name, []).append(m)
        else:
            regular[name] = regular.get(name, 0.0) + amt

    bank_accounts = [
        a
        for a in accounts
        if str(a.get("kind", "") or "").strip().lower() != "budget"
        and str(a.get("kind", "") or "").strip().lower() != "saving"
    ]
    if args.account:
        bank_accounts = [
            a for a in bank_accounts if str(a.get("name", "")).strip() == args.account.strip()
        ]
        if not bank_accounts:
            print(f"No bank account named {args.account!r} in this workspace.")
            return 1

    any_mismatch = False
    for a in bank_accounts:
        name = str(a.get("name", "")).strip()
        init = float(a.get("baseline_amount", 0.0) or 0.0)
        reg = regular.get(name, 0.0)
        tr = transfer.get(name, 0.0)
        computed = init + reg + tr
        stored = float(a.get("total_amount", 0.0) or 0.0)
        diff = computed - stored
        match = abs(diff) < 0.005

        n_reg = sum(
            1
            for m in movements
            if str(m.get("account_name", "")).strip() == name
            and not bool(m.get("is_transfer", False))
        )
        n_tr = len(transfer_rows.get(name, []))

        # What the APP actually displays: BankAccount.__post_init__ overrides
        # total_amount with the latest-by-date history snapshot. Replicate that
        # using the same date parser, and surface future-dated snapshots — those
        # silently win the "latest" sort and freeze the headline balance.
        from finance.models.accounts import parse_iso_date
        from datetime import datetime

        hist = a.get("history") or []
        parsed = [
            (parse_iso_date(str(s.get("date", ""))), str(s.get("date", "")), float(s.get("amount", 0.0) or 0.0))
            for s in hist
            if isinstance(s, dict)
        ]
        displayed = None
        if parsed:
            displayed = sorted(parsed, key=lambda t: t[0])[-1]
        today = datetime.now()
        future = sorted([t for t in parsed if t[0] > today], key=lambda t: t[0])

        print(f"━━ {name} ━━")
        print(f"  init (baseline)            : {_round(init):>15,.2f}")
        print(f"  + regular movements ({n_reg:>4}) : {_round(reg):>15,.2f}")
        print(f"  + transfer movements ({n_tr:>3}) : {_round(tr):>15,.2f}")
        print(f"  ----------------------------------------------")
        print(f"  = computed balance         : {_round(computed):>15,.2f}   <- init + movements (the real balance)")
        if displayed is not None:
            d_amt = displayed[2]
            print(f"  app shows (latest snapshot): {_round(d_amt):>15,.2f}   <- history point dated {displayed[1]}")
            if abs(d_amt - computed) >= 0.005:
                any_mismatch = True
                print(f"    ✗ APP DISAGREES by {_round(d_amt - computed):,.2f}")
        if future:
            any_mismatch = True
            print(f"  ⚠ {len(future)} FUTURE-dated history snapshot(s) (parsed date > today) — these hijack the displayed balance:")
            for dt, ds, amt in future:
                print(f"      {ds:<12} -> {amt:>15,.2f}")

        if args.list_transfers and transfer_rows.get(name):
            print("    transfers:")
            for m in sorted(transfer_rows[name], key=lambda r: str(r.get("date", ""))):
                sign = "+" if float(m.get("amount", 0)) >= 0 else "-"
                print(
                    f"      {str(m.get('date','')):<12} {sign}{abs(float(m.get('amount',0))):>13,.2f}"
                    f"  {str(m.get('description','') or '')[:50]}"
                )
        print()

    return 1 if any_mismatch else 0


if __name__ == "__main__":
    raise SystemExit(main())
