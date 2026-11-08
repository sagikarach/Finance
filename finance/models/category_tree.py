"""Expense-category hierarchy (parent categories and subcategories).

The smallest extension that stays compatible with the existing data contract:

* Movements (local JSON, Firestore, the mobile app) keep referencing their
  category by **name** in ``category`` — unchanged shape.
* The hierarchy itself is a list of nodes with **stable ids**; parent/child
  relationships use ids, never names. It is stored next to the flat lists in the
  categories file / ``meta/categories`` document as ``outcome_tree``.
* Names are unique across the tree, so a movement's name resolves to exactly
  one node. A name that is not in the tree (a custom category added later, or a
  legacy name from an older client) is treated as its own top-level group.
* ``legacy_aliases`` records which pre-hierarchy names were retired and what
  they became, so configured references (an asset's expense category) and the
  category-list sync can resolve or drop them.

Pure module (no Qt, no network). :func:`active_tree` reads the current
workspace's categories file with an mtime cache.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

SCHEMA_VERSION = 2

UNCLASSIFIED_ID = "unclassified"
UNCLASSIFIED_NAME = "טרם סווג"
# Pre-hierarchy fallback label used by reports for an empty category.
LEGACY_DEFAULT_NAME = "שונות"


@dataclass(frozen=True)
class CategoryNode:
    id: str
    name: str
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "parent_id": self.parent_id or ""}


# (parent id, parent name, ((child id, child name), ...))
DEFAULT_OUTCOME_STRUCTURE: Tuple[Tuple[str, str, Tuple[Tuple[str, str], ...]], ...] = (
    ("food", "מזון", (
        ("food.grocery", "סופר ומכולת"),
        ("food.restaurants", "אוכל בחוץ"),  # restaurants, cafés, deliveries
    )),
    ("housing", "דיור וחשבונות", (
        ("housing.rent", "שכירות"),
        ("housing.mortgage", "משכנתא"),
        ("housing.municipal_tax", "ארנונה"),
        ("housing.electricity", "חשמל"),
        ("housing.water_gas", "מים וגז"),
        ("housing.building_committee", "ועד בית"),
        ("housing.maintenance", "תחזוקה ותיקונים"),
    )),
    ("home", "ריהוט וציוד לבית", (
        ("home.furniture", "רהיטים"),
        ("home.appliances", "מוצרי חשמל"),
        ("home.housewares", "כלי בית וטקסטיל"),
        ("home.decor", "עיצוב"),
    )),
    ("transport", "רכב ותחבורה", (
        ("transport.fuel", "דלק"),
        ("transport.service", "טיפולים ותיקונים"),
        ("transport.insurance", "ביטוח רכב"),
        ("transport.licensing", "רישוי וטסט"),
        ("transport.parking_tolls", "חניה וכבישי אגרה"),
        ("transport.public_taxi", "תחבורה ציבורית ומוניות"),
        ("transport.rental", "השכרת רכב"),
    )),
    ("health", "בריאות וטיפול", (
        ("health.medicine", "תרופות"),
        ("health.doctors", "רופאים ובדיקות"),
        ("health.dental", "טיפולי שיניים"),
        ("health.ongoing", "טיפולים מתמשכים"),
    )),
    ("kids", "ילדים וחינוך", (
        ("kids.daycare", "גן ומסגרות"),
        ("kids.activities", "חוגים"),
        ("kids.gear", "ציוד ומוצרי ילדים"),  # gear, toys and baby products
    )),
    ("apparel", "ביגוד וטיפוח", (
        ("apparel.clothing", "בגדים ונעליים"),
        ("apparel.grooming", "תספורות וטיפוח"),
        ("apparel.jewelry", "תכשיטים"),
    )),
    ("leisure", "פנאי ונופש", (
        ("leisure.outings", "אטרקציות ובילויים"),
        ("leisure.hobbies", "תחביבים"),
        ("leisure.lodging", "לינה וחופשות"),
    )),
    ("digital", "תקשורת ושירותים דיגיטליים", (
        ("digital.telecom", "אינטרנט וסלולר"),
        ("digital.subscriptions", "מנויים ותוכנות"),
    )),
    ("gifts", "מתנות ותרומות", (
        ("gifts.gifts", "מתנות"),
        ("gifts.donations", "תרומות"),
    )),
    ("fees", "עמלות וביטוחים נוספים", (
        ("fees.bank", "עמלות בנק וכרטיס"),
        ("fees.insurance", "ביטוחים נוספים"),
    )),
    ("studies", "לימודים", ()),
    (UNCLASSIFIED_ID, UNCLASSIFIED_NAME, ()),
)

# Names retired by later structure edits → the node that absorbed them.
# Kept as legacy aliases so references resolve and syncs don't resurrect them.
RETIRED_DEFAULT_NAMES = {
    "מסעדות ומשלוחים": "אוכל בחוץ",
    "בתי קפה": "אוכל בחוץ",
    "ציוד וצעצועים": "ציוד ומוצרי ילדים",
    "מוצרי תינוקות": "ציוד ומוצרי ילדים",
}


def default_outcome_nodes() -> List[CategoryNode]:
    out: List[CategoryNode] = []
    for pid, pname, children in DEFAULT_OUTCOME_STRUCTURE:
        out.append(CategoryNode(pid, pname, None))
        out.extend(CategoryNode(cid, cname, pid) for cid, cname in children)
    return out


def custom_node_id(name: str) -> str:
    """Deterministic id for a retained custom category (idempotent migration)."""
    digest = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:10]
    return f"custom.{digest}"


class CategoryTree:
    """Immutable view over the nodes; lookups are O(1)."""

    def __init__(
        self,
        nodes: Iterable[CategoryNode],
        legacy_aliases: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.nodes: Tuple[CategoryNode, ...] = tuple(nodes)
        self.legacy_aliases: Dict[str, str] = dict(legacy_aliases or {})
        self._by_id: Dict[str, CategoryNode] = {}
        self._by_name: Dict[str, CategoryNode] = {}
        self._children: Dict[str, List[CategoryNode]] = {}
        for n in self.nodes:
            if n.id in self._by_id:
                raise ValueError(f"duplicate category id: {n.id}")
            if n.name in self._by_name:
                raise ValueError("duplicate category name in tree")
            self._by_id[n.id] = n
            self._by_name[n.name] = n
        for n in self.nodes:
            if n.parent_id:
                if n.parent_id not in self._by_id:
                    raise ValueError(f"unknown parent id: {n.parent_id}")
                if self._by_id[n.parent_id].parent_id:
                    raise ValueError("only two levels are supported")
                self._children.setdefault(n.parent_id, []).append(n)

    # ── lookups ──
    def __bool__(self) -> bool:
        return bool(self.nodes)

    def by_name(self, name: str) -> Optional[CategoryNode]:
        return self._by_name.get(str(name or "").strip())

    def by_id(self, node_id: str) -> Optional[CategoryNode]:
        return self._by_id.get(node_id)

    def parent_of(self, name: str) -> Optional[CategoryNode]:
        n = self.by_name(name)
        if n is None or not n.parent_id:
            return None
        return self._by_id.get(n.parent_id)

    def children_of(self, name: str) -> List[CategoryNode]:
        n = self.by_name(name)
        return list(self._children.get(n.id, [])) if n is not None else []

    def is_parent(self, name: str) -> bool:
        return bool(self.children_of(name))

    def top_level_name(self, name: str) -> str:
        """The report group of a movement category: its parent's name for a
        subcategory, the name itself for a parent / custom / unknown name."""
        name = str(name or "").strip()
        parent = self.parent_of(name)
        return parent.name if parent is not None else name

    def descendant_names(self, name: str) -> List[str]:
        """``name`` plus all its subcategory names (exactly once each)."""
        name = str(name or "").strip()
        return [name] + [c.name for c in self.children_of(name)]

    def resolve_reference(self, name: str) -> str:
        """A configured category reference: a retired legacy name resolves to
        its replacement; anything else is returned unchanged."""
        name = str(name or "").strip()
        if self.by_name(name) is None and name in self.legacy_aliases:
            return self.legacy_aliases[name]
        return name

    def assignable_names(self) -> List[str]:
        """Flat list in tree order (each parent followed by its children)."""
        out: List[str] = []
        for n in self.nodes:
            if not n.parent_id:
                out.append(n.name)
                out.extend(c.name for c in self._children.get(n.id, []))
        return out

    def is_unclassified(self, name: str) -> bool:
        n = self.by_name(name)
        return n is not None and n.id == UNCLASSIFIED_ID

    # ── serialization ──
    def nodes_to_list(self) -> List[Dict[str, Any]]:
        return [n.to_dict() for n in self.nodes]

    @staticmethod
    def nodes_from_list(raw: Any) -> List[CategoryNode]:
        out: List[CategoryNode] = []
        if not isinstance(raw, list):
            return out
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            nid = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            pid = str(item.get("parent_id") or "").strip() or None
            if nid and name:
                out.append(CategoryNode(nid, name, pid))
        return out

    @classmethod
    def from_storage(cls, data: Mapping[str, Any]) -> "CategoryTree":
        nodes = cls.nodes_from_list(data.get("outcome_tree"))
        aliases_raw = data.get("legacy_aliases")
        aliases: Dict[str, str] = {}
        if isinstance(aliases_raw, Mapping):
            aliases = {
                str(k).strip(): str(v).strip()
                for k, v in aliases_raw.items()
                if str(k).strip() and str(v).strip()
            }
        try:
            return cls(nodes, aliases)
        except ValueError:
            return cls([], aliases)


EMPTY_TREE = CategoryTree([])


def merge_tree_nodes(
    local: Sequence[CategoryNode], remote: Sequence[CategoryNode]
) -> List[CategoryNode]:
    """Union by id; the local definition wins on conflict. Remote nodes whose
    name collides with a different local node are skipped (names stay unique)."""
    out = list(local)
    ids = {n.id for n in out}
    names = {n.name for n in out}
    for n in remote:
        if n.id in ids or n.name in names:
            continue
        if n.parent_id and n.parent_id not in ids:
            continue
        out.append(n)
        ids.add(n.id)
        names.add(n.name)
    return out


def filter_retired_names(
    names: Iterable[str], tree: CategoryTree
) -> List[str]:
    """Drop retired legacy names (unless they are tree nodes again) so a union
    merge with an older client does not resurrect them."""
    out: List[str] = []
    for name in names:
        if name in tree.legacy_aliases and tree.by_name(name) is None:
            continue
        if name not in out:
            out.append(name)
    return out


def report_group(name: str, tree: Optional[CategoryTree] = None) -> str:
    """Report bucket for a movement category (descendants roll up to their
    parent exactly once; parent-only expenses land in the same bucket)."""
    t = active_tree() if tree is None else tree
    name = str(name or "").strip()
    if not name:
        return UNCLASSIFIED_NAME if t.by_id(UNCLASSIFIED_ID) else LEGACY_DEFAULT_NAME
    return t.top_level_name(name)


# ── active tree (current workspace), cached by file mtime ──

_CACHE: Dict[str, Tuple[int, CategoryTree]] = {}
_OVERRIDE: List[CategoryTree] = []


def set_active_tree_override(tree: Optional[CategoryTree]) -> None:
    """Tests / tooling: force the tree :func:`active_tree` returns."""
    _OVERRIDE.clear()
    if tree is not None:
        _OVERRIDE.append(tree)


def load_tree_from_path(path: Path) -> CategoryTree:
    import json

    try:
        st = path.stat()
    except OSError:
        return EMPTY_TREE
    key = str(path)
    cached = _CACHE.get(key)
    if cached is not None and cached[0] == st.st_mtime_ns:
        return cached[1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return EMPTY_TREE
    tree = CategoryTree.from_storage(data) if isinstance(data, dict) else EMPTY_TREE
    _CACHE[key] = (st.st_mtime_ns, tree)
    return tree


def active_tree() -> CategoryTree:
    if _OVERRIDE:
        return _OVERRIDE[0]
    try:
        from ..data.bank_movement_provider import JsonFileBankMovementProvider

        path = JsonFileBankMovementProvider().categories_path
    except Exception:  # noqa: BLE001 - no session / no file → flat categories
        return EMPTY_TREE
    return load_tree_from_path(path)
