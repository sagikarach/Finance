"""Import-time classification: the user's history outranks stale seed labels,
and weak suggestions go to review instead of being added automatically."""

from __future__ import annotations

from pathlib import Path

from finance.models import category_tree as ct
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.bank_movement_service import BankMovementService
from finance.models.category_tree import CategoryTree, default_outcome_nodes
from finance.models.movement_classifier import SimilarityBasedClassifier
from finance.models.workspace_ml_trainer import WorkspaceMLTrainer


def _mv(desc: str, amount: float, category: str, i: int) -> BankMovement:
    return BankMovement(amount=-amount, date=f"2026-0{1 + i % 8}-10", account_name="בנק",
                        category=category, type=MovementType.ONE_TIME, description=desc,
                        id=f"m{i}")


def _classifier(tmp_path: Path) -> SimilarityBasedClassifier:
    return SimilarityBasedClassifier(training_data_path=tmp_path / "expenses.json")


def test_history_outranks_seed_for_the_same_description(tmp_path, monkeypatch):
    ct.set_active_tree_override(CategoryTree(default_outcome_nodes(), {"קניות": "טרם סווג"}))
    seed = [{"description": "סופרפארם לוד", "amount": 50, "category": "בריאות",
             "expenseType": "חד פעמי"},
            {"description": "מוסך הצפון", "amount": 400, "category": "רכב",
             "expenseType": "חד פעמי"}]
    monkeypatch.setattr(WorkspaceMLTrainer, "_load_seed_cached_or_default", lambda self: seed)
    clf = _classifier(tmp_path)
    # a brand-new budget: the seed bootstraps, after the user's own rows
    few = [_mv("סופרפארם לוד", 50, "תרופות", i) for i in range(3)]
    WorkspaceMLTrainer().rebuild_training_file(movements=few, classifier=clf)
    rows = clf._training_data  # noqa: SLF001
    assert [r["source"] for r in rows] == ["history"] * 3 + ["seed", "seed"]
    assert rows[-1]["category"] == "טיפולים ותיקונים"  # relabeled to the hierarchy
    cat, _t, conf = clf.classify_outcome(_mv("סופרפארם לוד", 50, "", 99))
    assert cat == "תרופות" and conf >= BankMovementService.min_confidence
    # once the budget has real history, the seed is not used at all
    many = few + [_mv(f"חנות {i}", 20 + i, "סופר ומכולת", 10 + i) for i in range(60)]
    WorkspaceMLTrainer().rebuild_training_file(movements=many, classifier=clf)
    assert {r["source"] for r in clf._training_data} == {"history"}  # noqa: SLF001


def test_no_match_fallback_is_always_reviewed(tmp_path):
    ct.set_active_tree_override(CategoryTree(default_outcome_nodes()))
    clf = _classifier(tmp_path)
    clf.set_training_data([{"description": "שופרסל", "amount": 80, "category": "סופר ומכולת",
                            "expenseType": "חד פעמי"}])
    cat, _t, conf = clf.classify_outcome(_mv("חנות חדשה לגמרי", 80, "", 1))
    assert cat == "טרם סווג"
    assert conf < BankMovementService.min_confidence  # → review dialog, not auto-added
    assert SimilarityBasedClassifier.DEFAULT_CONFIDENCE < BankMovementService.min_confidence


def _service(tmp_path: Path, rows) -> BankMovementService:
    clf = _classifier(tmp_path)
    clf.set_training_data(rows)
    return BankMovementService(movement_provider=None, history_provider=None,  # type: ignore[arg-type]
                               classifier=clf)


def _row(desc: str, amount: float, category: str) -> dict:
    return {"description": desc, "amount": amount, "category": category,
            "expenseType": "חד פעמי"}


ALLOWED = ["מזון", "סופר ומכולת", "אוכל בחוץ", "תרופות", "טרם סווג"]


def test_manual_entry_suggests_category_from_past_expenses(tmp_path):
    ct.set_active_tree_override(CategoryTree(default_outcome_nodes()))
    svc = _service(tmp_path, [_row("סופרפארם לוד", 45, "תרופות")] * 3
                   + [_row("אושר עד לוד", 300, "סופר ומכולת")] * 3)
    assert svc.suggest_category("סופרפארם לוד", 50, ALLOWED) == "תרופות"
    assert svc.suggest_category("  אושר עד לוד ", 280, ALLOWED) == "סופר ומכולת"


def test_manual_entry_no_suggestion_when_unsure_or_unclassified(tmp_path):
    ct.set_active_tree_override(CategoryTree(default_outcome_nodes()))
    svc = _service(tmp_path, [_row("BIT", 100, "טרם סווג")] * 3
                   + [_row("סופרפארם לוד", 45, "תרופות")] * 3)
    assert svc.suggest_category("חנות שלא ראינו מעולם", 50, ALLOWED) is None  # no match
    assert svc.suggest_category("BIT", 100, ALLOWED) is None  # "טרם סווג" is no help
    assert svc.suggest_category("", 50, ALLOWED) is None
    assert svc.suggest_category("סופרפארם לוד", 45, ["מזון"]) is None  # not offered


class _MovementsOnly:
    def __init__(self, items):
        self.items = items

    def list_movements(self):
        return list(self.items)


def test_manual_income_suggests_from_past_income_only(tmp_path):
    def inc(desc, amount, cat, i, **kw):
        return BankMovement(amount=amount, date=f"2026-0{1 + i % 8}-01", account_name="בנק",
                            category=cat, type=MovementType.MONTHLY, description=desc,
                            id=f"i{i}", **kw)

    items = [inc("משכורת שגיא", 12876, "משכורת", i) for i in range(3)]
    items += [inc("החזר ביטוח", 300, "החזר", 10 + i) for i in range(2)]
    items += [_mv("משכורת שגיא", 50, "טרם סווג", 20)]  # an expense: ignored
    items += [inc("העברה", 900, "העברה", 30, is_transfer=True)]  # transfer: ignored
    svc = BankMovementService(movement_provider=_MovementsOnly(items),  # type: ignore[arg-type]
                              history_provider=None)  # type: ignore[arg-type]
    suggest = svc.income_suggester(["אחר", "החזר", "משכורת", "מתנה"])
    assert suggest("משכורת שגיא", 12876) == ("משכורת", MovementType.MONTHLY)
    assert suggest("החזר ביטוח", 300)[0] == "החזר"
    assert suggest("משהו אחר לגמרי", 100) is None
    assert suggest("", 100) is None
