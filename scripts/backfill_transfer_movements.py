"""One-time backfill: create the outgoing transfer movements that older
transfers never recorded.

Before transfers started writing a ``BankMovement`` ledger record, an in-app
transfer only adjusted balances and logged a ``TransferAction`` in the action
history. As a result, money moved out of a funding account/saving was invisible
to views that aggregate transfers (e.g. an asset's funding contributions).

This script reads the local action-history log, and for every ``TransferAction``
that has no matching transfer movement yet, creates one (negative amount,
``is_transfer=True``, category "העברה", dated to the original transfer) — exactly
what ``AccountsService.apply_transfer_request`` now creates going forward. New
movements are saved locally and, unless ``--local-only`` is passed, pushed to
Firebase so they reach mobile/other devices.

Idempotent: matching transfers are deduplicated by (account_name, amount, date),
so re-running only creates what is still missing.

Usage:
  python scripts/backfill_transfer_movements.py --dry-run
  python scripts/backfill_transfer_movements.py
  python scripts/backfill_transfer_movements.py --local-only
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import List, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _key(account_name: str, amount: float, date: str) -> Tuple[str, float, str]:
    return (str(account_name or "").strip(), round(float(amount or 0.0), 2), str(date or "").strip())


def main() -> int:
    from finance.data.action_history_provider import JsonFileActionHistoryProvider
    from finance.data.bank_movement_provider import JsonFileBankMovementProvider
    from finance.models.action_history import TransferAction
    from finance.models.bank_movement import BankMovement, MovementType

    p = argparse.ArgumentParser()
    p.add_argument(
        "--dry-run", action="store_true", help="Only print what would change."
    )
    p.add_argument(
        "--local-only",
        action="store_true",
        help="Persist locally but do not push to Firebase.",
    )
    args = p.parse_args()

    history_provider = JsonFileActionHistoryProvider()
    movement_provider = JsonFileBankMovementProvider()

    history = list(history_provider.list_history())
    existing = list(movement_provider.list_movements())

    # Multiset of transfer movements already on record, so already-recorded
    # transfers (and prior backfill runs) are not duplicated.
    existing_transfers: Counter = Counter()
    for m in existing:
        try:
            if bool(getattr(m, "is_transfer", False)):
                existing_transfers[
                    _key(m.account_name, m.amount, m.date)
                ] += 1
        except Exception:
            continue

    original_transfer_count = sum(existing_transfers.values())

    to_create: List[BankMovement] = []
    transfers_seen = 0
    for entry in history:
        action = getattr(entry, "action", None)
        if not isinstance(action, TransferAction):
            continue
        transfers_seen += 1

        amount = abs(float(getattr(action, "amount", 0.0) or 0.0))
        src_name = str(getattr(action, "source_name", "") or "").strip()
        dst_name = str(getattr(action, "target_name", "") or "").strip()
        date = str(getattr(entry, "timestamp", "") or "").strip()
        if amount <= 0 or not src_name or not date:
            continue

        k = _key(src_name, -amount, date)
        if existing_transfers.get(k, 0) > 0:
            existing_transfers[k] -= 1  # already recorded — skip
            continue

        to_create.append(
            BankMovement(
                amount=-amount,
                date=date,
                account_name=src_name,
                category="העברה",
                type=MovementType.ONE_TIME,
                is_transfer=True,
                description=f"העברה מ{src_name} ל{dst_name}",
            )
        )

    print(f"Transfer actions in history: {transfers_seen}")
    print(f"Existing transfer movements: {original_transfer_count}")
    print(f"Missing transfer movements to create: {len(to_create)}")

    if args.dry_run:
        for mv in to_create[:30]:
            print(f"- would create {mv.account_name} {mv.amount} on {mv.date}")
        if len(to_create) > 30:
            print(f"... and {len(to_create) - 30} more")
        return 0

    if not to_create:
        print("Nothing to backfill.")
        return 0

    # Persist locally in one snapshot write.
    try:
        movement_provider.save_movements(existing + to_create)
    except Exception as e:
        print(f"Failed to save movements locally: {e}")
        return 1
    print(f"Saved {len(to_create)} movement(s) locally.")

    if args.local_only:
        print("Skipping Firebase push (--local-only).")
        return 0

    # Push new movements to Firebase.
    try:
        from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter

        writer = FirebaseWorkspaceWriter()
    except Exception as e:
        print(f"Could not init Firebase writer (saved locally only): {e}")
        return 0

    pushed = 0
    for mv in to_create:
        try:
            writer.upsert_movement(mv)
            pushed += 1
        except Exception as e:
            print(f"Failed to push movement {mv.id}: {e}")
            continue
    print(f"Pushed {pushed}/{len(to_create)} movement(s) to Firebase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
