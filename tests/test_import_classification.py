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
