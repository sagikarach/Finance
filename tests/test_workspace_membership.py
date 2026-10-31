from typing import Any

import pytest

from finance.models import firebase_workspace_membership as m


class FakeFs:
    def __init__(self, docs):
        self.docs = dict(docs)
        self.writes = []

    def get_document(self, *, document_path, id_token):
        if document_path in self.docs:
            return {"name": f"projects/p/databases/(default)/documents/{document_path}"}
        raise RuntimeError("NOT_FOUND: Document not found")

    def upsert_document(self, *, document_path, id_token, fields):
        self.writes.append((document_path, dict(fields)))
        self.docs[document_path] = fields


def _ensure(fs: Any, uid: str) -> None:
    m.ensure_workspace_membership(fs=fs, project_id="p", workspace_id="W", uid=uid, id_token="t")


@pytest.fixture(autouse=True)
def _clear_cache():
    m._VERIFIED.clear()


def test_existing_member_writes_nothing():
    fs = FakeFs({"workspaces/W/members/u1": {}})
    _ensure(fs, "u1")
    assert fs.writes == []


def test_join_existing_workspace_as_editor_without_touching_creator():
    fs = FakeFs({"workspaces/W": {"created_by": "owner"}})
    _ensure(fs, "u2")
    assert [w[0] for w in fs.writes] == ["workspaces/W/members/u2"]
    assert fs.writes[0][1]["role"] == "editor"


def test_new_workspace_member_doc_first_then_owner_workspace():
    fs = FakeFs({})
    _ensure(fs, "u1")
    assert [w[0] for w in fs.writes] == ["workspaces/W/members/u1", "workspaces/W"]
    assert fs.writes[0][1]["role"] == "owner"
    assert fs.writes[1][1]["created_by"] == "u1"


def test_permission_denied_propagates():
    class Denied(FakeFs):
        def get_document(self, *, document_path, id_token):
            raise RuntimeError("PERMISSION_DENIED: Missing or insufficient permissions.")

    with pytest.raises(RuntimeError, match="PERMISSION_DENIED"):
        _ensure(Denied({}), "u1")
