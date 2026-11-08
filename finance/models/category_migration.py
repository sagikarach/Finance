"""Versioned, idempotent migration of the flat expense categories into the
parent/subcategory hierarchy (:mod:`category_tree`).

Two layers:

* :func:`plan_migration` — pure and deterministic. From the raw movement rows,
  installment plans, assets (mortgage records) and the old category lists it
  decides, per movement, the new category and *why* (explicit link, merchant
  rule, the user's old category, or nothing). No movement ids or amounts appear
  in any rule.
* :class:`CategoryMigrationRunner` — file I/O around the plan: backup +
  rollback mapping, a state file (resumable, no-op when already done), atomic
  writes that touch only category fields, a push of the changed records only,
  then exactly one notification refresh and one classifier rebuild.

Decision order for an expense movement (first match wins):

1. transfer / income category / already-new category → unchanged;
2. explicit relationship the user configured:
   asset purchase price or one-time acquisition cost → *asset acquisition*
   (category deliberately left as is — not forced into a living-expense node);
   asset recurring/yearly cost item, mortgage payment, installment plan /
   direct debit → classified from the configured item's name;
3. a conservative merchant/description rule, applied only when it is
   compatible with the user's old category (a "car" expense is never moved to
   "food" by a merchant rule — that conflict is flagged for review instead);
4. the old category's own meaning (e.g. "רכב" → parent "רכב ותחבורה");
   generic old categories ("קניות", "שונות", empty) → "טרם סווג";
   custom categories with no equivalent are retained as top-level nodes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from .category_tree import (
    UNCLASSIFIED_ID,
    CategoryNode,
    CategoryTree,
    custom_node_id,
    default_outcome_nodes,
)

MIGRATION_ID = "category_hierarchy_v1"
TRANSFER_CATEGORY = "העברה"

# Decision kinds.
MAPPED = "mapped"  # a subcategory
PARENT_ONLY = "parent_only"
CUSTOM = "custom"  # retained custom category (top-level node)
UNCLASSIFIED = "unclassified"
ASSET_ACQUISITION = "asset_acquisition"  # linked to an asset; category kept
UNCHANGED = "unchanged"  # transfer / income / already migrated

ANY_PARENT = "*"

# Old (pre-hierarchy) category → (fallback node id or None, compatible parents).
# A merchant rule may refine an old category only into a compatible parent.
LEGACY_CATEGORY_MAP: Mapping[str, Tuple[Optional[str], FrozenSet[str]]] = {
    "": (None, frozenset({ANY_PARENT})),
    "קניות": (None, frozenset({ANY_PARENT})),
    "שונות": (None, frozenset({ANY_PARENT})),
    "רכב": ("transport", frozenset({"transport"})),
    "תחבורה": ("transport", frozenset({"transport"})),
    "מגורים": ("housing", frozenset({"housing", "home", "fees"})),
    "בריאות": ("health", frozenset({"health"})),
    "ביגוד": ("apparel.clothing", frozenset({"apparel"})),
    "בילויים": ("leisure", frozenset({"leisure", "food"})),
    "בנק": ("fees", frozenset({"fees"})),
    "חינוך": ("kids", frozenset({"kids"})),
}


@dataclass(frozen=True)
class Rule:
    """``target`` when the normalized text contains any of ``any_of`` and none
    of ``none_of`` (``exact``: the whole text equals one of ``any_of``).
    ``old_scope`` limits the rule to movements whose old category is listed."""

    name: str
    target: str
    any_of: Tuple[str, ...]
    none_of: Tuple[str, ...] = ()
    exact: bool = False
    old_scope: Optional[FrozenSet[str]] = None


def _r(name: str, target: str, *any_of: str, none_of: Sequence[str] = (),
       exact: bool = False, old_scope: Optional[Iterable[str]] = None) -> Rule:
    return Rule(name, target, tuple(any_of), tuple(none_of), exact,
                frozenset(old_scope) if old_scope is not None else None)


# Order matters: specific rules before generic ones. Every keyword names a
# purpose or a single-purpose merchant type; ambiguous merchants (IKEA, BuyMe,
# Bit, PayBox, Super-Pharm, gas-station convenience stores, "טיפול <name>")
# deliberately map to a parent at most, or not at all.
DESCRIPTION_RULES: Tuple[Rule, ...] = (
    # ── fees & insurance ──
    _r("bank_fee", "fees.bank", "דמי כרטיס", "עמלה", "עמלת", "ע.מפעולות", "דמי ניהול חשבון"),
    _r("life_health_insurance", "fees.insurance", "הפניקס חיים", "ביטוח חיים", "ביטוח בריאות",
       "ביטוח דירה"),
    # ── car ──
    _r("car_insurance", "transport.insurance", "ביטוח חובה", "ביטוח מקיף", "תוספת מקיף",
       "ר. חובה", "רכב חובה"),
    _r("car_insurance_clearing", "transport.insurance", "מרכז הסליקה של חברות ביטוח",
       old_scope={"רכב"}),
    _r("car_licensing", "transport.licensing", "רשיונות רכב", "רישיונות רכב", "רישוי רכב",
       "רשיון רכב", "רישיון רכב", "מבדקי רכב", "טסט"),
    _r("car_service", "transport.service", "מוסך", "צמיגי", "צמיגים"),
    _r("car_service_scoped", "transport.service", "טיפול", old_scope={"רכב"}),
    _r("transit_app", "transport", "פנגו מוביט"),  # parking or fares — parent only
    _r("parking", "transport.parking_tolls", "חניון", "חניוני", "חניה", "חנייה", "כביש 6",
       "אחוזות חו"),
    _r("public_transport", "transport.public_taxi", "רב-פס", "רב פס", "רב-קו", "מונית",
       "gett", "yango"),
    _r("fuel", "transport.fuel", "תחנת דלק", "תחנות דלק", "דלק ", "סונול", "דור אלון",
       "ביילסול", " טן ", " פז ", none_of=("yellow", "גז")),
    # ── housing ──
    _r("mortgage", "housing.mortgage", "משכנתא", none_of=("יועץ",)),
    _r("rent", "housing.rent", "שכר דירה", "שכירות"),
    _r("municipal_tax", "housing.municipal_tax", "ארנונה"),
    _r("electricity", "housing.electricity", "חברת החשמל"),
    _r("water", "housing.water_gas", "מי לוד", "תאגיד מים", "תאגיד המים"),
    _r("home_gas", "housing.water_gas", "פז גז", "פזגז", "אמישראגז", "סופרגז"),
    _r("building_committee", "housing.building_committee", "ועד בית"),
    # ── home ──
    _r("furniture", "home.furniture", "רהיטים", "ריהוט"),
    _r("housewares", "home.housewares", "כלי בית", "כלים ועיצובים"),
    _r("home_store", "home", "איקאה", "ikea", "הום סנטר", "מחסני תאורה"),
    # ── health ──
    _r("dental", "health.dental", "שיניים", "אורתודונט"),
    _r("pharmacy", "health.medicine", "בית מרקחת", "תרופות"),
    _r("hospital_clinic", "health.doctors", " ביח ", "בית חולים", "מרפאה", "רופא"),
    _r("drugstore", "health", "סופר פארם", "סופר- פארם", "סופרפארם", "דראגסטורס", "פארם"),
    # ── kids ──
    _r("baby_products", "kids.gear", "מטרנה", "סימילאק", "חיתולים", "מוצצים", "כיסא אוכל"),
    _r("daycare", "kids.daycare", "מעון", "מעונות", "צהרון", "גן ילדים"),
    _r("activities", "kids.activities", " חוג ", "חוגים"),
    # ── apparel & grooming ──
    _r("grooming", "apparel.grooming", "מספרה", "תספורת", "פירסינג", "ציפורניים"),
    _r("clothing_online", "apparel.clothing", "shein", "טרמינל איקס"),
    _r("car_rental", "transport.rental", "השכרת רכב", "sixt", "סיקסט", "hertz", "avis",
       "אלדן"),
    _r("jewelry", "apparel.jewelry", "תכשיט"),
    _r("studies", "studies", "שכר לימוד", "אוניברסיט", "מכללה", "האוניברסיטה הפתוחה"),
    # ── leisure ──
    _r("lodging", "leisure.lodging", "צימר", "מלון", "airbnb", "booking.com"),
    _r("attractions", "leisure.outings", "רשות הטבע והגנים", "קולנוע", "זואולוגי", "ספארי",
       "כפר השעשועים", "האגם הקסום", "סגווי"),
    # ── gifts & donations ──
    _r("donation", "gifts.donations", "תרומה", "תרומות", "עזר מציון", "גמ״ח", 'גמ"ח', "נתינה"),
    _r("gift", "gifts.gifts", "מתנה", "מתנת"),
    # ── food ──
    _r("restaurant", "food.restaurants", "מסעדה", "מסעדת", "פיצה", "pizza", "המבורגר",
       "בורגר", "burger", "שווארמה", "חומוס", "סושי", "ביסטרו", "קייטרינג", "משלוחה",
       "שניצל", "ארוחת", "אסאדו", "וולט", "wolt"),
    _r("cafe", "food.restaurants", "קפה", "coffee", "cafe", "בריסטה", "קפיטריה",
       none_of=("מכונות אוטומטיות",)),
    _r("bakery", "food", "מאפיה", "מאפיית", "בייקרי", "פטיסרי", "קונדיטוריה", "בית הפיתה"),
    _r("grocery", "food.grocery", "שופרסל", "רמי לוי", "אושר עד", "יוחננוף", "carrefour",
       "קרפור", "מכולת", "מינימרקט", "מיני מרקט", "טיב טעם", "ויקטורי", "חצי חינם",
       "סופר עומר", "סופר אלונית", "מגה בעיר", "מגה קמעונאות", "פלוס מרקט", "רביד מרקט",
       "מרקט ליז", "פרש דה מרקט", "פירות", "שוק חקלאי", "עוף והודו", "קניות חלב",
       none_of=("תקשורת",)),
    _r("grocery_exact", "food.grocery", "חלב", "ביצים", exact=True),
)

_BIDI = re.compile("[‎‏‪-‮⁦-⁩]")
_WS = re.compile(r"\s+")


def normalize_text(text: Any) -> str:
    s = _BIDI.sub("", str(text or ""))
    return _WS.sub(" ", s).strip().casefold()


def _keyword(text: str) -> str:
    """Like :func:`normalize_text` but keeps edge spaces: a trailing space in a
    keyword ("טן ", "חוג ") means "word boundary"."""
    return _WS.sub(" ", _BIDI.sub("", text)).casefold()


def _parent_id(node_id: str) -> str:
    return node_id.split(".", 1)[0]


def match_rule(text: str, old_category: Optional[str] = None) -> Optional[Rule]:
    """First rule matching ``text`` (already any case/bidi form)."""
    t = normalize_text(text)
    if not t:
        return None
    padded = f" {t} "
    for rule in DESCRIPTION_RULES:
        if rule.old_scope is not None and (old_category or "") not in rule.old_scope:
            continue
        if any(_keyword(x) in padded for x in rule.none_of):
            continue
        if rule.exact:
            if t in {normalize_text(x) for x in rule.any_of}:
                return rule
            continue
        if any(_keyword(x) in padded for x in rule.any_of):
            return rule
    return None


# ── plan ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MovementDecision:
    movement_id: str
    old_category: str
    new_category: str
    kind: str
    reason: str  # rule / link / fallback name (no descriptions)
    review: Optional[str] = None  # why a person should look at it

    @property
    def changed(self) -> bool:
        return self.new_category != self.old_category


@dataclass(frozen=True)
class RecordChange:
    record_id: str
    field_name: str
    old_value: str
    new_value: str


@dataclass
class MigrationPlan:
    tree: CategoryTree
    outcome_names: List[str]
    decisions: List[MovementDecision]
    plan_changes: List[RecordChange]
    mortgage_changes: List[RecordChange]
    retained_legacy: List[str]  # old names still referenced, kept listed

    @property
    def movement_changes(self) -> List[MovementDecision]:
        return [d for d in self.decisions if d.changed]

    def counts(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for d in self.decisions:
            out[d.kind] = out.get(d.kind, 0) + 1
        return out


def _is_transfer_row(row: Mapping[str, Any]) -> bool:
    if bool(row.get("is_transfer")):
        return True
    if str(row.get("category") or "").strip() == TRANSFER_CATEGORY:
        return True
    return bool(str(row.get("transfer_from") or "").strip() or
                str(row.get("transfer_to") or "").strip())


def build_target_tree(old_outcome: Sequence[str]) -> CategoryTree:
    """Default structure + every old custom category that has no mapping."""
    nodes = default_outcome_nodes()
    names = {n.name for n in nodes}
    for name in old_outcome:
        name = str(name or "").strip()
        if (not name or name in LEGACY_CATEGORY_MAP or name == TRANSFER_CATEGORY
                or name in names):
            continue
        nodes.append(CategoryNode(custom_node_id(name), name, None))
        names.add(name)
    return CategoryTree(nodes)


def _explicit_links(
    movements: Sequence[Any], plans: Sequence[Any], assets: Sequence[Any]
) -> Tuple[Dict[str, Tuple[str, str]], Set[str]]:
    """``(movement id → (node id, link reason))`` for configured recurring
    links, and the ids of asset-acquisition movements."""
    from .mortgage import CostItem
    from .mortgage_math import cost_matched_movements, match_movements

    links: Dict[str, Tuple[str, str]] = {}
    acquisition: Set[str] = set()

    def link(ms: Iterable[Any], label: str, reason: str) -> None:
        rule = match_rule(label)
        if rule is None:
            return
        for m in ms:
            links.setdefault(str(m.id), (rule.target, reason))

    for asset in assets:
        pq = str(getattr(asset, "price_query", "") or "").strip()
        if pq:
            acquisition.update(
                str(m.id) for m in cost_matched_movements(CostItem(query=pq), list(movements))
            )
        for cost in list(getattr(asset, "one_time_costs", None) or []):
            acquisition.update(str(m.id) for m in cost_matched_movements(cost, list(movements)))
        for cost in (list(getattr(asset, "monthly_costs", None) or [])
                     + list(getattr(asset, "yearly_costs", None) or [])):
            link(cost_matched_movements(cost, list(movements)),
                 str(getattr(cost, "name", "") or ""), "asset_cost_item")
        acquisition.update(str(x) for x in (getattr(asset, "prepayment_movement_ids", None) or []))
        vq = str(getattr(asset, "vendor_query", "") or "").strip()
        if vq:
            matched = match_movements(
                list(movements), vendor_query=vq,
                account_name=str(getattr(asset, "account_name", "") or ""),
                start_date=str(getattr(asset, "start_date", "") or ""),
                excluded_ids=list(getattr(asset, "excluded_movement_ids", None) or []),
            )
            for m in matched:
                links.setdefault(str(m.id), ("housing.mortgage", "mortgage_payment"))

    for plan in plans:
        label = f"{getattr(plan, 'name', '')} {getattr(plan, 'category', '')}"
        if getattr(plan, "is_direct_debit", False):
            prefix = f"dd-{plan.id}-"
            ms = [m for m in movements if str(m.id).startswith(prefix)]
        else:
            ms = list(plan.matches(list(movements)))
        link(ms, label, "installment_plan")
    return links, acquisition


def _decide(
    row: Mapping[str, Any],
    tree: CategoryTree,
    old_outcome: Set[str],
    links: Mapping[str, Tuple[str, str]],
    acquisition: Set[str],
) -> MovementDecision:
    mid = str(row.get("id") or "")
    old = str(row.get("category") or "").strip()

    def node_name(node_id: str) -> str:
        n = tree.by_id(node_id)
        assert n is not None, node_id
        return n.name

    def result(node_id: str, reason: str, review: Optional[str] = None) -> MovementDecision:
        node = tree.by_id(node_id)
        assert node is not None, node_id
        if node.id == UNCLASSIFIED_ID:
            kind = UNCLASSIFIED
        elif node.id.startswith("custom."):
            kind = CUSTOM
        elif node.parent_id:
            kind = MAPPED
        else:
            kind = PARENT_ONLY
        return MovementDecision(mid, old, node.name, kind, reason, review)

    if _is_transfer_row(row):
        return MovementDecision(mid, old, old, UNCHANGED, "transfer")
    existing_node = tree.by_name(old)
    if existing_node is not None:  # already migrated (or a retained custom)
        kind = CUSTOM if existing_node.id.startswith("custom.") else UNCHANGED
        return MovementDecision(mid, old, old, kind, "already_in_tree")
    if old and old not in old_outcome and old not in LEGACY_CATEGORY_MAP:
        return MovementDecision(mid, old, old, UNCHANGED, "not_an_expense_category")

    if mid in acquisition:
        return MovementDecision(mid, old, old, ASSET_ACQUISITION, "asset_acquisition_link")

    fallback, compatible = LEGACY_CATEGORY_MAP.get(old, (None, frozenset()))
    if old not in LEGACY_CATEGORY_MAP:  # custom category kept as its own node
        return MovementDecision(mid, old, old, CUSTOM, "retained_custom")

    def compatible_with(node_id: str) -> bool:
        return ANY_PARENT in compatible or _parent_id(node_id) in compatible

    if mid in links:
        node_id, reason = links[mid]
        if compatible_with(node_id):
            return result(node_id, reason)
        return result(fallback or UNCLASSIFIED_ID, f"{reason}_conflict",
                      review=f"link suggests {node_name(node_id)}")

    rule = match_rule(str(row.get("description") or ""), old)
    if rule is not None:
        if compatible_with(rule.target):
            return result(rule.target, f"rule:{rule.name}")
        return result(fallback or UNCLASSIFIED_ID, f"old_category:{old}",
                      review=f"rule {rule.name} suggests {node_name(rule.target)}")

    if fallback is None:
        return result(UNCLASSIFIED_ID, f"old_category:{old or 'empty'}")
    return result(fallback, f"old_category:{old}")


def relabel(description: Any, old_category: str, tree: CategoryTree) -> Optional[str]:
    """New label for a stored (description, old category) pair — e.g. a
    classifier training example — using the same rules as the migration but
    without plan/asset links. ``None`` when nothing usable can be said."""
    old = str(old_category or "").strip()
    if tree.by_name(old) is not None:
        return None if tree.is_unclassified(old) else old
    if old not in LEGACY_CATEGORY_MAP:
        return None
    fallback, compatible = LEGACY_CATEGORY_MAP[old]
    rule = match_rule(str(description or ""), old)
    node_id = None
    if rule is not None and (ANY_PARENT in compatible or _parent_id(rule.target) in compatible):
        node_id = rule.target
    elif fallback is not None:
        node_id = fallback
    node = tree.by_id(node_id) if node_id else None
    return node.name if node is not None else None


def plan_migration(
    movement_rows: Sequence[Mapping[str, Any]],
    *,
    plans: Sequence[Any] = (),
    assets: Sequence[Any] = (),
    categories_data: Optional[Mapping[str, Any]] = None,
) -> MigrationPlan:
    """Deterministic plan. ``movement_rows`` are the raw stored dicts."""
    from .bank_movement import deserialize_bank_movement

    data = dict(categories_data or {})
    existing = CategoryTree.from_storage(data)
    raw_outcome = [str(x).strip() for x in (data.get("outcome") or []) if str(x).strip()]
    old_outcome = [n for n in raw_outcome if existing.by_name(n) is None]
    old_outcome_set = set(old_outcome) | set(existing.legacy_aliases)
    tree = build_target_tree(old_outcome)
    if existing:  # keep nodes added after a previous run (ids stable)
        from .category_tree import merge_tree_nodes

        tree = CategoryTree(merge_tree_nodes(existing.nodes, tree.nodes),
                            existing.legacy_aliases)

    movements = [m for m in (deserialize_bank_movement(r) for r in movement_rows) if m]
    links, acquisition = _explicit_links(movements, plans, assets)
    decisions = [
        _decide(row, tree, old_outcome_set, links, acquisition) for row in movement_rows
    ]

    # Old names still used after the migration stay listed (never deleted while
    # referenced); every other legacy name is retired with an alias.
    still_used = {d.new_category for d in decisions if d.kind == ASSET_ACQUISITION}
    aliases = dict(existing.legacy_aliases)
    for name, (fallback, _compat) in LEGACY_CATEGORY_MAP.items():
        if name and name in old_outcome_set and name not in still_used:
            target = tree.by_id(fallback or UNCLASSIFIED_ID)
            if target is not None:
                aliases.setdefault(name, target.name)
    for name in still_used:
        aliases.pop(name, None)
    tree = CategoryTree(tree.nodes, aliases)

    retained = sorted(n for n in still_used if n and tree.by_name(n) is None)
    extra = [n for n in raw_outcome
             if tree.by_name(n) is None and n not in aliases and n not in retained]
    outcome_names = tree.assignable_names() + retained + [
        n for n in extra if n not in retained
    ]

    plan_changes: List[RecordChange] = []
    for p in plans:
        cat = str(getattr(p, "category", "") or "").strip()
        if not cat or tree.by_name(cat) is not None:
            continue
        rule = match_rule(f"{getattr(p, 'name', '')}")
        _fallback, compat = LEGACY_CATEGORY_MAP.get(cat, (None, frozenset()))
        if rule is not None and (ANY_PARENT in compat or _parent_id(rule.target) in compat):
            new = tree.by_id(rule.target)
        else:
            new = tree.by_name(tree.resolve_reference(cat))
        if new is not None and new.name != cat:
            plan_changes.append(RecordChange(str(p.id), "category", cat, new.name))

    mortgage_changes: List[RecordChange] = []
    for a in assets:
        cat = str(getattr(a, "expense_category", "") or "").strip()
        if cat and tree.by_name(cat) is None and cat in aliases:
            mortgage_changes.append(
                RecordChange(str(a.id), "expense_category", cat, aliases[cat])
            )

    return MigrationPlan(tree, outcome_names, decisions, plan_changes,
                         mortgage_changes, retained)


# ── runner (I/O) ──────────────────────────────────────────────────────────


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".migrating")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


@dataclass(frozen=True)
class WorkspaceFiles:
    accounts_dir: Path
    key: str  # workspace id (or uid)
    backup_root: Optional[Path] = None

    def path(self, stem: str) -> Path:
        return self.accounts_dir / f"{stem}_{self.key}.json"

    @property
    def movements(self) -> Path:
        return self.path("bank_movements")

    @property
    def categories(self) -> Path:
        return self.path("bank_movement_categories")

    @property
    def plans(self) -> Path:
        return self.path("installment_plans")

    @property
    def mortgages(self) -> Path:
        return self.path("mortgages")

    @property
    def state(self) -> Path:
        return self.accounts_dir / f"category_migration_{self.key}.json"

    @property
    def backups(self) -> Path:
        return self.backup_root or (self.accounts_dir / "migration_backups")

    @classmethod
    def current(cls) -> "WorkspaceFiles":
        from ..data.bank_movement_provider import JsonFileBankMovementProvider

        p = JsonFileBankMovementProvider().categories_path
        prefix = "bank_movement_categories_"
        stem = p.stem
        if not stem.startswith(prefix):
            raise RuntimeError("no workspace is active")
        return cls(accounts_dir=p.parent, key=stem[len(prefix):])


@dataclass
class Pushed:
    movements: int = 0
    plans: int = 0
    mortgages: int = 0
    categories: int = 0
    batches: int = 0


class MigrationPusher:
    """Sends only the changed records. The default uses the app's Firebase
    writer (bulk commit for movements, within the backend batch limit)."""

    def push(self, *, movements: List[Any], plans: List[Any], mortgages: List[Any],
             income: List[str], outcome: List[str], tree: Optional[CategoryTree],
             clear_tree: bool = False) -> Pushed:
        raise NotImplementedError


class FirebaseMigrationPusher(MigrationPusher):
    BATCH_SIZE = 400  # Firestore commit limit is 500 writes

    def push(self, *, movements, plans, mortgages, income, outcome, tree,
             clear_tree=False) -> Pushed:
        from .firebase_workspace_writer import FirebaseWorkspaceWriter

        writer = FirebaseWorkspaceWriter()
        out = Pushed()
        if movements:
            out.movements = int(writer.upsert_movements_bulk(movements,
                                                             batch_size=self.BATCH_SIZE))
            out.batches = -(-len(movements) // self.BATCH_SIZE)
        for p in plans:
            writer.upsert_installment_plan(p)
            out.plans += 1
        for m in mortgages:
            writer.upsert_mortgage(m)
            out.mortgages += 1
        if clear_tree:
            writer.clear_category_tree(income=income, outcome=outcome)
        else:
            writer.upsert_categories(income=income, outcome=outcome, tree=tree)
        out.categories = 1
        return out


@dataclass
class MigrationReport:
    mode: str  # dry_run | apply | rollback | noop
    plan: Optional[MigrationPlan] = None
    changed_movements: int = 0
    changed_plans: int = 0
    changed_mortgages: int = 0
    files_written: List[str] = field(default_factory=list)
    backup_dir: Optional[str] = None
    pushed: Optional[Pushed] = None
    refreshed: int = 0
    retrained: int = 0
    skipped_user_edits: int = 0
    timings: Dict[str, float] = field(default_factory=dict)
    reads: int = 0


class CategoryMigrationRunner:
    """Dry-run / apply / rollback for one workspace's files."""

    def __init__(
        self,
        files: WorkspaceFiles,
        *,
        pusher: Optional[MigrationPusher] = None,
        refresh: Optional[Callable[[], Any]] = None,
        retrain: Optional[Callable[[], Any]] = None,
        progress: Optional[Callable[[str, int, int], None]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.files = files
        self.pusher = pusher
        self.refresh = refresh
        self.retrain = retrain
        self.progress = progress or (lambda _s, _i, _n: None)
        self.clock = clock

    # ── helpers ──
    def _load(self) -> Tuple[list, dict, list, list, Any, Any]:
        from ..data.installment_plan_provider import JsonFileInstallmentPlanProvider
        from ..data.mortgage_provider import deserialize_mortgage

        rows = _read_json(self.files.movements, [])
        cats = _read_json(self.files.categories, {})
        plan_rows = _read_json(self.files.plans, [])
        mortgage_rows = _read_json(self.files.mortgages, [])
        plans = [p for p in (JsonFileInstallmentPlanProvider._deserialize(r)
                             for r in plan_rows) if p is not None]
        assets = [a for a in (deserialize_mortgage(r) for r in mortgage_rows) if a is not None]
        return rows, (cats if isinstance(cats, dict) else {}), plan_rows, mortgage_rows, plans, assets

    def _state(self) -> dict:
        s = _read_json(self.files.state, {})
        return s if isinstance(s, dict) and s.get("migration_id") == MIGRATION_ID else {}

    def _save_state(self, state: dict) -> None:
        state["migration_id"] = MIGRATION_ID
        _atomic_write_json(self.files.state, state)

    def plan(self) -> MigrationPlan:
        rows, cats, _pr, _mr, plans, assets = self._load()
        return plan_migration(rows, plans=plans, assets=assets, categories_data=cats)

    def dry_run(self) -> MigrationReport:
        t0 = time.perf_counter()
        plan = self.plan()
        return MigrationReport(
            mode="dry_run", plan=plan,
            changed_movements=len(plan.movement_changes),
            changed_plans=len(plan.plan_changes),
            changed_mortgages=len(plan.mortgage_changes),
            timings={"plan": time.perf_counter() - t0}, reads=4,
        )

    def _backup(self) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(self.clock()))
        dest = self.files.backups / f"{MIGRATION_ID}_{self.files.key}_{stamp}"
        dest.mkdir(parents=True, exist_ok=False)
        for src in (self.files.movements, self.files.categories, self.files.plans,
                    self.files.mortgages):
            if src.exists():
                shutil.copy2(src, dest / src.name)
        return dest

    def apply(self) -> MigrationReport:
        timings: Dict[str, float] = {}
        t0 = time.perf_counter()
        state = self._state()
        rows, cats, plan_rows, mortgage_rows, plans, assets = self._load()
        plan = plan_migration(rows, plans=plans, assets=assets, categories_data=cats)
        timings["read_and_plan"] = time.perf_counter() - t0
        report = MigrationReport(mode="apply", plan=plan, timings=timings, reads=4)

        tree_unchanged = (
            CategoryTree.from_storage(cats).nodes == plan.tree.nodes
            and CategoryTree.from_storage(cats).legacy_aliases == plan.tree.legacy_aliases
            and list(cats.get("outcome") or []) == plan.outcome_names
        )
        nothing_to_write = (
            not plan.movement_changes and not plan.plan_changes
            and not plan.mortgage_changes and tree_unchanged
        )
        if state.get("status") == "done" and nothing_to_write:
            report.mode = "noop"
            return report

        # 1. backup (once per migration run) + rollback mapping
        if not state.get("backup_dir") or state.get("status") == "rolled_back":
            backup = self._backup()
            state = {"status": "backed_up", "backup_dir": str(backup),
                     "started_at": self.clock()}
            self._save_state(state)
        backup_dir = Path(state["backup_dir"])
        report.backup_dir = str(backup_dir)

        # 2. record intent before writing (resumable)
        mapping_path = backup_dir / "rollback_mapping.json"
        mapping = _read_json(mapping_path, {"movements": {}, "plans": {}, "mortgages": {}})
        for d in plan.movement_changes:
            mapping["movements"].setdefault(d.movement_id, [d.old_category, d.new_category])
        for c in plan.plan_changes:
            mapping["plans"].setdefault(c.record_id, [c.old_value, c.new_value])
        for c in plan.mortgage_changes:
            mapping["mortgages"].setdefault(c.record_id, [c.old_value, c.new_value])
        _atomic_write_json(mapping_path, mapping)
        state["status"] = "applying"
        state["pending_push"] = {
            "movements": sorted(set(state.get("pending_push", {}).get("movements", []))
                                | {d.movement_id for d in plan.movement_changes}),
            "plans": sorted(set(state.get("pending_push", {}).get("plans", []))
                            | {c.record_id for c in plan.plan_changes}),
            "mortgages": sorted(set(state.get("pending_push", {}).get("mortgages", []))
                                | {c.record_id for c in plan.mortgage_changes}),
        }
        self._save_state(state)

        # 3. local writes — only category fields change; one write per file
        t1 = time.perf_counter()
        new_by_id = {d.movement_id: d.new_category for d in plan.movement_changes}
        total = len(rows)
        if new_by_id:
            for i, r in enumerate(rows):
                mid = str(r.get("id") or "")
                if mid in new_by_id:
                    r["category"] = new_by_id[mid]
                if i % 250 == 0:
                    self.progress("movements", i, total)
            _atomic_write_json(self.files.movements, rows)
            report.files_written.append(self.files.movements.name)
        self.progress("movements", total, total)
        if plan.plan_changes:
            by_id = {c.record_id: c.new_value for c in plan.plan_changes}
            for r in plan_rows:
                if str(r.get("id")) in by_id:
                    r["category"] = by_id[str(r.get("id"))]
            _atomic_write_json(self.files.plans, plan_rows)
            report.files_written.append(self.files.plans.name)
        if plan.mortgage_changes:
            by_id = {c.record_id: c.new_value for c in plan.mortgage_changes}
            for r in mortgage_rows:
                if str(r.get("id")) in by_id:
                    r["expense_category"] = by_id[str(r.get("id"))]
            _atomic_write_json(self.files.mortgages, mortgage_rows)
            report.files_written.append(self.files.mortgages.name)
        if not tree_unchanged:
            from .category_tree import SCHEMA_VERSION

            cats = dict(cats)
            cats.setdefault("income", [])
            cats["outcome"] = plan.outcome_names
            cats["outcome_tree"] = plan.tree.nodes_to_list()
            cats["legacy_aliases"] = dict(plan.tree.legacy_aliases)
            cats["schema_version"] = SCHEMA_VERSION
            _atomic_write_json(self.files.categories, cats)
            report.files_written.append(self.files.categories.name)
        timings["local_writes"] = time.perf_counter() - t1
        report.changed_movements = len(plan.movement_changes)
        report.changed_plans = len(plan.plan_changes)
        report.changed_mortgages = len(plan.mortgage_changes)
        state["status"] = "applied_local"
        self._save_state(state)

        # 4. push changed records only, 5. one refresh, 6. one retrain
        self._finish(state, report, timings, clear_tree=False)
        return report

    def _finish(self, state: dict, report: MigrationReport, timings: Dict[str, float],
                *, clear_tree: bool) -> None:
        if self.pusher is not None:
            t2 = time.perf_counter()
            rows, cats, _pr, _mr, plans, assets = self._load()
            from .bank_movement import deserialize_bank_movement

            pending = state.get("pending_push", {})
            want_m = set(pending.get("movements", []))
            want_p = set(pending.get("plans", []))
            want_a = set(pending.get("mortgages", []))
            movements = [m for m in (deserialize_bank_movement(r) for r in rows
                                     if str(r.get("id") or "") in want_m) if m]
            tree = CategoryTree.from_storage(cats)
            report.pushed = self.pusher.push(
                movements=movements,
                plans=[p for p in plans if str(p.id) in want_p],
                mortgages=[a for a in assets if str(a.id) in want_a],
                income=list(cats.get("income") or []),
                outcome=list(cats.get("outcome") or []),
                tree=tree or None,
                clear_tree=clear_tree,
            )
            state["pending_push"] = {}
            state["status"] = "pushed"
            self._save_state(state)
            timings["push"] = time.perf_counter() - t2
        if self.refresh is not None:
            t3 = time.perf_counter()
            self.refresh()
            report.refreshed = 1
            timings["notification_refresh"] = time.perf_counter() - t3
        if self.retrain is not None:
            t4 = time.perf_counter()
            self.retrain()
            report.retrained = 1
            timings["classifier_rebuild"] = time.perf_counter() - t4
        state["status"] = "done" if not clear_tree else "rolled_back"
        state["finished_at"] = self.clock()
        self._save_state(state)

    def rollback(self) -> MigrationReport:
        """Restore the original categories from the rollback mapping. A record
        the user changed after the migration is left alone (and counted)."""
        state = self._state()
        backup = Path(state.get("backup_dir") or "")
        mapping = _read_json(backup / "rollback_mapping.json", None)
        if not state or mapping is None:
            raise RuntimeError("no completed migration to roll back")
        report = MigrationReport(mode="rollback", backup_dir=str(backup))
        rows, cats, plan_rows, mortgage_rows, _plans, _assets = self._load()
        changed_m: List[str] = []
        for r in rows:
            mid = str(r.get("id") or "")
            pair = mapping["movements"].get(mid)
            if pair is None:
                continue
            old, new = pair
            if str(r.get("category") or "") == new:
                r["category"] = old
                changed_m.append(mid)
            else:
                report.skipped_user_edits += 1
        changed_p: List[str] = []
        for r in plan_rows:
            pair = mapping["plans"].get(str(r.get("id")))
            if pair and str(r.get("category") or "") == pair[1]:
                r["category"] = pair[0]
                changed_p.append(str(r.get("id")))
        changed_a: List[str] = []
        for r in mortgage_rows:
            pair = mapping["mortgages"].get(str(r.get("id")))
            if pair and str(r.get("expense_category") or "") == pair[1]:
                r["expense_category"] = pair[0]
                changed_a.append(str(r.get("id")))
        state["pending_push"] = {"movements": changed_m, "plans": changed_p,
                                 "mortgages": changed_a}
        state["status"] = "rolling_back"
        self._save_state(state)
        if changed_m:
            _atomic_write_json(self.files.movements, rows)
        if changed_p:
            _atomic_write_json(self.files.plans, plan_rows)
        if changed_a:
            _atomic_write_json(self.files.mortgages, mortgage_rows)
        original = _read_json(backup / self.files.categories.name, {})
        restored = dict(original) if isinstance(original, dict) else {}
        tree = CategoryTree.from_storage(cats)
        for key in ("income", "outcome"):
            names = list(restored.get(key) or [])
            for n in cats.get(key) or []:  # names the user added since
                if n not in names and tree.by_name(n) is None and n not in tree.legacy_aliases:
                    names.append(n)
            restored[key] = names
        for key in ("outcome_tree", "legacy_aliases", "schema_version"):
            restored.pop(key, None)
        _atomic_write_json(self.files.categories, restored)
        report.changed_movements = len(changed_m)
        report.changed_plans = len(changed_p)
        report.changed_mortgages = len(changed_a)
        self._finish(state, report, report.timings, clear_tree=True)
        return report
