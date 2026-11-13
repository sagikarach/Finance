"""Structural edits to the expense-category hierarchy: rename, merge, add.

Pure planning (:func:`plan_category_edit`) plus an applier that reuses the
migration's safety rails: backup first, atomic writes that change only category
fields, push of the changed records only, then one notification refresh and one
classifier rebuild. Re-applying the same edit is a no-op (no writes).

Merged/renamed names are kept as legacy aliases, so references resolve and an
older client's category list cannot resurrect them on sync.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .category_migration import (
    MigrationPusher,
    Pushed,
    WorkspaceFiles,
    _atomic_write_json,
    _read_json,
)
from .category_tree import (
    SCHEMA_VERSION,
    UNCLASSIFIED_ID,
    CategoryNode,
    CategoryTree,
    filter_retired_names,
)


@dataclass
class CategoryEdit:
    renames: Dict[str, str] = field(default_factory=dict)  # node id → new name
    merges: Dict[str, str] = field(default_factory=dict)  # source id → target id
    additions: List[CategoryNode] = field(default_factory=list)


def plan_category_edit(tree: CategoryTree, edit: CategoryEdit) -> Tuple[CategoryTree, Dict[str, str]]:
    """``(new tree, {old name → new name})``. Raises ``ValueError`` for an
    invalid edit (unknown id, merging a parent with children, duplicate name)."""
    by_id = {n.id: n for n in tree.nodes}
    final_name = {nid: edit.renames.get(nid, n.name) for nid, n in by_id.items()}
    for src, dst in edit.merges.items():
        if src not in by_id or dst not in by_id:
            if src not in by_id and dst in by_id:
                continue  # already merged earlier → idempotent
            raise ValueError(f"unknown category id in merge: {src} → {dst}")
        if tree.children_of(by_id[src].name):
            raise ValueError("only leaf categories can be merged")
    for nid in edit.renames:
        if nid not in by_id:
            raise ValueError(f"unknown category id: {nid}")

    name_map: Dict[str, str] = {}
    for nid, n in by_id.items():
        if nid in edit.merges:
            target = edit.merges[nid]
            name_map[n.name] = final_name[target]
        elif final_name[nid] != n.name:
            name_map[n.name] = final_name[nid]

    nodes: List[CategoryNode] = [
        CategoryNode(n.id, final_name[n.id], n.parent_id)
        for n in tree.nodes
        if n.id not in edit.merges
    ]
    ids = {n.id for n in nodes}
    for add in edit.additions:
        if add.id in ids:
            continue  # already added → idempotent
        if add.parent_id and add.parent_id not in ids:
            raise ValueError(f"unknown parent id: {add.parent_id}")
        if add.parent_id:
            # after the parent's last child
            pos = max(i for i, n in enumerate(nodes)
                      if n.id == add.parent_id or n.parent_id == add.parent_id) + 1
        else:
            pos = next((i for i, n in enumerate(nodes) if n.id == UNCLASSIFIED_ID), len(nodes))
        nodes.insert(pos, add)
        ids.add(add.id)

    aliases = {old: name_map.get(new, new) for old, new in tree.legacy_aliases.items()}
    for old, new in name_map.items():
        aliases[old] = new
    new_tree = CategoryTree(nodes, {})  # validates unique names
    aliases = {k: v for k, v in aliases.items() if new_tree.by_name(k) is None}
    return CategoryTree(nodes, aliases), name_map


@dataclass
class EditReport:
    mode: str
    changed_movements: int = 0
    changed_plans: int = 0
    changed_mortgages: int = 0
    tree_changed: bool = False
    backup_dir: Optional[str] = None
    pushed: Optional[Pushed] = None
    refreshed: int = 0
    retrained: int = 0
    moved: Dict[str, int] = field(default_factory=dict)  # "old → new": count
    timings: Dict[str, float] = field(default_factory=dict)


def apply_category_edit(
    files: WorkspaceFiles,
    edit: CategoryEdit,
    *,
    dry_run: bool = False,
    pusher: Optional[MigrationPusher] = None,
    refresh: Optional[Callable[[], Any]] = None,
    retrain: Optional[Callable[[], Any]] = None,
    clock: Callable[[], float] = time.time,
) -> EditReport:
    t0 = time.perf_counter()
    rows = _read_json(files.movements, [])
    cats = _read_json(files.categories, {})
    plan_rows = _read_json(files.plans, [])
    mortgage_rows = _read_json(files.mortgages, [])
    tree = CategoryTree.from_storage(cats)
    if not tree:
        raise RuntimeError("no category hierarchy — run the category migration first")
    new_tree, name_map = plan_category_edit(tree, edit)
    # names retired earlier but still on records (e.g. synced from an old client)
    full_map = dict(new_tree.legacy_aliases)
    full_map.update(name_map)

    report = EditReport(mode="dry_run" if dry_run else "apply")
    changed_ids: List[str] = []
    for r in rows:
        old = str(r.get("category") or "")
        if old in name_map:
            key = f"{old} → {name_map[old]}"
            report.moved[key] = report.moved.get(key, 0) + 1
            changed_ids.append(str(r.get("id")))
    changed_plans = [r for r in plan_rows if str(r.get("category") or "") in name_map]
    changed_mortgages = [
        r for r in mortgage_rows
        if str(r.get("expense_category") or "") in name_map
        or any(str(x) in name_map for x in (r.get("expense_categories") or []))
    ]
    outcome = list(cats.get("outcome") or [])
    ordered = new_tree.assignable_names()
    new_outcome = filter_retired_names(
        ordered + [n for n in outcome if n not in ordered and n not in full_map], new_tree
    )
    report.tree_changed = (
        new_tree.nodes != tree.nodes
        or new_tree.legacy_aliases != tree.legacy_aliases
        or new_outcome != outcome
    )
    report.changed_movements = len(changed_ids)
    report.changed_plans = len(changed_plans)
    report.changed_mortgages = len(changed_mortgages)
    report.timings["read_and_plan"] = time.perf_counter() - t0
    if dry_run:
        return report
    if not (changed_ids or changed_plans or changed_mortgages or report.tree_changed):
        report.mode = "noop"
        return report

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(clock()))
    backup = files.backups / f"category_edit_{files.key}_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    for src in (files.movements, files.categories, files.plans, files.mortgages):
        if src.exists():
            shutil.copy2(src, backup / src.name)
    report.backup_dir = str(backup)

    t1 = time.perf_counter()
    if changed_ids:
        for r in rows:
            old = str(r.get("category") or "")
            if old in name_map:
                r["category"] = name_map[old]
        _atomic_write_json(files.movements, rows)
    if changed_plans:
        for r in changed_plans:
            r["category"] = name_map[str(r["category"])]
        _atomic_write_json(files.plans, plan_rows)
    if changed_mortgages:
        for r in changed_mortgages:
            old_single = str(r.get("expense_category") or "")
            if old_single in name_map:
                r["expense_category"] = name_map[old_single]
            if r.get("expense_categories"):
                mapped: list = []
                for x in r["expense_categories"]:
                    y = name_map.get(str(x), str(x))
                    if y not in mapped:  # two merged names count once
                        mapped.append(y)
                r["expense_categories"] = mapped
        _atomic_write_json(files.mortgages, mortgage_rows)
    cats = dict(cats)
    cats["outcome"] = new_outcome
    cats["outcome_tree"] = new_tree.nodes_to_list()
    cats["legacy_aliases"] = dict(new_tree.legacy_aliases)
    cats["schema_version"] = SCHEMA_VERSION
    _atomic_write_json(files.categories, cats)
    report.timings["local_writes"] = time.perf_counter() - t1

    if pusher is not None:
        from ..data.installment_plan_provider import JsonFileInstallmentPlanProvider
        from ..data.mortgage_provider import deserialize_mortgage
        from .bank_movement import deserialize_bank_movement

        t2 = time.perf_counter()
        want = set(changed_ids)
        report.pushed = pusher.push(
            movements=[m for m in (deserialize_bank_movement(r) for r in rows
                                   if str(r.get("id")) in want) if m],
            plans=[p for p in (JsonFileInstallmentPlanProvider._deserialize(r)
                               for r in changed_plans) if p],
            mortgages=[a for a in (deserialize_mortgage(r) for r in changed_mortgages) if a],
            income=list(cats.get("income") or []),
            outcome=new_outcome,
            tree=new_tree,
        )
        report.timings["push"] = time.perf_counter() - t2
    if refresh is not None:
        refresh()
        report.refreshed = 1
    if retrain is not None:
        retrain()
        report.retrained = 1
    report.timings["total"] = time.perf_counter() - t0
    return report


def restore_backup(files: WorkspaceFiles, backup_dir: Path) -> List[str]:
    """Copy a backup's files back (full local revert; push with a sync)."""
    restored = []
    for name in (files.movements.name, files.categories.name, files.plans.name,
                 files.mortgages.name):
        src = backup_dir / name
        if src.exists():
            shutil.copy2(src, files.accounts_dir / name)
            restored.append(name)
    return restored


# ── per-movement category corrections (a reviewed list, not a rule) ───────


@dataclass(frozen=True)
class MovementCorrection:
    """Set ``movement_id``'s category to ``category`` — only while it still
    has ``expected`` (a record the user changed since the review is left
    alone). ``reason`` is kept in the report for the audit trail."""

    movement_id: str
    expected: str
    category: str
    reason: str = ""


@dataclass
class CorrectionReport:
    mode: str  # dry_run | apply | noop
    changed: List[str] = field(default_factory=list)  # movement ids
    already: List[str] = field(default_factory=list)  # already had the target
    conflicts: Dict[str, str] = field(default_factory=dict)  # id → current category
    missing: List[str] = field(default_factory=list)
    backup_dir: Optional[str] = None
    pushed: Optional[Pushed] = None
    refreshed: int = 0
    retrained: int = 0


def apply_movement_corrections(
    files: WorkspaceFiles,
    corrections: List[MovementCorrection],
    *,
    dry_run: bool = False,
    pusher: Optional[MigrationPusher] = None,
    refresh: Optional[Callable[[], Any]] = None,
    retrain: Optional[Callable[[], Any]] = None,
    clock: Callable[[], float] = time.time,
) -> CorrectionReport:
    """Change only the ``category`` of the listed expense movements, after a
    backup, in one atomic write; push only the changed movements; refresh and
    retrain once. Targets must be current (non-retired) category names.
    Re-running is a no-op (each record already has its target)."""
    rows = _read_json(files.movements, [])
    cats = _read_json(files.categories, {})
    tree = CategoryTree.from_storage(cats)
    allowed = set(cats.get("outcome") or []) | {n.name for n in tree.nodes}
    for c in corrections:
        target = str(c.category or "").strip()
        if not target or target not in allowed:
            raise ValueError(f"unknown target category: {target!r}")
        if tree and target in tree.legacy_aliases and tree.by_name(target) is None:
            raise ValueError(f"retired target category: {target!r}")
    by_id = {str(r.get("id")): r for r in rows}
    report = CorrectionReport(mode="dry_run" if dry_run else "apply")
    todo: Dict[str, str] = {}
    for c in corrections:
        r = by_id.get(c.movement_id)
        if r is None:
            report.missing.append(c.movement_id)
            continue
        current = str(r.get("category") or "")
        try:
            is_expense = float(r.get("amount") or 0) < 0 and not r.get("is_transfer")
        except (TypeError, ValueError):
            is_expense = False
        if current == c.category:
            report.already.append(c.movement_id)
        elif current != c.expected or not is_expense:
            report.conflicts[c.movement_id] = current
        else:
            todo[c.movement_id] = c.category
    report.changed = list(todo)
    if dry_run:
        return report
    if not todo:
        report.mode = "noop"
        return report

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(clock()))
    backup = files.backups / f"category_fix_{files.key}_{stamp}"
    backup.mkdir(parents=True, exist_ok=False)
    for src in (files.movements, files.categories):
        if src.exists():
            shutil.copy2(src, backup / src.name)
    (backup / "corrections.json").write_text(
        json.dumps([vars(c) for c in corrections], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report.backup_dir = str(backup)
    for mid, cat in todo.items():
        by_id[mid]["category"] = cat
    _atomic_write_json(files.movements, rows)

    if pusher is not None:
        from .bank_movement import deserialize_bank_movement

        report.pushed = pusher.push(
            movements=[m for m in (deserialize_bank_movement(by_id[i]) for i in todo) if m],
            plans=[], mortgages=[],
            income=list(cats.get("income") or []),
            outcome=list(cats.get("outcome") or []),
            tree=tree or None,
        )
    if refresh is not None:
        refresh()
        report.refreshed = 1
    if retrain is not None:
        retrain()
        report.retrained = 1
    return report
