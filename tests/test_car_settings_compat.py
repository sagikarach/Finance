"""The car's category selection survives local persistence, Firebase
round-trips and an older desktop replacing the whole car document."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Dict, List

import pytest

from finance.data import mortgage_provider as mp
from finance.data.mortgage_provider import (
    JsonFileMortgageProvider,
    deserialize_mortgage,
    serialize_mortgage,
)
from finance.models.firebase_client import FirestoreClient
from finance.models.firebase_sync_workspace_cache import pull_mortgages_to_local_cache
from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter
from finance.models.mortgage import AssetKind, Mortgage

CAR = Mortgage(id="car1", name="i35", kind=AssetKind.CAR, property_price=31500.0)


class FakeFirestore:
    """Documents by path; ``upsert_document`` replaces (what older desktops
    do), ``patch_document_fields`` merges only the masked fields."""

    def __init__(self) -> None:
        self.docs: Dict[str, Dict[str, Any]] = {}
        self.calls: List[str] = []
        self._codec = FirestoreClient(project_id="test")

    def upsert_document(self, *, document_path, id_token, fields):
        self.calls.append("replace")
        self.docs[document_path] = json.loads(json.dumps(fields))

    def patch_document_fields(self, *, document_path, id_token, fields):
        self.calls.append("patch:" + ",".join(sorted(fields)))
        self.docs.setdefault(document_path, {}).update(json.loads(json.dumps(fields)))

    def list_collection(self, *, collection_path, id_token, page_size=1000):
        from finance.models.firebase_client import _fs_value

        return [
            {"name": f"projects/test/databases/(default)/documents/{p}",
             "fields": {k: _fs_value(v) for k, v in d.items()}}
            for p, d in self.docs.items() if p.startswith(collection_path + "/")
        ]

    def parse_any_doc(self, doc):
        return self._codec.parse_any_doc(doc)


@pytest.fixture
def fs(monkeypatch, tmp_path):
    fake = FakeFirestore()
    session = type("S", (), {"project_id": "test", "id_token": "t", "workspace_id": "W"})()
    monkeypatch.setattr(FirebaseWorkspaceWriter, "_load_session_refresh_if_needed", lambda self: session)
    monkeypatch.setattr(FirebaseWorkspaceWriter, "_ensure_workspace", lambda self, s: "W")
    monkeypatch.setattr(FirebaseWorkspaceWriter, "_fs", lambda self, pid: fake)
    path = tmp_path / "mortgages.json"
    monkeypatch.setattr(mp, "JsonFileMortgageProvider", lambda *a, **k: JsonFileMortgageProvider(path))
    return fake


def _writer() -> FirebaseWorkspaceWriter:
    return FirebaseWorkspaceWriter.__new__(FirebaseWorkspaceWriter)


def _old_client_write(fake: FakeFirestore, car: Mortgage) -> None:
    """What desktop ≤ 1.2.37 does: the whole document, without the field."""
    fields = serialize_mortgage(car)
    fields.pop("expense_categories", None)
    fake.upsert_document(document_path=f"workspaces/W/mortgages/{car.id}", id_token="t",
                         fields={**fields, "deleted": False})


def _pull(fake: FakeFirestore) -> Mortgage:
    pull_mortgages_to_local_cache(fs=fake, workspace_id="W", id_token="t")
    return mp.JsonFileMortgageProvider().list_mortgages()[0]


def test_local_file_keeps_missing_empty_and_chosen_apart(tmp_path):
    p = JsonFileMortgageProvider(tmp_path / "m.json")
    p.save_mortgages([CAR, replace(CAR, id="c2", expense_categories=[]),
                      replace(CAR, id="c3", expense_categories=["דלק"])])
    raw = {r["id"]: r for r in json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))}
    assert "expense_categories" not in raw["car1"]  # never chosen: no key
    assert raw["c2"]["expense_categories"] == []
    loaded = {m.id: m.expense_categories for m in p.list_mortgages()}
    assert loaded == {"car1": None, "c2": [], "c3": ["דלק"]}


def test_firebase_round_trip_uses_a_field_mask(fs):
    chosen = replace(CAR, expense_categories=["דלק", "חניה וכבישי אגרה"])
    _writer().upsert_mortgage(chosen)
    assert fs.calls[-1].startswith("patch:") and "expense_categories" in fs.calls[-1]
    assert _pull(fs).expense_categories == ["דלק", "חניה וכבישי אגרה"]
    _writer().upsert_mortgage(replace(CAR, expense_categories=[]))  # deliberately none
    assert _pull(fs).expense_categories == []


def test_a_client_without_a_selection_does_not_erase_the_servers(fs):
    _writer().upsert_mortgage(replace(CAR, expense_categories=["דלק"]))
    _writer().upsert_mortgage(CAR)  # selection never chosen on this device
    assert "expense_categories" not in fs.calls[-1]
    assert fs.docs["workspaces/W/mortgages/car1"]["expense_categories"] == ["דלק"]


def test_old_client_overwrite_is_survived_and_repaired_by_the_next_push(fs):
    chosen = replace(CAR, expense_categories=["דלק"])
    mp.JsonFileMortgageProvider().save_mortgages([chosen])
    _writer().upsert_mortgage(chosen)
    _old_client_write(fs, replace(chosen, name="i35 (renamed on old desktop)"))
    assert "expense_categories" not in fs.docs["workspaces/W/mortgages/car1"]  # erased there
    local = _pull(fs)
    assert local.name == "i35 (renamed on old desktop)"  # the old client's edit is taken
    assert local.expense_categories == ["דלק"]  # the selection is kept locally
    _writer().upsert_mortgage(local)  # next push writes it back
    assert fs.docs["workspaces/W/mortgages/car1"]["expense_categories"] == ["דלק"]


def test_server_value_wins_when_present_even_if_empty(fs):
    mp.JsonFileMortgageProvider().save_mortgages([replace(CAR, expense_categories=["דלק"])])
    _writer().upsert_mortgage(replace(CAR, expense_categories=[]))
    assert _pull(fs).expense_categories == []


def test_record_never_chosen_stays_unset_after_pull(fs):
    mp.JsonFileMortgageProvider().save_mortgages([CAR])
    _old_client_write(fs, CAR)
    assert _pull(fs).expense_categories is None
    assert deserialize_mortgage(serialize_mortgage(CAR)).expense_categories is None
