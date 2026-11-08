"""Migrate the current budget's expense categories into the parent/subcategory
hierarchy (``finance/models/category_migration.py``).

    python scripts/migrate_categories.py                 # dry run (default)
    python scripts/migrate_categories.py --apply         # backup, apply, push, refresh
    python scripts/migrate_categories.py --rollback      # restore original categories
    python scripts/migrate_categories.py --report out.csv   # per-movement decisions

Run it with the app closed. ``--data-dir DIR --key WORKSPACE --no-push`` runs
against a copy of the files (no network). Progress goes to stderr; descriptions
are only written to the explicit ``--report`` file, never to logs.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _progress(stage: str, i: int, n: int) -> None:
    print(f"\r  {stage}: {i}/{n}", end="" if i < n else "\n", file=sys.stderr)


def _write_report(path: Path, files, plan) -> None:
    rows = json.loads(files.movements.read_text(encoding="utf-8"))
    by_id = {str(r.get("id")): r for r in rows}
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["movement_id", "date", "account", "amount", "description",
                    "old_category", "new_category", "kind", "reason", "review"])
        for d in plan.decisions:
            r = by_id.get(d.movement_id, {})
            w.writerow([d.movement_id, r.get("date"), r.get("account_name"), r.get("amount"),
                        r.get("description"), d.old_category, d.new_category, d.kind,
                        d.reason, d.review or ""])


def main() -> int:
    from finance.models.category_migration import (
        CategoryMigrationRunner,
        FirebaseMigrationPusher,
        WorkspaceFiles,
    )

    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    ap.add_argument("--data-dir", type=Path, help="accounts dir of a copy (implies --key)")
    ap.add_argument("--key", default="", help="workspace id for --data-dir")
    ap.add_argument("--no-push", action="store_true", help="local files only")
    ap.add_argument("--no-refresh", action="store_true")
    ap.add_argument("--report", type=Path, help="CSV with every movement decision")
    args = ap.parse_args()

    if args.data_dir:
        files = WorkspaceFiles(accounts_dir=args.data_dir, key=args.key)
    else:
        files = WorkspaceFiles.current()

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

        movements = JsonFileBankMovementProvider(files.movements).list_movements()
        WorkspaceMLTrainer().rebuild_training_file(
            movements=movements, classifier=SimilarityBasedClassifier()
        )

    runner = CategoryMigrationRunner(
        files,
        pusher=None if args.no_push else FirebaseMigrationPusher(),
        refresh=None if args.no_refresh else refresh,
        retrain=None if args.data_dir else retrain,
        progress=_progress,
    )
    t0 = time.perf_counter()
    if args.apply:
        report = runner.apply()
    elif args.rollback:
        report = runner.rollback()
    else:
        report = runner.dry_run()
    elapsed = time.perf_counter() - t0

    plan = report.plan
    out = {
        "mode": report.mode,
        "changed_movements": report.changed_movements,
        "changed_plans": report.changed_plans,
        "changed_mortgages": report.changed_mortgages,
        "files_written": report.files_written,
        "backup_dir": report.backup_dir,
        "pushed": vars(report.pushed) if report.pushed else None,
        "notification_refreshes": report.refreshed,
        "classifier_rebuilds": report.retrained,
        "skipped_user_edits": report.skipped_user_edits,
        "timings_sec": {k: round(v, 4) for k, v in report.timings.items()},
        "total_sec": round(elapsed, 4),
    }
    if plan is not None:
        out["decision_counts"] = plan.counts()
        out["review_needed"] = sum(1 for d in plan.decisions if d.review)
        out["retained_legacy_names"] = plan.retained_legacy
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if args.report and plan is not None:
        _write_report(args.report, files, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
