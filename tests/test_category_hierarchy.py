"""Category hierarchy: tree model, migration (mapping, integrity, idempotency,
resume, rollback), persistence + sync, reports, and the detector's
subcategory baselines. Everything runs on temp files with the network blocked.
"""

from __future__ import annotations

import json
import socket
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import pytest

import finance.models.gemini_classifier as gemini_classifier
from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.data.notifications_provider import JsonFileNotificationsProvider
from finance.models import category_tree as ct
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.category_migration import (
    ASSET_ACQUISITION,
    CUSTOM,
    MAPPED,
    PARENT_ONLY,
    UNCHANGED,
    UNCLASSIFIED,
    CategoryMigrationRunner,
    MigrationPusher,
    Pushed,
    WorkspaceFiles,
    match_rule,
    plan_migration,
    relabel,
)
from finance.models.category_tree import (
    UNCLASSIFIED_NAME,
    CategoryNode,
    CategoryTree,
    default_outcome_nodes,
    filter_retired_names,
    merge_tree_nodes,
    report_group,
)
from finance.models.installment_plan import InstallmentPlan
from finance.models.monthly_report import CategoryMonthlyBreakdown
from finance.models.mortgage import CostItem, Mortgage
from finance.models.notifications import (
    CLOSED_BY_USER,
    Notification,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from finance.models.notifications_service import NotificationsService
from finance.models.unusual_expense_detector import (
    DetectionIndex,
    Outcome,
    baseline_window,
    evaluate_month,
)

KEY = "WS-TEST"
EVAL = (2026, 10)
BASELINE = baseline_window(EVAL, 6)
OLD_OUTCOME = ["קניות", "שונות", "רכב", "תחבורה", "מגורים", "בריאות", "ביגוד",
               "בילויים", "בנק", "חינוך", "דת", "העברה"]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "data"))

    def _no_network(*_a, **_k):
        raise OSError("network disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)

    def _no_ai(*_a, **_k):
        raise AssertionError("AI service must not be used")

    monkeypatch.setattr(gemini_classifier, "get_gemini_classifier", _no_ai)
    monkeypatch.setattr(gemini_classifier, "has_gemini_api_key", _no_ai)
    ct.set_active_tree_override(ct.EMPTY_TREE)
    yield tmp_path
    ct.set_active_tree_override(None)


_seq = [0]


def mv(amount: float, d: str, category: str, description: str = "", **kw: Any) -> BankMovement:
    _seq[0] += 1
    return BankMovement(
        amount=amount, date=d, account_name=kw.pop("account_name", "בנק"),
        category=category, type=kw.pop("type", MovementType.ONE_TIME),
        description=description, id=kw.pop("id", f"m{_seq[0]}"), **kw,
    )


def row(m: BankMovement) -> Dict[str, Any]:
    d = asdict(m)
    d["type"] = m.type.value
    return d


def write_workspace(tmp: Path, movements: List[BankMovement], *, plans=(), assets=(),
                    outcome=OLD_OUTCOME) -> WorkspaceFiles:
    acc = tmp / "accounts"
    acc.mkdir(parents=True, exist_ok=True)
    files = WorkspaceFiles(accounts_dir=acc, key=KEY)
    JsonFileBankMovementProvider(files.movements).save_movements(list(movements))
    files.categories.write_text(json.dumps({"income": ["משכורת"], "outcome": list(outcome)},
                                           ensure_ascii=False), encoding="utf-8")
    from finance.data.installment_plan_provider import JsonFileInstallmentPlanProvider
    from finance.data.mortgage_provider import JsonFileMortgageProvider

    JsonFileInstallmentPlanProvider(files.plans).save_plans(list(plans))
    JsonFileMortgageProvider(files.mortgages).save_mortgages(list(assets))
    return files


def decisions_by_id(movements, **kw):
    plan = plan_migration([row(m) for m in movements],
                          categories_data={"outcome": OLD_OUTCOME}, **kw)
    return {d.movement_id: d for d in plan.decisions}, plan


class RecordingPusher(MigrationPusher):
    def __init__(self, fail: bool = False):
        self.calls: List[Dict[str, Any]] = []
        self.fail = fail

    def push(self, **kw) -> Pushed:
        if self.fail:
            raise OSError("offline")
        self.calls.append(kw)
        return Pushed(movements=len(kw["movements"]), plans=len(kw["plans"]),
                      mortgages=len(kw["mortgages"]), categories=1)


# ── tree model ────────────────────────────────────────────────────────────


def test_default_tree_has_target_structure_with_unique_names_and_stable_ids():
    tree = CategoryTree(default_outcome_nodes())
    parents = [n for n in tree.nodes if not n.parent_id]
    assert [p.name for p in parents] == [
        "מזון", "דיור וחשבונות", "ריהוט וציוד לבית", "רכב ותחבורה", "בריאות וטיפול",
        "ילדים וחינוך", "ביגוד וטיפוח", "פנאי ונופש", "תקשורת ושירותים דיגיטליים",
        "מתנות ותרומות", "עמלות וביטוחים נוספים", "לימודים", UNCLASSIFIED_NAME,
    ]
    assert tree.parent_of("סופר ומכולת").id == "food"
    assert tree.children_of(UNCLASSIFIED_NAME) == []
    # parent/child relationships use ids, not names
    assert all(n.parent_id in (None, "food", "housing", "home", "transport", "health", "kids",
                               "apparel", "leisure", "digital", "gifts", "fees",
                               "studies")
               for n in tree.nodes)


def test_tree_rejects_duplicate_names_and_three_levels():
    with pytest.raises(ValueError):
        CategoryTree([CategoryNode("a", "x"), CategoryNode("b", "x")])
    with pytest.raises(ValueError):
        CategoryTree([CategoryNode("a", "x"), CategoryNode("a.b", "y", "a"),
                      CategoryNode("a.b.c", "z", "a.b")])


def test_merge_and_retired_name_filter():
    local = default_outcome_nodes()
    remote = local + [CategoryNode("custom.zzz", "חיות מחמד")]
    merged = merge_tree_nodes(local, remote)
    assert merged[-1].name == "חיות מחמד"
    tree = CategoryTree(merged, {"קניות": UNCLASSIFIED_NAME})
    assert filter_retired_names(["קניות", "מזון", "מזון", "חיות מחמד"], tree) == ["מזון", "חיות מחמד"]
    assert tree.resolve_reference("קניות") == UNCLASSIFIED_NAME
    assert tree.resolve_reference("מזון") == "מזון"


# ── deterministic mapping ────────────────────────────────────────────────


@pytest.mark.parametrize("description,old,expected,kind", [
    ("שופרסל דיל רמלה", "קניות", "סופר ומכולת", MAPPED),
    ("רמי לוי - לוד", "קניות", "סופר ומכולת", MAPPED),
    ("גלי אל רהיטים בעמ", "קניות", "רהיטים", MAPPED),
    ("טיפול 10000", "רכב", "טיפולים ותיקונים", MAPPED),
    ("ארנונה 2023", "מגורים", "ארנונה", MAPPED),
    ("תשלום לצימר", "בילויים", "לינה וחופשות", MAPPED),
    # ambiguous merchants: parent at most, never a guessed subcategory
    ("איקאה IKEA", "קניות", "ריהוט וציוד לבית", PARENT_ONLY),
    ("buyme", "שונות", UNCLASSIFIED_NAME, UNCLASSIFIED),
    ("BIT", "שונות", UNCLASSIFIED_NAME, UNCLASSIFIED),
    ("PAYBOX", "בילויים", "פנאי ונופש", PARENT_ONLY),
    ("טיפול חן", "בריאות", "בריאות וטיפול", PARENT_ONLY),
    ("טיפול חן", "שונות", UNCLASSIFIED_NAME, UNCLASSIFIED),
    ("סופר פארם רמלוד", "בריאות", "בריאות וטיפול", PARENT_ONLY),
    ("פז YELLOW רמלה", "רכב", "רכב ותחבורה", PARENT_ONLY),
    # custom category with no equivalent is retained
    ("מועצה דתית", "דת", "דת", CUSTOM),
])
def test_mapping_examples(description, old, expected, kind):
    m = mv(-100, "2026-05-01", old, description)
    by_id, _ = decisions_by_id([m])
    d = by_id[m.id]
    assert (d.new_category, d.kind) == (expected, kind)


def test_rule_conflicting_with_users_category_is_flagged_not_applied():
    m = mv(-80, "2026-05-01", "רכב", "אושר עד לוד")  # grocery store under "car"
    d = decisions_by_id([m])[0][m.id]
    assert d.new_category == "רכב ותחבורה"
    assert d.review and "סופר ומכולת" in d.review


def test_keyword_boundaries_do_not_leak_into_other_words():
    assert match_rule("יעקוב חוגי שיווק פירות") is not None
    assert match_rule("יעקוב חוגי שיווק פירות").target == "food.grocery"  # not "חוג "
    assert match_rule("קטן") is None  # "טן " (TEN stations) needs a word boundary


def test_mapping_is_deterministic_and_independent_of_account():
    ms = [mv(-50, "2026-05-01", "קניות", "שופרסל", account_name=a)
          for a in ("בנק", "מזומן", "סיבוס", "ביט", "פייבוקס")]
    a, _ = decisions_by_id(ms)
    b, _ = decisions_by_id(list(reversed(ms)))
    assert {d.new_category for d in a.values()} == {"סופר ומכולת"}
    assert {k: v.new_category for k, v in a.items()} == {k: v.new_category for k, v in b.items()}


def test_transfers_income_and_links_are_preserved():
    transfer = mv(-500, "2026-05-01", "העברה", "העברה לחיסכון", is_transfer=True,
                  transfer_from="בנק", transfer_to="פיקדון -- א")
    income = mv(9000, "2026-05-01", "משכורת", "שכר")
    house = mv(-180000, "2026-05-02", "מגורים", "קניית דירה")
    lawyer = mv(-5000, "2026-05-03", "שונות", "עו״ד")
    tax = mv(-400, "2026-05-04", "מגורים", "עיריית לוד גזברות")
    mortgage_pay = mv(-5700, "2026-05-05", "מגורים", "תשלום משכנתא")
    event_dinner = mv(-300, "2026-05-06", "בילויים", "מסעדה", event_id="evt-1")
    asset = Mortgage(id="a1", name="דירה", vendor_query="תשלום משכנתא", account_name="בנק",
                     price_query="קניית דירה",
                     one_time_costs=[CostItem(name="עו\"ד", amount=1, query="עו״ד")],
                     monthly_costs=[CostItem(name="ארנונה", amount=0, query="עיריית לוד")])
    by_id, plan = decisions_by_id(
        [transfer, income, house, lawyer, tax, mortgage_pay, event_dinner], assets=[asset])
    assert by_id[transfer.id].kind == UNCHANGED and by_id[transfer.id].new_category == "העברה"
    assert by_id[income.id].kind == UNCHANGED
    assert by_id[house.id].kind == ASSET_ACQUISITION and by_id[house.id].new_category == "מגורים"
    assert by_id[lawyer.id].kind == ASSET_ACQUISITION
    assert by_id[tax.id].new_category == "ארנונה" and by_id[tax.id].reason == "asset_cost_item"
    assert by_id[mortgage_pay.id].new_category == "משכנתא"
    assert by_id[event_dinner.id].new_category == "אוכל בחוץ"
    # old names still referenced by acquisitions stay listed (not deleted)
    assert set(plan.retained_legacy) == {"מגורים", "שונות"}
    assert "מגורים" in plan.outcome_names and "מגורים" not in plan.tree.legacy_aliases
    assert plan.tree.legacy_aliases["רכב"] == "רכב ותחבורה"


def test_installment_plan_links_and_plan_category_are_migrated():
    plan_obj = InstallmentPlan(id="p1", name="‫ביטוח חובה - 2026‬",
                               vendor_query="ביטוח חובה", account_name="בנק",
                               start_date="2026-01-01", payments_count=12,
                               original_amount=1200, category="רכב")
    m = mv(-100, "2026-02-01", "רכב", "ביטוח חובה 2026")
    by_id, plan = decisions_by_id([m], plans=[plan_obj])
    assert by_id[m.id].new_category == "ביטוח רכב"
    assert [(c.old_value, c.new_value) for c in plan.plan_changes] == [("רכב", "ביטוח רכב")]


def test_relabel_for_training_examples():
    tree = CategoryTree(default_outcome_nodes())
    assert relabel("שופרסל", "קניות", tree) == "סופר ומכולת"
    assert relabel("BIT", "שונות", tree) is None
    assert relabel("x", "בריאות", tree) == "בריאות וטיפול"
    assert relabel("x", UNCLASSIFIED_NAME, tree) is None


# ── runner: integrity, idempotency, resume, rollback, single refresh ──────


def sample_movements() -> List[BankMovement]:
    out = []
    for acct in ("בנק", "מזומן", "סיבוס", "ביט", "פייבוקס"):
        out.append(mv(-55.5, "2026-04-02", "קניות", "רמי לוי", account_name=acct))
    out += [mv(-90, f"2026-0{i}-10", "רכב", "סונול סתריה") for i in range(1, 8)]
    out.append(mv(-300, "2026-03-01", "העברה", "העברה", is_transfer=True))
    out.append(mv(12000, "2026-03-01", "משכורת", "שכר"))
    return out


def test_apply_changes_only_categories_and_runs_one_refresh(tmp_path):
    ms = sample_movements()
    files = write_workspace(tmp_path, ms)
    before = json.loads(files.movements.read_text(encoding="utf-8"))
    refreshes, retrains = [], []
    pusher = RecordingPusher()
    report = CategoryMigrationRunner(files, pusher=pusher, refresh=lambda: refreshes.append(1),
                                     retrain=lambda: retrains.append(1)).apply()
    after = json.loads(files.movements.read_text(encoding="utf-8"))
    assert len(before) == len(after)
    for a, b in zip(before, after):
        assert {k: v for k, v in a.items() if k != "category"} == \
               {k: v for k, v in b.items() if k != "category"}
    assert sum(r["amount"] for r in before) == sum(r["amount"] for r in after)
    assert report.changed_movements == 12
    assert refreshes == [1] and retrains == [1]  # once, not per movement
    assert len(pusher.calls) == 1
    assert {m.id for m in pusher.calls[0]["movements"]} == {m.id for m in ms[:12]}
    assert pusher.calls[0]["tree"]  # hierarchy pushed with the lists
    cats = json.loads(files.categories.read_text(encoding="utf-8"))
    assert cats["schema_version"] == 2 and "קניות" not in cats["outcome"]
    assert cats["income"] == ["משכורת"]


def test_rerun_after_completion_writes_nothing(tmp_path):
    files = write_workspace(tmp_path, sample_movements())
    CategoryMigrationRunner(files).apply()
    stamps = {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")}
    refreshes = []
    report = CategoryMigrationRunner(files, refresh=lambda: refreshes.append(1)).apply()
    assert report.mode == "noop" and refreshes == []
    assert {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")} == stamps


def test_interrupted_push_is_resumed_without_reclassifying(tmp_path):
    ms = sample_movements()
    files = write_workspace(tmp_path, ms)
    with pytest.raises(OSError):
        CategoryMigrationRunner(files, pusher=RecordingPusher(fail=True)).apply()
    state = json.loads(files.state.read_text(encoding="utf-8"))
    assert state["status"] == "applied_local" and len(state["pending_push"]["movements"]) == 12
    pusher = RecordingPusher()
    report = CategoryMigrationRunner(files, pusher=pusher).apply()
    assert report.changed_movements == 0  # already applied locally
    assert len(pusher.calls[0]["movements"]) == 12  # but still pushed once
    assert json.loads(files.state.read_text(encoding="utf-8"))["status"] == "done"


def test_rollback_restores_original_and_keeps_later_user_edits(tmp_path):
    ms = sample_movements()
    files = write_workspace(tmp_path, ms)
    original = files.movements.read_bytes()
    original_cats = json.loads(files.categories.read_text(encoding="utf-8"))
    CategoryMigrationRunner(files).apply()
    rows = json.loads(files.movements.read_text(encoding="utf-8"))
    rows[0]["category"] = "אוכל בחוץ"  # user edit after the migration
    files.movements.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    pusher = RecordingPusher()
    report = CategoryMigrationRunner(files, pusher=pusher).rollback()
    assert report.skipped_user_edits == 1
    restored = json.loads(files.movements.read_text(encoding="utf-8"))
    assert restored[0]["category"] == "אוכל בחוץ"
    assert [r["category"] for r in restored[1:]] == \
           [r["category"] for r in json.loads(original)[1:]]
    cats = json.loads(files.categories.read_text(encoding="utf-8"))
    assert cats == original_cats
    assert pusher.calls[0]["clear_tree"] is True


def test_full_rollback_is_byte_identical(tmp_path):
    files = write_workspace(tmp_path, sample_movements())
    original = files.movements.read_bytes()
    CategoryMigrationRunner(files).apply()
    CategoryMigrationRunner(files).rollback()
    assert files.movements.read_bytes() == original


def test_user_handled_alerts_stay_closed_through_migration_refresh(tmp_path):
    ms = [mv(-a, f"{y:04d}-{m:02d}-{i + 1:02d}", "קניות", "שופרסל")
          for y, m in BASELINE for i, a in enumerate([40, 60, 80, 100])]
    big = mv(-2000, "2026-10-12", "קניות", "שופרסל")
    ms.append(big)
    files = write_workspace(tmp_path, ms)
    notes = JsonFileNotificationsProvider(files.path("notifications"))
    notes.upsert(Notification(
        id="n1", key=f"unexpected_expense:{big.id}", type=NotificationType.UNEXPECTED_EXPENSE,
        title="t", message="m", severity=NotificationSeverity.WARNING, created_at="2026-11-01",
        status=NotificationStatus.RESOLVED, closed_by=CLOSED_BY_USER))

    def refresh():
        NotificationsService(
            provider=notes,
            movement_provider=JsonFileBankMovementProvider(files.movements),
            installment_provider=_Empty(), mortgage_provider=_Empty(), event_provider=_Empty(),
            today=lambda: date(2026, 11, 5),
        ).refresh()

    CategoryMigrationRunner(files, refresh=refresh).apply()
    n = [x for x in notes.list_notifications() if x.key.endswith(big.id)]
    assert len(n) == 1 and n[0].status == NotificationStatus.RESOLVED
    assert n[0].closed_by == CLOSED_BY_USER


class _Empty:
    def list_plans(self):
        return []

    def list_mortgages(self):
        return []

    def list_events(self):
        return []


# ── persistence & sync ────────────────────────────────────────────────────


def test_provider_keeps_tree_when_flat_list_changes(tmp_path):
    p = JsonFileBankMovementProvider(tmp_path / f"bank_movements_{KEY}.json")
    tree = CategoryTree(default_outcome_nodes(), {"קניות": UNCLASSIFIED_NAME})
    p.save_category_tree(tree, outcome_names=tree.assignable_names())
    p.add_category_for_type("חיות מחמד", False)  # normal UI path
    loaded = p.load_category_tree()
    assert loaded.nodes == tree.nodes and loaded.legacy_aliases == tree.legacy_aliases
    assert "חיות מחמד" in p.list_categories_for_type(False)


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


def test_sync_merges_tree_drops_retired_names_and_pushes_hierarchy(tmp_path):
    from finance.models.firebase_sync_categories import sync_categories

    p = JsonFileBankMovementProvider(tmp_path / f"bank_movements_{KEY}.json")
    tree = CategoryTree(default_outcome_nodes(), {"קניות": UNCLASSIFIED_NAME})
    p.save_category_tree(tree, outcome_names=tree.assignable_names())
    # an older client still lists "קניות"; another added a custom node
    remote = {"income": ["משכורת"], "outcome": ["קניות", "מזון", "צעצועי חתול"],
              "outcome_tree": [n.to_dict() for n in tree.nodes]
              + [{"id": "custom.cat", "name": "חתולים", "parent_id": ""}]}
    fs = FakeFS(remote)
    sync_categories(fs=fs, workspace_id=KEY, uid="u", id_token="t", provider=p, allow_push=True)
    pushed = fs.patches[0]
    assert "קניות" not in pushed["outcome"]
    assert "צעצועי חתול" in pushed["outcome"] and "חתולים" in pushed["outcome"]
    assert any(n["name"] == "חתולים" for n in pushed["outcome_tree"])
    assert p.load_category_tree().by_name("חתולים") is not None
    assert "קניות" not in p.list_categories_for_type(False)


def test_sync_without_local_tree_never_writes_hierarchy_fields(tmp_path):
    from finance.models.firebase_sync_categories import sync_categories

    p = JsonFileBankMovementProvider(tmp_path / f"bank_movements_{KEY}.json")
    p.add_category_for_type("קניות", False)
    fs = FakeFS({"income": [], "outcome": ["קניות"]})
    sync_categories(fs=fs, workspace_id=KEY, uid="u", id_token="t", provider=p, allow_push=True)
    assert "outcome_tree" not in fs.patches[0]


# ── reports ───────────────────────────────────────────────────────────────


def test_reports_roll_descendants_into_parent_exactly_once():
    tree = CategoryTree(default_outcome_nodes())
    ct.set_active_tree_override(tree)
    ms = [mv(-100, "2026-05-01", "סופר ומכולת"), mv(-50, "2026-05-02", "מזון"),
          mv(-20, "2026-05-03", "אוכל בחוץ"), mv(-7, "2026-05-04", "דת"),
          mv(-1, "2026-05-05", "")]
    rows = {b.category: b for b in CategoryMonthlyBreakdown.breakdowns_for(ms, 2026, 5)}
    assert rows["מזון"].total_amount == 170 and rows["מזון"].movement_count == 3
    assert rows["דת"].total_amount == 7
    assert rows[UNCLASSIFIED_NAME].total_amount == 1
    assert sum(b.total_amount for b in rows.values()) == 178
    assert report_group("סופר ומכולת", tree) == "מזון"
    assert report_group("שם לא מוכר", tree) == "שם לא מוכר"


def test_asset_expense_category_resolves_retired_name_to_ownership_subcategories():
    from finance.models.asset_expense_service import expense_category_names

    ct.set_active_tree_override(CategoryTree(default_outcome_nodes(), {"רכב": "רכב ותחבורה"}))
    names = expense_category_names(Mortgage(id="c", name="car", expense_category=""))
    # The retired "רכב" resolves to the transport parent, which becomes its
    # car-ownership subcategories only — never public transport / taxis / rental.
    assert "דלק" in names and len(names) == len(set(names))
    assert "תחבורה ציבורית ומוניות" not in names and "השכרת רכב" not in names
    assert "רכב ותחבורה" not in names  # the broad parent is kept for review


# ── detector on the hierarchy ─────────────────────────────────────────────


def _hist(category: str, amounts, description="x"):
    return [mv(-a, f"{y:04d}-{m:02d}-{i + 3:02d}", category, f"{description}{i}")
            for y, m in BASELINE for i, a in enumerate(amounts)]


def test_subcategory_baseline_is_isolated_from_siblings_and_parent():
    ms = _hist("סופר ומכולת", [40, 60, 80, 100]) + _hist("אוכל בחוץ", [400])
    ms += _hist("מזון", [10, 12])  # parent-only history
    cand = mv(-700, "2026-10-10", "סופר ומכולת", "שופרסל")
    rest = mv(-700, "2026-10-11", "אוכל בחוץ", "מסעדה")
    d = {x.movement_id: x for x in evaluate_month(ms + [cand, rest], evaluated_month=EVAL)}
    assert d[cand.id].outcome == Outcome.ALERT
    assert d[cand.id].baseline.count == 24  # only its own subcategory
    assert d[rest.id].outcome == Outcome.INSUFFICIENT_HISTORY  # 6 rows: no sibling borrowing


def test_parent_only_compared_with_parent_only_and_no_fallback_to_parent():
    ms = _hist("מזון", [10, 12, 14, 16]) + _hist("סופר ומכולת", [1000, 1100, 1200, 1300])
    parent_cand = mv(-500, "2026-10-10", "מזון", "מאפיה")
    sparse = mv(-500, "2026-10-11", "אוכל בחוץ", "קפה")  # no history of its own
    d = {x.movement_id: x for x in evaluate_month(ms + [parent_cand, sparse], evaluated_month=EVAL)}
    assert d[parent_cand.id].outcome == Outcome.ALERT
    assert d[parent_cand.id].baseline.count == 24
    assert d[sparse.id].outcome == Outcome.INSUFFICIENT_HISTORY


def test_unclassified_gets_no_statistical_decision_but_increase_check_still_works():
    ms = _hist(UNCLASSIFIED_NAME, [40, 60, 80, 100])
    odd = mv(-5000, "2026-10-10", UNCLASSIFIED_NAME, "BIT")
    ms += [mv(-3600, f"2026-{m:02d}-01", UNCLASSIFIED_NAME, "העברה חודשית") for m in range(4, 10)]
    rise = mv(-4200, "2026-10-01", UNCLASSIFIED_NAME, "העברה חודשית")
    d = {x.movement_id: x for x in evaluate_month(ms + [odd, rise], evaluated_month=EVAL)}
    assert d[odd.id].outcome == Outcome.UNCLASSIFIED and not d[odd.id].is_alert
    assert d[rise.id].outcome == Outcome.RECURRING_INCREASE and d[rise.id].is_alert


def test_shared_index_gives_identical_decisions():
    ms = _hist("סופר ומכולת", [40, 60, 80, 100]) + [mv(-700, "2026-10-10", "סופר ומכולת", "a")]
    idx = DetectionIndex(ms)
    for ym in [(2026, 9), (2026, 10)]:
        a = evaluate_month(ms, evaluated_month=ym)
        b = evaluate_month(ms, evaluated_month=ym, index=idx)
        assert [(x.movement_id, x.outcome, x.threshold) for x in a] == \
               [(x.movement_id, x.outcome, x.threshold) for x in b]


# ── unique-description recategorization (settings window model) ───────────


def test_descriptions_grouped_by_normalized_text_expenses_only():
    from finance.models.description_categories import group_expense_descriptions

    ms = [
        mv(-100, "2026-05-01", "סופר ומכולת", "שופרסל דיל"),
        mv(-50, "2026-05-09", "מזון", "  שופרסל   דיל "),  # same payee, other spelling
        mv(-30, "2026-05-03", UNCLASSIFIED_NAME, "BIT"),
        mv(500, "2026-05-04", "משכורת", "שופרסל דיל"),  # income: ignored
        mv(-900, "2026-05-05", "העברה", "העברה", is_transfer=True),  # transfer: ignored
    ]
    groups = {g.description.strip(): g for g in group_expense_descriptions(ms)}
    g = groups["שופרסל דיל"]
    assert g.count == 2 and g.total == 150 and g.last_date == "2026-05-09"
    assert g.is_mixed and g.main_category in ("סופר ומכולת", "מזון")
    assert groups["BIT"].is_unclassified()
    assert "העברה" not in groups


def test_apply_description_categories_changes_only_category_of_expenses():
    from finance.models.description_categories import (
        apply_description_categories,
        description_key,
    )

    a = mv(-100, "2026-05-01", UNCLASSIFIED_NAME, "פינת הנשיא לוד", event_id="e1")
    b = mv(-20, "2026-06-01", "מזון", "פינת  הנשיא לוד")
    inc = mv(40, "2026-06-02", "החזר", "פינת הנשיא לוד")
    other = mv(-5, "2026-06-03", UNCLASSIFIED_NAME, "BIT")
    out, changed = apply_description_categories(
        [a, b, inc, other], {description_key("פינת הנשיא לוד"): "סופר ומכולת"})
    assert [m.id for m in changed] == [a.id, b.id]
    by_id = {m.id: m for m in out}
    assert by_id[a.id].category == "סופר ומכולת" and by_id[a.id].event_id == "e1"
    assert by_id[a.id].amount == a.amount and by_id[a.id].date == a.date
    assert by_id[inc.id].category == "החזר" and by_id[other.id].category == UNCLASSIFIED_NAME


def test_category_choices_tree_order_without_retired_or_transfer():
    from finance.models.description_categories import category_choices

    tree = CategoryTree(default_outcome_nodes() + [CategoryNode("custom.x", "דת")],
                        {"קניות": UNCLASSIFIED_NAME})
    choices = category_choices(tree, ["קניות", "העברה", "שונות", "דת"])
    names = [n for _l, n in choices]
    assert names[:4] == ["מזון", "סופר ומכולת", "אוכל בחוץ", "דיור וחשבונות"]
    assert dict(choices)["    סופר ומכולת"] == "סופר ומכולת"  # indented subcategory
    assert "קניות" not in names and "העברה" not in names
    assert "שונות" in names and names.count("דת") == 1


# ── structure edits (rename / merge / add) ────────────────────────────────


def _old_structure_tree() -> CategoryTree:
    """The hierarchy as the first migration created it (before the edit)."""
    nodes = []
    for n in default_outcome_nodes():
        if n.id in ("transport.rental", "apparel.jewelry", "studies"):
            continue
        if n.id == "food.restaurants":
            nodes += [CategoryNode(n.id, "מסעדות ומשלוחים", n.parent_id),
                      CategoryNode("food.cafes", "בתי קפה", "food")]
        elif n.id == "kids.gear":
            nodes += [CategoryNode(n.id, "ציוד וצעצועים", n.parent_id),
                      CategoryNode("kids.baby", "מוצרי תינוקות", "kids")]
        else:
            nodes.append(n)
    return CategoryTree(nodes, {"קניות": UNCLASSIFIED_NAME})



def _user_edit():
    from finance.models.category_edits import CategoryEdit

    return CategoryEdit(
        merges={"food.cafes": "food.restaurants", "kids.baby": "kids.gear"},
        renames={"food.restaurants": "אוכל בחוץ", "kids.gear": "ציוד ומוצרי ילדים"},
        additions=[CategoryNode("transport.rental", "השכרת רכב", "transport"),
                   CategoryNode("apparel.jewelry", "תכשיטים", "apparel"),
                   CategoryNode("studies", "לימודים", None)],
    )


def test_plan_category_edit_merges_renames_and_adds_in_place():
    from finance.models.category_edits import plan_category_edit

    new, name_map = plan_category_edit(_old_structure_tree(), _user_edit())
    assert name_map == {"מסעדות ומשלוחים": "אוכל בחוץ", "בתי קפה": "אוכל בחוץ",
                        "ציוד וצעצועים": "ציוד ומוצרי ילדים",
                        "מוצרי תינוקות": "ציוד ומוצרי ילדים"}
    assert [c.name for c in new.children_of("מזון")] == ["סופר ומכולת", "אוכל בחוץ"]
    assert new.children_of("רכב ותחבורה")[-1].name == "השכרת רכב"
    assert new.children_of("ביגוד וטיפוח")[-1].name == "תכשיטים"
    tops = [n.name for n in new.nodes if not n.parent_id]
    assert tops.index("לימודים") == tops.index(UNCLASSIFIED_NAME) - 1
    assert new.by_name("אוכל בחוץ").id == "food.restaurants"  # id kept
    assert new.legacy_aliases["בתי קפה"] == "אוכל בחוץ"
    assert new.legacy_aliases["קניות"] == UNCLASSIFIED_NAME
    # the edited tree matches the current default structure
    assert [(n.id, n.name, n.parent_id) for n in new.nodes] == \
           [(n.id, n.name, n.parent_id) for n in default_outcome_nodes()]


def test_apply_category_edit_moves_movements_once_and_is_idempotent(tmp_path):
    from finance.models.category_edits import apply_category_edit

    ms = [mv(-30, "2026-05-01", "בתי קפה", "קפה"), mv(-90, "2026-05-02", "מסעדות ומשלוחים", "פיצה"),
          mv(-40, "2026-05-03", "מוצרי תינוקות", "מטרנה"), mv(-50, "2026-05-04", "סופר ומכולת", "שופרסל"),
          mv(-300, "2026-05-05", "העברה", "העברה", is_transfer=True)]
    files = write_workspace(tmp_path, ms)
    tree = _old_structure_tree()
    files.categories.write_text(json.dumps({
        "income": [], "outcome": tree.assignable_names() + ["העברה"],
        "outcome_tree": tree.nodes_to_list(), "legacy_aliases": tree.legacy_aliases,
        "schema_version": 2}, ensure_ascii=False), encoding="utf-8")
    before = json.loads(files.movements.read_text(encoding="utf-8"))
    pusher, refreshes = RecordingPusher(), []
    rep = apply_category_edit(files, _user_edit(), pusher=pusher,
                              refresh=lambda: refreshes.append(1))
    after = json.loads(files.movements.read_text(encoding="utf-8"))
    assert [r["category"] for r in after] == ["אוכל בחוץ", "אוכל בחוץ", "ציוד ומוצרי ילדים",
                                              "סופר ומכולת", "העברה"]
    for a, b in zip(before, after):
        assert {k: v for k, v in a.items() if k != "category"} == \
               {k: v for k, v in b.items() if k != "category"}
    assert rep.changed_movements == 3 and refreshes == [1]
    assert {m.id for m in pusher.calls[0]["movements"]} == {ms[0].id, ms[1].id, ms[2].id}
    cats = json.loads(files.categories.read_text(encoding="utf-8"))
    assert "בתי קפה" not in cats["outcome"] and "לימודים" in cats["outcome"]
    assert "העברה" in cats["outcome"]
    stamps = {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")}
    again = apply_category_edit(files, _user_edit(), pusher=RecordingPusher())
    assert again.mode == "noop"
    assert {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")} == stamps


def test_structure_edit_maps_selected_car_categories(tmp_path):
    from finance.data.mortgage_provider import serialize_mortgage
    from finance.models.category_edits import apply_category_edit
    from finance.models.mortgage import AssetKind

    files = write_workspace(tmp_path, [mv(-30, "2026-05-01", "בתי קפה", "קפה")])
    tree = _old_structure_tree()
    files.categories.write_text(json.dumps({
        "income": [], "outcome": tree.assignable_names(),
        "outcome_tree": tree.nodes_to_list(), "legacy_aliases": tree.legacy_aliases,
        "schema_version": 2}, ensure_ascii=False), encoding="utf-8")
    car = Mortgage(id="car", name="car", kind=AssetKind.CAR,
                   expense_categories=["בתי קפה", "מסעדות ומשלוחים", "דלק"])
    files.mortgages.write_text(json.dumps([serialize_mortgage(car)], ensure_ascii=False),
                               encoding="utf-8")
    apply_category_edit(files, _user_edit(), pusher=RecordingPusher())
    saved = json.loads(files.mortgages.read_text(encoding="utf-8"))[0]
    # two merged names become one entry; the untouched name stays
    assert saved["expense_categories"] == ["אוכל בחוץ", "דלק"]


# ── reviewed per-movement corrections ─────────────────────────────────────


def _review_workspace(tmp_path):
    ms = [mv(-329.52, "2025-06-04", "רכב ותחבורה", "אושר עד לוד", id="osher"),
          mv(-18, "2026-05-29", "רכב ותחבורה", "הקפה של משה", id="cafe"),
          mv(-290.08, "2025-07-19", "רכב ותחבורה", "פז YELLOW רמלה", id="yellow"),
          mv(-31500, "2024-10-20", "רכב ותחבורה", "קניית רכב", id="purchase"),
          mv(-50, "2026-05-01", "סופר ומכולת", "שופרסל", id="other")]
    files = write_workspace(tmp_path, ms)
    tree = CategoryTree(default_outcome_nodes(), {"בתי קפה": "אוכל בחוץ"})
    files.categories.write_text(json.dumps({
        "income": [], "outcome": tree.assignable_names(),
        "outcome_tree": tree.nodes_to_list(), "legacy_aliases": tree.legacy_aliases,
        "schema_version": 2}, ensure_ascii=False), encoding="utf-8")
    return files


def _fixes():
    from finance.models.category_edits import MovementCorrection

    return [MovementCorrection("osher", "רכב ותחבורה", "סופר ומכולת", "supermarket"),
            MovementCorrection("cafe", "רכב ותחבורה", "אוכל בחוץ", "café")]


def test_corrections_change_only_listed_categories_and_are_idempotent(tmp_path):
    from finance.models.category_edits import apply_movement_corrections

    files = _review_workspace(tmp_path)
    before = {r["id"]: r for r in json.loads(files.movements.read_text(encoding="utf-8"))}
    pusher, refreshes = RecordingPusher(), []
    rep = apply_movement_corrections(files, _fixes(), pusher=pusher,
                                     refresh=lambda: refreshes.append(1))
    after = {r["id"]: r for r in json.loads(files.movements.read_text(encoding="utf-8"))}
    assert rep.changed == ["osher", "cafe"] and refreshes == [1]
    assert after["osher"]["category"] == "סופר ומכולת" and after["cafe"]["category"] == "אוכל בחוץ"
    for mid in before:  # nothing else on any record changed
        diff = {k for k in before[mid] if before[mid][k] != after[mid].get(k)}
        assert diff <= ({"category"} if mid in ("osher", "cafe") else set())
    assert after["yellow"]["category"] == "רכב ותחבורה"  # ambiguous: untouched
    assert after["purchase"]["category"] == "רכב ותחבורה"
    assert {m.id for m in pusher.calls[0]["movements"]} == {"osher", "cafe"}
    assert rep.backup_dir and (Path(rep.backup_dir) / files.movements.name).exists()
    stamps = {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")}
    again = apply_movement_corrections(files, _fixes(), pusher=RecordingPusher())
    assert again.mode == "noop" and set(again.already) == {"osher", "cafe"}
    assert {p: p.stat().st_mtime_ns for p in files.accounts_dir.glob("*.json")} == stamps


def test_corrections_skip_records_changed_since_review_and_refuse_bad_targets(tmp_path):
    from finance.models.category_edits import MovementCorrection, apply_movement_corrections

    files = _review_workspace(tmp_path)
    rows = json.loads(files.movements.read_text(encoding="utf-8"))
    for r in rows:
        if r["id"] == "osher":
            r["category"] = "מתנות"  # the user changed it after the review
    files.movements.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    rep = apply_movement_corrections(files, _fixes(), pusher=RecordingPusher())
    assert rep.conflicts == {"osher": "מתנות"} and rep.changed == ["cafe"]
    with pytest.raises(ValueError):  # a retired name is never written
        apply_movement_corrections(files, [MovementCorrection("cafe", "אוכל בחוץ", "בתי קפה")])
    with pytest.raises(ValueError):
        apply_movement_corrections(files, [MovementCorrection("cafe", "אוכל בחוץ", "לא קיים")])
