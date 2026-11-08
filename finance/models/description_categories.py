"""Unique expense descriptions and bulk recategorization (pure, no Qt).

Groups expense movements by their normalized description (the same identity
the unusual-expense detector uses for payees), so the user can review each
distinct description once and assign one category to all its movements.
Only the ``category`` field is ever changed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .bank_movement import BankMovement, counts_as_transfer
from .category_tree import UNCLASSIFIED_NAME, CategoryTree
from .movement_matching import normalize_text


def description_key(description: Any) -> str:
    return normalize_text(str(description or "")).casefold()


@dataclass
class DescriptionGroup:
    key: str
    description: str  # most common raw spelling, for display
    count: int = 0
    total: float = 0.0
    last_date: str = ""
    categories: Counter = field(default_factory=Counter)
    accounts: Counter = field(default_factory=Counter)
    movement_ids: List[str] = field(default_factory=list)

    @property
    def main_category(self) -> str:
        return self.categories.most_common(1)[0][0] if self.categories else ""

    @property
    def is_mixed(self) -> bool:
        return len(self.categories) > 1

    def is_unclassified(self) -> bool:
        return any(not c or c == UNCLASSIFIED_NAME for c in self.categories)

    def is_parent_only(self, tree: CategoryTree) -> bool:
        return any(tree.is_parent(c) for c in self.categories)


def _is_expense(m: BankMovement) -> bool:
    try:
        return float(m.amount) < 0 and not counts_as_transfer(m)
    except (TypeError, ValueError):
        return False


def group_expense_descriptions(movements: Iterable[BankMovement]) -> List[DescriptionGroup]:
    """One group per normalized description (expenses only, transfers
    excluded), largest total first. Movements without a description are
    grouped under an empty key."""
    groups: Dict[str, DescriptionGroup] = {}
    spellings: Dict[str, Counter] = {}
    for m in movements:
        if not _is_expense(m):
            continue
        key = description_key(m.description)
        g = groups.get(key)
        if g is None:
            g = groups[key] = DescriptionGroup(key=key, description="")
            spellings[key] = Counter()
        g.count += 1
        g.total += abs(float(m.amount))
        g.last_date = max(g.last_date, str(m.date or ""))
        g.categories[str(m.category or "").strip()] += 1
        g.accounts[str(m.account_name or "")] += 1
        g.movement_ids.append(str(m.id))
        spellings[key][str(m.description or "").strip()] += 1
    for key, g in groups.items():
        g.description = spellings[key].most_common(1)[0][0]
    return sorted(groups.values(), key=lambda g: (-g.total, g.key))


def apply_description_categories(
    movements: Sequence[BankMovement],
    assignments: Mapping[str, str],
) -> Tuple[List[BankMovement], List[BankMovement]]:
    """Set ``category`` on every expense whose description key is in
    ``assignments``. Returns ``(all movements, changed movements)``; nothing
    else on a movement is touched, and income/transfers are never changed."""
    out: List[BankMovement] = []
    changed: List[BankMovement] = []
    for m in movements:
        new_cat: Optional[str] = None
        if _is_expense(m):
            new_cat = assignments.get(description_key(m.description))
        if new_cat and new_cat != m.category:
            m2 = replace(m, category=new_cat)
            out.append(m2)
            changed.append(m2)
        else:
            out.append(m)
    return out, changed


def category_choices(tree: CategoryTree, flat_names: Iterable[str]) -> List[Tuple[str, str]]:
    """``(label, category name)`` for a picker: tree order with indented
    subcategories, then any other (custom) names from the flat list."""
    out: List[Tuple[str, str]] = []
    seen = set()
    if tree:
        for n in tree.nodes:
            if n.parent_id:
                continue
            out.append((n.name, n.name))
            seen.add(n.name)
            for c in tree.children_of(n.name):
                out.append((f"    {c.name}", c.name))
                seen.add(c.name)
    for name in flat_names:
        name = str(name or "").strip()
        if name and name not in seen and name not in tree.legacy_aliases and name != "העברה":
            out.append((name, name))
            seen.add(name)
    return out
