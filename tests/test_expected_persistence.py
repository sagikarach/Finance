"""The expected marker and plan link survive local files, Firebase writes and
pulls (incl. a document rewritten by an older desktop), and the service
changes nothing else on the movement."""

from __future__ import annotations

from dataclasses import asdict, replace

from finance.data.action_history_provider import JsonFileActionHistoryProvider
from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.models.bank_movement import BankMovement, MovementType, deserialize_bank_movement
from finance.models.bank_movement_service import BankMovementService
from finance.models.firebase_client import FirestoreClient, _fs_value
from finance.models.firebase_sync_pullers import merge_remote_into_local
from finance.models.firebase_workspace_writer import movement_expectation_fields
from finance.models.installment_plan import KIND_DIRECT_DEBIT, InstallmentPlan

FEE = BankMovement(amount=-574.0, date="2026-08-09", account_name="בנק",
                   category="עמלות בנק וכרטיס", type=MovementType.ONE_TIME,
                   description="עמלת פתיחת חשבון", id="fee")
PLAN = InstallmentPlan(id="gan", name="גן", kind=KIND_DIRECT_DEBIT, monthly_amount=4293.9,
                       start_date="2025-09-01", charge_day=1, payments_count=12, auto_post=False)


def _remote(fields: dict) -> dict:
    """What a pull hands to the merge: Firestore-decoded fields."""
    doc = {"name": "projects/p/databases/(default)/documents/w/m/x",
           "fields": {k: _fs_value(v) for k, v in fields.items()}}
    return FirestoreClient(project_id="p").parse_any_doc(doc)[1]


def _doc(m: BankMovement) -> dict:
    d = asdict(m)
    d["type"] = m.type.value
    return d


def test_local_file_round_trip(tmp_path):
    p = JsonFileBankMovementProvider(tmp_path / "bank_movements.json")
    linked = replace(FEE, id="g", expected=True, plan_id="gan", plan_occurrence=4)
    p.save_movements([FEE, linked])
    got = {m.id: m for m in p.list_movements()}
    assert got["fee"] == FEE and got["g"] == linked
    old_row = {k: v for k, v in _doc(FEE).items() if k not in ("expected", "plan_id", "plan_occurrence")}
    assert deserialize_bank_movement(old_row) == FEE  # older files load unchanged


def test_firebase_round_trip_and_explicit_undo():
    marked = replace(FEE, expected=True, plan_id="gan", plan_occurrence=4)
    fields = {**_doc(marked), **movement_expectation_fields(marked)}
    back = deserialize_bank_movement(_remote(fields))
    assert (back.expected, back.plan_id, back.plan_occurrence) == (True, "gan", 4)
    undone = movement_expectation_fields(FEE)
    assert undone == {"expected": False, "plan_id": None, "plan_occurrence": None}
    local = {"fee": marked}
    merge_remote_into_local(remote_by_id={"fee": _remote({**_doc(FEE), **undone})}, local_by_id=local)
    assert (local["fee"].expected, local["fee"].plan_id) == (False, None)  # undo wins


def test_old_client_rewrite_keeps_the_local_marker():
    marked = replace(FEE, expected=True, plan_id="gan", plan_occurrence=4)
    old_doc = {k: v for k, v in _doc(FEE).items() if k not in ("expected", "plan_id", "plan_occurrence")}
    old_doc["category"] = "עמלות"  # the old client changed something else
    local = {"fee": marked}
    merge_remote_into_local(remote_by_id={"fee": _remote(old_doc)}, local_by_id=local)
    assert local["fee"].category == "עמלות"
    assert (local["fee"].expected, local["fee"].plan_id, local["fee"].plan_occurrence) == (True, "gan", 4)


def test_service_changes_only_the_expectation_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "data"))
    p = JsonFileBankMovementProvider(tmp_path / "bank_movements.json")
    other = replace(FEE, id="other", amount=-20.0)
    pay = replace(FEE, id="pay", amount=-4293.9, date="2026-01-07", category="גן ומסגרות")
    p.save_movements([FEE, other, pay])
    svc = BankMovementService(p, JsonFileActionHistoryProvider(tmp_path / "h.json"))
    assert svc.update_expectation("fee", expected=True).expected is True
    assert svc.update_expectation("fee", expected=True) is None  # no change → no write
    linked = svc.update_expectation("pay", plan=PLAN)
    assert (linked.plan_id, linked.plan_occurrence) == ("gan", 5)  # Jan 2026 = payment 5
    got = {m.id: m for m in p.list_movements()}
    assert got["fee"] == replace(FEE, expected=True)
    assert got["pay"] == replace(pay, plan_id="gan", plan_occurrence=5)
    assert got["other"] == other
    svc.update_expectation("fee", expected=False)
    svc.update_expectation("pay", plan=None)
    assert {m.id: m for m in p.list_movements()} == {"fee": FEE, "other": other, "pay": pay}
