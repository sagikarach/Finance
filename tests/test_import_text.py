"""The service-level text importer (shared by file + Drive imports)."""

from finance.models.accounts import BankAccount
from finance.models.bank_movement_service import BankMovementService


class _FakeProvider:
    def list_movements(self):
        return []


def _svc():
    # No classifier -> expenses are applied directly (no review queue).
    return BankMovementService(movement_provider=_FakeProvider(), history_provider=None)


def _bank():
    return [BankAccount(name="ויזה", total_amount=0.0, is_liquid=True, active=True)]


def test_import_outcome_csv_text_parses_and_imports():
    svc = _svc()
    csv_text = (
        "תאריך עסקה,שם בית העסק,סכום חיוב\n"
        "16-07-2026,רמי לוי,50\n"
        "29/07/2026,סופרפארם,29.24\n"
    )
    svc.import_outcome_csv_text(_bank(), "ויזה", csv_text)

    imported = svc.pop_imported_for_last_csv()
    by_desc = {m.description: m for m in imported}
    assert set(by_desc) == {"רמי לוי", "סופרפארם"}
    # Dates are normalized to ISO (via BankMovement), amounts are expenses (negative).
    assert by_desc["רמי לוי"].date == "2026-07-16"
    assert by_desc["רמי לוי"].amount == -50.0
    assert by_desc["סופרפארם"].date == "2026-07-29"


def test_import_outcome_csv_text_empty_accounts_is_noop():
    svc = _svc()
    assert svc.import_outcome_csv_text([], "ויזה", "whatever") == []
