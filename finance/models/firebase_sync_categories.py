from __future__ import annotations

from typing import List

from .category_tree import CategoryTree, filter_retired_names, merge_tree_nodes
from .firebase_client import FirestoreClient
from ..utils.safe import PARSE_ERRORS, swallow
from ..utils.logging_setup import get_logger
_log = get_logger("models")


def _clean_names(raw: object) -> List[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if isinstance(x, str) and str(x).strip()]


def sync_categories(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    uid: str,
    id_token: str,
    provider,
    allow_push: bool,
) -> None:
    """Merge the category lists (union) and the expense hierarchy (union by
    node id, local wins). Retired pre-hierarchy names are dropped from the
    merged expense list so an older client cannot resurrect them."""
    workspace_id = (workspace_id or "").strip()
    if workspace_id:
        doc_path = f"workspaces/{workspace_id}/meta/categories"
    else:
        doc_path = f"users/{uid}/meta/categories"

    remote_income: List[str] = []
    remote_outcome: List[str] = []
    remote_tree = CategoryTree([])
    try:
        doc = fs.get_document(document_path=doc_path, id_token=id_token)
        _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
        remote_income = _clean_names(parsed.get("income", []))
        remote_outcome = _clean_names(parsed.get("outcome", []))
        remote_tree = CategoryTree.from_storage(parsed)
    except Exception as exc:  # noqa: BLE001
        _log.debug("sync_categories: %s", exc)
        remote_income = []
        remote_outcome = []

    try:
        local_income = list(provider.list_categories_for_type(True))
    except PARSE_ERRORS:
        local_income = []
    try:
        local_outcome = list(provider.list_categories_for_type(False))
    except PARSE_ERRORS:
        local_outcome = []
    local_tree: CategoryTree = CategoryTree([])
    with swallow(msg="sync_categories"):
        loader = getattr(provider, "load_category_tree", None)
        loaded = loader() if callable(loader) else None
        if isinstance(loaded, CategoryTree):
            local_tree = loaded

    tree: CategoryTree = local_tree
    if remote_tree or remote_tree.legacy_aliases:
        try:
            aliases = dict(remote_tree.legacy_aliases)
            aliases.update(local_tree.legacy_aliases)
            tree = CategoryTree(
                merge_tree_nodes(local_tree.nodes, remote_tree.nodes), aliases
            )
        except ValueError as exc:
            _log.debug("sync_categories: tree merge skipped: %s", exc)
            tree = local_tree

    merged_income = sorted({*(remote_income), *(local_income)})
    merged_outcome = sorted({*(remote_outcome), *(local_outcome)})
    if tree:
        # Tree order first, then any other (custom / mobile-added) names.
        ordered = tree.assignable_names()
        merged_outcome = ordered + [n for n in merged_outcome if n not in ordered]
    merged_outcome = filter_retired_names(merged_outcome, tree)

    if allow_push:
        fields: dict = {"income": merged_income, "outcome": merged_outcome, "version": 1}
        if tree:
            from .category_tree import SCHEMA_VERSION

            fields["outcome_tree"] = tree.nodes_to_list()
            fields["legacy_aliases"] = dict(tree.legacy_aliases)
            fields["schema_version"] = SCHEMA_VERSION
        fs.patch_document_fields(document_path=doc_path, id_token=id_token, fields=fields)

    with swallow(msg="sync_categories"):
        tree_changed = tree.nodes != local_tree.nodes or (
            tree.legacy_aliases != local_tree.legacy_aliases
        )
        outcome_changed = merged_outcome != local_outcome
        income_missing = [c for c in merged_income if c not in local_income]
        if tree and (tree_changed or outcome_changed):
            provider.save_category_tree(tree, outcome_names=merged_outcome)
        elif outcome_changed and not tree:
            for c in merged_outcome:
                provider.add_category_for_type(c, False)
        for c in income_missing:
            provider.add_category_for_type(c, True)
