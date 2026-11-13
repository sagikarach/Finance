"""Creating a category from the UI (pure, no Qt, no I/O).

A new expense category is either top-level (stored in the flat list, as
before) or a subcategory of an existing top-level category (a hierarchy node
with a stable id, so every device places it under the same parent).
"""

from __future__ import annotations

from typing import Iterable, List

from .category_tree import CategoryNode, CategoryTree, custom_node_id


def validate_new_category_name(
    name: str, existing: Iterable[str], tree: CategoryTree, *, is_income: bool = False
) -> str:
    """A Hebrew error message, or "" when ``name`` can be added. Names are
    unique per list (and across the expense hierarchy); a retired pre-hierarchy
    name is refused because sync would drop it again."""
    name = str(name or "").strip()
    if not name:
        return "יש להזין שם קטגוריה"
    if "/" in name:
        return "שם קטגוריה לא יכול להכיל /"
    taken = {str(x).strip() for x in existing}
    if name in taken:
        return "הקטגוריה כבר קיימת"
    if not is_income and tree:
        if tree.by_name(name) is not None:
            return "הקטגוריה כבר קיימת"
        if name in tree.legacy_aliases:
            return f"השם הוחלף בעבר ב״{tree.legacy_aliases[name]}״ — בחרו בה או בשם אחר"
    return ""


def top_level_choices(tree: CategoryTree) -> List[str]:
    """Top-level categories a new subcategory can be placed under."""
    return [n.name for n in tree.nodes if not n.parent_id and not tree.is_unclassified(n.name)]


def add_child_category(tree: CategoryTree, name: str, parent_name: str) -> CategoryTree:
    """``tree`` with ``name`` added under ``parent_name`` (after its last
    subcategory). Raises ``ValueError`` for an unknown or non-top-level parent
    or a name already in the tree."""
    name = str(name or "").strip()
    parent = tree.by_name(parent_name)
    if parent is None or parent.parent_id:
        raise ValueError("parent must be an existing top-level category")
    if tree.by_name(name) is not None:
        raise ValueError("category already exists")
    node = CategoryNode(custom_node_id(name), name, parent.id)
    nodes = list(tree.nodes)
    insert_at = max(
        i for i, n in enumerate(nodes) if n.id == parent.id or n.parent_id == parent.id
    ) + 1
    nodes.insert(insert_at, node)
    return CategoryTree(nodes, tree.legacy_aliases)
