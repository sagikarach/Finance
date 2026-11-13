"""Importing an expense file never silently drops a row.

Regression: only the 3 lowest-confidence rows awaiting review were shown; the
rest of the review queue — and every row when the review was skipped — was
discarded without a word.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any, List

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.category_tree import UNCLASSIFIED_NAME  # noqa: E402
from finance.models.classified_expense import ClassifiedExpense  # noqa: E402


def _pending(n: int) -> List[ClassifiedExpense]:
    return [
        ClassifiedExpense(
            movement=BankMovement(
                amount=-(10.0 + i),
                date="2026-10-01",
                account_name="בנק",
                category="",
                type=MovementType.ONE_TIME,
                description=f"row {i}",
                id=f"m{i}",
            ),
            suggested_category="דלק" if i % 2 else None,
            suggested_type=MovementType.MONTHLY if i % 3 == 0 else None,
            confidence=0.1 + i / 100,
        )
        for i in range(n)
    ]


class _Service:
    def __init__(self, pending: List[ClassifiedExpense]) -> None:
        self._pending = list(pending)
        self._imported_for_last_csv: List[BankMovement] = []
        self.applied: List[BankMovement] = []
        self.classifier = None

    def pop_pending_reviews(self) -> List[ClassifiedExpense]:
        out, self._pending = self._pending, []
        return out

    def apply_movement(self, accounts: Any, movement: BankMovement, **_: Any) -> Any:
        self.applied.append(movement)
        return accounts

    def pop_imported_for_last_csv(self) -> List[BankMovement]:
        out, self._imported_for_last_csv = self._imported_for_last_csv, []
        return out

    def recalculate_account_balances(self, accounts: Any) -> Any:
        return accounts


def _run(monkeypatch: pytest.MonkeyPatch, pending: List[ClassifiedExpense], dialog_cls: Any):
    from finance.pages.bank_account_page import BankAccountPage
    import finance.ui.batch_outcome_review_dialog as mod

    monkeypatch.setattr(mod, "BatchOutcomeReviewDialog", dialog_cls)
    service = _Service(pending)
    history: List[Any] = []
    stub = SimpleNamespace(
        _bank_movement_service=service,
        _bank_movement_provider=SimpleNamespace(list_categories=lambda: ["דלק"]),
        _accounts=[],
        _history_provider=SimpleNamespace(add_action=history.append, list_history=lambda: []),
        _find_history_table=lambda: None,
        _save_and_refresh_accounts=lambda: None,
    )
    BankAccountPage._apply_imported_expenses(stub, SimpleNamespace(name="בנק"), "f.csv")  # type: ignore[arg-type]
    return service, history


def test_every_pending_row_is_offered_for_review(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: List[int] = []

    class Accepting:
        def __init__(self, expenses: List[ClassifiedExpense], *_: Any, **__: Any) -> None:
            self._e = expenses
            seen.append(len(expenses))

        def exec(self) -> bool:
            return True

        def get_results(self) -> List[BankMovement]:
            return [e.to_bank_movement_with_user_input("דלק", MovementType.ONE_TIME) for e in self._e]

    service, history = _run(monkeypatch, _pending(18), Accepting)
    assert seen == [18]
    assert len(service.applied) == 18
    assert {m.category for m in service.applied} == {"דלק"}
    assert history[0].action.expenses_count == 18


def test_skipped_review_keeps_rows_as_unclassified(monkeypatch: pytest.MonkeyPatch) -> None:
    class Skipping:
        def __init__(self, *_: Any, **__: Any) -> None:
            pass

        def exec(self) -> bool:
            return False

        def get_results(self) -> List[Any]:
            return []

    pending = _pending(5)
    service, history = _run(monkeypatch, pending, Skipping)
    assert [m.id for m in service.applied] == [p.movement.id for p in pending]
    assert {m.category for m in service.applied} == {UNCLASSIFIED_NAME}
    # the suggested frequency is kept; nothing else about the row changes
    assert service.applied[0].type == MovementType.MONTHLY
    assert service.applied[1].type == MovementType.ONE_TIME
    assert [m.amount for m in service.applied] == [p.movement.amount for p in pending]
    assert history[0].action.expenses_count == 5


def test_partially_failed_review_falls_back_per_row(monkeypatch: pytest.MonkeyPatch) -> None:
    class Partial:
        def __init__(self, expenses: List[ClassifiedExpense], *_: Any, **__: Any) -> None:
            self._e = expenses

        def exec(self) -> bool:
            return True

        def get_results(self) -> List[Any]:
            return [
                e.to_bank_movement_with_user_input("דלק", MovementType.ONE_TIME) if i == 0 else None
                for i, e in enumerate(self._e)
            ]

    service, _ = _run(monkeypatch, _pending(3), Partial)
    assert len(service.applied) == 3
    assert [m.category for m in service.applied] == ["דלק", UNCLASSIFIED_NAME, UNCLASSIFIED_NAME]
