import json

from finance.models.accounts import MoneySnapshot
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.date_normalization import migrate_dates_to_iso


def test_models_normalize_date_to_iso_on_construction():
    # Every write path funnels through these two frozen models.
    assert MoneySnapshot(date="01/11/2025", amount=1.0).date == "2025-11-01"
    m = BankMovement(
        amount=-18.0,
        date="16-07-2026",
        account_name="ויזה",
        category="",
        type=MovementType.ONE_TIME,
    )
    assert m.date == "2026-07-16"


def _write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def test_migration_normalizes_all_shapes_and_is_idempotent(tmp_path):
    accounts = tmp_path
    _write(
        accounts / "bank_accounts.json",
        [{"name": "A", "history": [
            {"date": "01/11/2025", "amount": 10},
            {"date": "16-07-2026", "amount": 20},
            {"date": "03.09.24", "amount": 30},
            {"date": "2026-01-05", "amount": 40},  # already ISO
        ]}],
    )
    _write(
        accounts / "bank_movements.json",
        [{"date": "29/07/2026", "amount": -5, "account_name": "x"}],
    )

    changed = migrate_dates_to_iso(accounts)
    assert changed == 2

    hist = json.loads((accounts / "bank_accounts.json").read_text("utf-8"))[0]["history"]
    assert [h["date"] for h in hist] == [
        "2025-11-01", "2026-07-16", "2024-09-03", "2026-01-05",
    ]

    # Marker written -> a second run is a no-op.
    assert migrate_dates_to_iso(accounts) == 0


def test_migration_leaves_timestamps_untouched(tmp_path):
    # A "date" carrying a time component is not a plain day — must not be truncated.
    _write(
        tmp_path / "x.json",
        [{"date": "2026-07-16T10:30:00"}, {"date": "13/08/2026"}],
    )
    migrate_dates_to_iso(tmp_path)
    rows = json.loads((tmp_path / "x.json").read_text("utf-8"))
    assert rows[0]["date"] == "2026-07-16T10:30:00"  # untouched
    assert rows[1]["date"] == "2026-08-13"  # normalized


def test_migration_survives_a_bad_json_file(tmp_path):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    _write(tmp_path / "ok.json", [{"date": "01/02/2026"}])
    # Bad file skipped, good file still migrated, no exception.
    migrate_dates_to_iso(tmp_path)
    assert json.loads((tmp_path / "ok.json").read_text("utf-8"))[0]["date"] == "2026-02-01"
