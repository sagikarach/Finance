"""Rename / merge / add expense categories in the current budget's hierarchy.

    python scripts/edit_categories.py --merge food.cafes=food.restaurants \\
        --rename food.restaurants="אוכל בחוץ" --add transport.rental="השכרת רכב"@transport
    (dry run by default; add --apply to write, push the changed records,
    refresh notifications once and rebuild the classifier once)

    python scripts/edit_categories.py --corrections reviewed.json [--apply]
    (per-movement fixes from a reviewed list: [{"movement_id", "expected",
    "category", "reason"}]; a record whose category is no longer "expected"
    is left alone)

Run it with the app closed. ``--data-dir DIR --key WS --no-push`` works on a
copy. ``--restore BACKUP_DIR`` copies a backup back (then press Sync).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _pairs(values, sep="="):
    out = {}
    for v in values or []:
        k, _, rest = v.partition(sep)
        if not k or not rest:
            raise SystemExit(f"bad value: {v!r} (expected KEY{sep}VALUE)")
        out[k.strip()] = rest.strip()
    return out


def main() -> int:
    from finance.models.category_edits import (
        CategoryEdit,
        apply_category_edit,
        restore_backup,
    )
    from finance.models.category_migration import FirebaseMigrationPusher, WorkspaceFiles
    from finance.models.category_tree import CategoryNode

    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="append", help="SOURCE_ID=TARGET_ID")
    ap.add_argument("--rename", action="append", help="ID=NEW NAME")
    ap.add_argument("--add", action="append", help="ID=NAME or ID=NAME@PARENT_ID")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--restore", type=Path)
    ap.add_argument("--corrections", type=Path, help="reviewed per-movement list (JSON)")
    ap.add_argument("--data-dir", type=Path)
    ap.add_argument("--key", default="")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    files = (WorkspaceFiles(accounts_dir=args.data_dir, key=args.key)
             if args.data_dir else WorkspaceFiles.current())
    if args.restore:
        print(json.dumps({"restored": restore_backup(files, args.restore)}, ensure_ascii=False))
        return 0

    additions = []
    for nid, spec in _pairs(args.add).items():
        name, _, parent = spec.partition("@")
        additions.append(CategoryNode(nid, name.strip(), parent.strip() or None))
    edit = CategoryEdit(renames=_pairs(args.rename), merges=_pairs(args.merge),
                        additions=additions)

    def refresh() -> None:
        from finance.data.action_history_provider import JsonFileActionHistoryProvider
        from finance.data.bank_movement_provider import JsonFileBankMovementProvider
        from finance.data.installment_plan_provider import JsonFileInstallmentPlanProvider
        from finance.data.mortgage_provider import JsonFileMortgageProvider
        from finance.data.notifications_provider import JsonFileNotificationsProvider
        from finance.data.one_time_event_provider import JsonFileOneTimeEventProvider
        from finance.models.notifications_service import NotificationsService

        p = files.path
        NotificationsService(
            provider=JsonFileNotificationsProvider(p("notifications")),
            movement_provider=JsonFileBankMovementProvider(p("bank_movements")),
            history_provider=JsonFileActionHistoryProvider(p("action_history")),
            installment_provider=JsonFileInstallmentPlanProvider(p("installment_plans")),
            mortgage_provider=JsonFileMortgageProvider(p("mortgages")),
            event_provider=JsonFileOneTimeEventProvider(p("one_time_events")),
        ).refresh()

    def retrain() -> None:
        from finance.data.bank_movement_provider import JsonFileBankMovementProvider
        from finance.models.movement_classifier import SimilarityBasedClassifier
        from finance.models.workspace_ml_trainer import WorkspaceMLTrainer

        WorkspaceMLTrainer().rebuild_training_file(
            movements=JsonFileBankMovementProvider(files.movements).list_movements(),
            classifier=SimilarityBasedClassifier(),
        )

    if args.corrections:
        from finance.models.category_edits import MovementCorrection, apply_movement_corrections

        items = json.loads(args.corrections.read_text(encoding="utf-8"))
        corrections = [MovementCorrection(**{k: str(v) for k, v in it.items()}) for it in items]
        rep = apply_movement_corrections(
            files, corrections, dry_run=not args.apply,
            pusher=None if (args.no_push or not args.apply) else FirebaseMigrationPusher(),
            refresh=refresh if args.apply else None,
            retrain=retrain if (args.apply and not args.data_dir) else None,
        )
        print(json.dumps({
            "mode": rep.mode, "changed": rep.changed, "already": rep.already,
            "conflicts": rep.conflicts, "missing": rep.missing,
            "backup_dir": rep.backup_dir,
            "pushed": vars(rep.pushed) if rep.pushed else None,
            "notification_refreshes": rep.refreshed, "classifier_rebuilds": rep.retrained,
        }, ensure_ascii=False, indent=2))
        return 0

    report = apply_category_edit(
        files, edit, dry_run=not args.apply,
        pusher=None if (args.no_push or not args.apply) else FirebaseMigrationPusher(),
        refresh=refresh if args.apply else None,
        retrain=retrain if (args.apply and not args.data_dir) else None,
    )
    print(json.dumps({
        "mode": report.mode,
        "moved": report.moved,
        "changed_movements": report.changed_movements,
        "changed_plans": report.changed_plans,
        "changed_mortgages": report.changed_mortgages,
        "tree_changed": report.tree_changed,
        "backup_dir": report.backup_dir,
        "pushed": vars(report.pushed) if report.pushed else None,
        "notification_refreshes": report.refreshed,
        "classifier_rebuilds": report.retrained,
        "timings_sec": {k: round(v, 4) for k, v in report.timings.items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
