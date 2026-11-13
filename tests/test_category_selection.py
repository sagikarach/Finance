"""Hierarchical category selection everywhere: path labels, parent selection,
custom / unknown values kept, creating a subcategory that survives
persistence and sync, and no change from merely opening or cancelling."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest

from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.models import category_tree as ct
from finance.models.category_create import (
    add_child_category,
    top_level_choices,
    validate_new_category_name,
)
from finance.models.category_tree import UNCLASSIFIED_NAME, CategoryTree, default_outcome_nodes

TREE = CategoryTree(default_outcome_nodes(), {"קניות": UNCLASSIFIED_NAME})
KEY = "W1"


# ── model ────────────────────────────────────────────────────────────────


def test_new_category_name_validation():
    names = TREE.assignable_names() + ["חיות מחמד"]
    assert validate_new_category_name("", names, TREE)
    assert validate_new_category_name("דלק", names, TREE) == "הקטגוריה כבר קיימת"
    assert validate_new_category_name("חיות מחמד", names, TREE)
    assert "טרם סווג" in validate_new_category_name("קניות", names, TREE)  # retired
    assert validate_new_category_name("א/ב", names, TREE)
    assert validate_new_category_name("רכב חשמלי", names, TREE) == ""
    # income list is separate from the expense hierarchy
    assert validate_new_category_name("דלק", ["משכורת"], TREE, is_income=True) == ""


def test_add_child_category_goes_under_its_parent_with_a_stable_id():
    new = add_child_category(TREE, "טעינת רכב חשמלי", "רכב ותחבורה")
    kids = [c.name for c in new.children_of("רכב ותחבורה")]
    assert kids[-1] == "טעינת רכב חשמלי"
    node = new.by_name("טעינת רכב חשמלי")
    assert node.id.startswith("custom.") and new.parent_of(node.name).id == "transport"
    again = add_child_category(TREE, "טעינת רכב חשמלי", "רכב ותחבורה")
    assert again.by_name("טעינת רכב חשמלי").id == node.id  # same on every device
    with pytest.raises(ValueError):
        add_child_category(TREE, "x", "דלק")  # a subcategory cannot be a parent
    assert UNCLASSIFIED_NAME not in top_level_choices(TREE)


def _provider(tmp_path) -> JsonFileBankMovementProvider:
    p = JsonFileBankMovementProvider(tmp_path / f"bank_movements_{KEY}.json")
    p.save_category_tree(TREE, outcome_names=TREE.assignable_names() + ["חיות מחמד"])
    return p


def test_child_category_persists_and_keeps_custom_names(tmp_path):
    p = _provider(tmp_path)
    p.add_expense_category("טעינת רכב חשמלי", "רכב ותחבורה")
    reloaded = JsonFileBankMovementProvider(tmp_path / f"bank_movements_{KEY}.json")
    tree = reloaded.load_category_tree()
    assert tree.parent_of("טעינת רכב חשמלי").name == "רכב ותחבורה"
    outcome = reloaded.list_categories_for_type(False)
    assert outcome.index("טעינת רכב חשמלי") < outcome.index(UNCLASSIFIED_NAME)
    assert "חיות מחמד" in outcome  # custom name kept
    assert tree.legacy_aliases == TREE.legacy_aliases
    p.add_expense_category("ציפורים", "")  # top-level: flat list, tree unchanged
    assert reloaded.load_category_tree().by_name("ציפורים") is None
    assert "ציפורים" in reloaded.list_categories_for_type(False)


class FakeFS:
    def __init__(self, remote: Dict[str, Any]):
        self.remote = remote
        self.patches: List[Dict[str, Any]] = []

    def get_document(self, **_kw):
        return {"fields": True}

    def parse_any_doc(self, _doc):
        return "categories", dict(self.remote)

    def patch_document_fields(self, *, document_path, id_token, fields):
        self.patches.append(fields)


def test_child_category_survives_sync_with_an_older_remote(tmp_path):
    from finance.models.firebase_sync_categories import sync_categories

    p = _provider(tmp_path)
    p.add_expense_category("טעינת רכב חשמלי", "רכב ותחבורה")
    remote = {"income": ["משכורת"], "outcome": TREE.assignable_names(),
              "outcome_tree": TREE.nodes_to_list(), "updated_by": "mobile"}
    fs = FakeFS(remote)
    sync_categories(fs=fs, workspace_id=KEY, uid="u", id_token="t", provider=p, allow_push=True)
    pushed = fs.patches[0]
    node = next(n for n in pushed["outcome_tree"] if n["name"] == "טעינת רכב חשמלי")
    assert node["parent_id"] == "transport"
    # a field-level patch: only the category fields, never unrelated ones
    assert set(pushed) <= {"income", "outcome", "version", "outcome_tree",
                           "legacy_aliases", "schema_version"}
    assert p.load_category_tree().by_name("טעינת רכב חשמלי") is not None


# ── widgets (offscreen) ──────────────────────────────────────────────────

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from finance.qt import QApplication  # noqa: E402
from finance.widgets.category_combo import (  # noqa: E402
    NO_CATEGORY_LABEL,
    CategoryChecklist,
    CategoryComboBox,
    category_label,
    category_value,
    fill_category_combo,
    make_category_combo,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tree():
    ct.set_active_tree_override(TREE)
    return TREE


def test_labels_show_the_full_path(tree):
    assert category_label("סופר ומכולת") == "מזון / סופר ומכולת"
    assert category_label("מזון") == "מזון"
    assert category_label("שם לא מוכר") == "שם לא מוכר"


def test_combo_keeps_custom_unknown_and_empty_values(app, tree):
    names = tree.assignable_names() + ["חיות מחמד"]
    for current in ("חיות מחמד", "בתי קפה ישנים", "קניות", ""):
        combo = make_category_combo(None, names, current)
        assert category_value(combo) == current  # open + save = no change
    combo = make_category_combo(None, names, "")
    assert combo.currentText() == NO_CATEGORY_LABEL
    # a retired name is not offered unless it is the current value
    plain = make_category_combo(None, names + ["קניות"], "דלק")
    assert plain.findData("קניות") < 0
    assert plain.currentText() == "רכב ותחבורה / דלק"


def test_popup_groups_children_and_a_parent_is_selectable(app, tree):
    combo = make_category_combo(None, tree.assignable_names(), "דלק")
    combo.showPopup()
    tw = combo.tree_widget
    assert tw is not None
    tops = [tw.topLevelItem(i).text(0) for i in range(tw.topLevelItemCount())]
    assert "רכב ותחבורה" in tops and "דלק" not in tops  # nested under its parent
    parent = tw.topLevelItem(tops.index("רכב ותחבורה"))
    assert parent.childCount() == len(tree.children_of("רכב ותחבורה"))
    combo._choose(parent)  # clicking the parent's name selects the parent itself
    assert category_value(combo) == "רכב ותחבורה"


def test_income_combo_is_flat(app, tree):
    combo = make_category_combo(None, ["משכורת", "קצבה"], "משכורת", is_income=True)
    assert isinstance(combo, CategoryComboBox) and category_value(combo) == "משכורת"


def test_checklist_parent_does_not_select_children(app, tree):
    cl = CategoryChecklist(None, tree=tree, checked=["דלק", "חניה פרטית"])
    assert set(cl.checked_names()) == {"דלק", "חניה פרטית"}  # custom kept
    cl.set_checked("רכב ותחבורה", True)
    assert set(cl.checked_names()) == {"דלק", "חניה פרטית", "רכב ותחבורה"}


def test_extra_items_and_refill_keep_the_choice(app, tree):
    combo = CategoryComboBox()
    fill_category_combo(combo, tree.assignable_names(), "דלק",
                        extra_items=[("הוסף קטגוריה חדשה…", "__add__")])
    assert combo.itemData(combo.count() - 1) == "__add__"
    fill_category_combo(combo, tree.assignable_names() + ["חדשה"], category_value(combo))
    assert category_value(combo) == "דלק"


def test_new_category_dialog_offers_parents_and_validates(app, tree):
    from finance.ui.bank_movement_dialog import NewCategoryDialog

    dlg = NewCategoryDialog(tree.assignable_names(), tree=tree)
    assert dlg._parent_combo is not None
    dlg._edit.setText("טעינת רכב חשמלי")
    dlg._parent_combo.setCurrentIndex(dlg._parent_combo.findData("רכב ותחבורה"))
    from finance.qt import QPushButton

    add_btn = next(b for b in dlg.findChildren(QPushButton) if b.text() == "הוסף")
    add_btn.click()
    assert dlg.get_name() == "טעינת רכב חשמלי" and dlg.get_parent_name() == "רכב ותחבורה"
    dup = NewCategoryDialog(tree.assignable_names(), tree=tree)
    dup._edit.setText("דלק")
    next(b for b in dup.findChildren(QPushButton) if b.text() == "הוסף").click()
    assert dup.get_name() == ""  # refused: already exists
    income = NewCategoryDialog(["משכורת"], is_income=True)
    assert income._parent_combo is None


def test_cancelled_review_add_returns_to_previous_choice(app, tree, monkeypatch):
    from finance.models.classified_expense import ClassifiedExpense
    from finance.models.bank_movement import BankMovement, MovementType
    from finance.ui import batch_outcome_review_dialog as mod

    movement = BankMovement(amount=-50, date="2026-05-01", account_name="בנק",
                            category="", type=MovementType.ONE_TIME, description="פז")
    exp = ClassifiedExpense(movement=movement, suggested_category="דלק",
                            suggested_type=MovementType.ONE_TIME, confidence=0.4)
    dlg = mod.BatchOutcomeReviewDialog([exp], tree.assignable_names())
    combo = dlg._category_combos[0]
    assert category_value(combo) == "דלק"

    class _Cancel:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr(mod, "NewCategoryDialog", _Cancel)
    sentinel = combo.findData(dlg._add_category_sentinel)
    combo.setCurrentIndex(sentinel)
    dlg._on_category_activated(0, sentinel)
    assert category_value(combo) == "דלק"
