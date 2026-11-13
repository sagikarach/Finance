"""Which movements are a car's ownership costs (pure, no Qt, no I/O).

A car asset counts the expenses in the categories *selected for that car* —
exactly those names, never "every descendant" of a broad parent. General
transportation (public transport, taxis, rental cars) is not an ownership cost
and is never included unless the user selects it explicitly.

Precedence, each movement counted at most once:

1. a movement the user excluded from the car (``Mortgage.excluded_movement_ids``)
   is not counted;
2. a movement matched by one of the car's yearly cost items (ביטוח, טסט…) is
   that item's — it is counted in the yearly figure, not in the monthly spend;
3. otherwise an expense whose category is one of the selected categories is
   counted in the monthly spend.

Older car settings stored one category name (``expense_category``, default
"רכב"). :func:`car_category_selection` converts it on read, without writing
anything: a retired name resolves to its replacement; the broad "רכב ותחבורה"
parent becomes its car-ownership subcategories (fuel, service, insurance,
licensing, parking), and expenses filed on the parent itself are kept *for
review* (shown, not counted) because they mix car and non-car spending. Any
other broad parent is kept for review only. A custom or unknown name is kept
as it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .bank_movement import counts_as_transfer
from .category_tree import CategoryTree
from .mortgage_math import cost_matched_movements
from ..utils.safe import PARSE_ERRORS

LEGACY_DEFAULT_CAR_CATEGORY = "רכב"
TRANSPORT_PARENT_ID = "transport"
# Stable hierarchy ids (names may be renamed by the user; ids do not change).
CAR_OWNERSHIP_IDS: Tuple[str, ...] = (
    "transport.fuel",
    "transport.service",
    "transport.insurance",
    "transport.licensing",
    "transport.parking_tolls",
)
NOT_CAR_OWNERSHIP_IDS: Tuple[str, ...] = ("transport.public_taxi", "transport.rental")


@dataclass(frozen=True)
class CarCategorySelection:
    """The categories counted for a car, and broad legacy references kept for
    the user to review (shown with their movements, never counted)."""

    categories: Tuple[str, ...] = ()
    review: Tuple[str, ...] = ()
    # True when derived from an older single-category setting (not saved yet).
    migrated: bool = False

    @property
    def needs_review(self) -> bool:
        return bool(self.review)


def _clean(names: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for n in names or []:
        s = str(n or "").strip()
        if s and s not in out:
            out.append(s)
    return out


def default_car_categories(tree: CategoryTree) -> List[str]:
    """The car-ownership subcategories present in ``tree`` (by stable id)."""
    out: List[str] = []
    for nid in CAR_OWNERSHIP_IDS:
        node = tree.by_id(nid)
        if node is not None:
            out.append(node.name)
    return out


def _from_reference(raw: str, tree: CategoryTree) -> Tuple[List[str], List[str]]:
    """``(counted, review)`` for one stored category reference."""
    name = tree.resolve_reference(raw) if tree else raw
    node = tree.by_name(name) if tree else None
    if node is None:
        return [name], []  # custom / unknown / no hierarchy: kept exactly
    if not tree.is_parent(node.name):
        return [node.name], []
    if node.id == TRANSPORT_PARENT_ID:
        return default_car_categories(tree), [node.name]
    return [], [node.name]


def car_category_selection(mortgage: Any, tree: CategoryTree) -> CarCategorySelection:
    """The car's category selection. A saved list (``expense_categories``,
    even an empty one) is used as is; when it was never chosen (``None``) the
    older single ``expense_category`` is converted (see the module
    docstring). Never writes anything."""
    raw = getattr(mortgage, "expense_categories", None)
    if raw is not None:  # chosen (an empty list = deliberately none)
        return CarCategorySelection(categories=tuple(_clean(raw)))
    raw = str(getattr(mortgage, "expense_category", "") or "").strip()
    counted, review = _from_reference(raw or LEGACY_DEFAULT_CAR_CATEGORY, tree)
    return CarCategorySelection(
        categories=tuple(_clean(counted)), review=tuple(_clean(review)), migrated=True
    )


@dataclass
class CarCostBreakdown:
    """The car's movements, each in exactly one bucket."""

    selection: CarCategorySelection
    monthly: List[Any] = field(default_factory=list)  # counted in the monthly spend
    cost_items: List[Any] = field(default_factory=list)  # counted by a yearly item
    excluded: List[Any] = field(default_factory=list)  # in a selected category, excluded
    review: List[Any] = field(default_factory=list)  # broad legacy category, not counted

    def monthly_by_category(self) -> List[Tuple[str, float, int]]:
        """``(category, total, count)`` of the monthly spend, largest first."""
        totals: Dict[str, float] = {}
        counts: Dict[str, int] = {}
        for m in self.monthly:
            c = str(getattr(m, "category", "") or "").strip()
            totals[c] = totals.get(c, 0.0) + abs(_amount(m))
            counts[c] = counts.get(c, 0) + 1
        return sorted(
            ((c, totals[c], counts[c]) for c in totals), key=lambda x: -x[1]
        )


def _amount(m: Any) -> float:
    try:
        return float(getattr(m, "amount", 0.0) or 0.0)
    except PARSE_ERRORS:
        return 0.0


def _is_expense(m: Any) -> bool:
    try:
        return _amount(m) < 0 and not counts_as_transfer(m)
    except PARSE_ERRORS:
        return False


def car_cost_breakdown(
    mortgage: Any,
    movements: Sequence[Any],
    tree: CategoryTree,
    selection: Optional[CarCategorySelection] = None,
) -> CarCostBreakdown:
    sel = selection or car_category_selection(mortgage, tree)
    names = set(sel.categories)
    review = set(sel.review) - names
    user_excluded = {
        str(x) for x in (getattr(mortgage, "excluded_movement_ids", None) or []) if str(x)
    }
    item_ids: set = set()
    for cost in getattr(mortgage, "yearly_costs", None) or []:
        for m in cost_matched_movements(cost, list(movements)):
            item_ids.add(str(getattr(m, "id", "") or id(m)))

    out = CarCostBreakdown(selection=sel)
    seen: set = set()
    for m in movements:
        mid = str(getattr(m, "id", "") or id(m))
        if mid in seen or not _is_expense(m):
            continue
        cat = str(getattr(m, "category", "") or "").strip()
        if mid in item_ids:
            seen.add(mid)
            out.cost_items.append(m)
            continue
        if cat in names:
            seen.add(mid)
            (out.excluded if mid in user_excluded else out.monthly).append(m)
        elif cat in review:
            seen.add(mid)
            out.review.append(m)
    return out


def selection_label(sel: CarCategorySelection, *, limit: int = 3) -> str:
    """Short Hebrew description of the selection for headers."""
    if not sel.categories:
        return "לא נבחרו קטגוריות"
    names = list(sel.categories)
    if len(names) <= limit:
        return ", ".join(names)
    return f"{', '.join(names[:limit])} ועוד {len(names) - limit}"
