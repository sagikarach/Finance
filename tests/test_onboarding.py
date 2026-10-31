"""New-user flow: sign up / log in and everything else is automatic."""

from types import SimpleNamespace

import pytest

import finance.models.firebase_login_service as ls
import finance.models.firebase_workspace_membership as m
import finance.utils.app_paths as ap
from finance.models.firebase_session import FirebaseSessionStore
from finance.models.firebase_workspace_profiles import FirebaseWorkspaceProfilesStore


class FakeAuth:
    created: list = []

    def __init__(self, *, api_key):
        pass

    def sign_up_with_password(self, *, email, password):
        FakeAuth.created.append(email)
        return SimpleNamespace(uid="newuid", id_token="t", refresh_token="r", expires_in=3600)

    def sign_in_with_password(self, *, email, password):
        return SimpleNamespace(uid="olduid", id_token="t", refresh_token="r", expires_in=3600)


class FakeFs:
    docs: dict = {}

    def __init__(self, *, project_id=""):
        pass

    def get_document(self, *, document_path, id_token):
        if document_path in FakeFs.docs:
            return {"name": document_path, "fields": FakeFs.docs[document_path]}
        raise RuntimeError("NOT_FOUND")

    def upsert_document(self, *, document_path, id_token, fields):
        FakeFs.docs[document_path] = dict(fields)

    def patch_document_fields(self, *, document_path, id_token, fields):
        FakeFs.docs.setdefault(document_path, {}).update(fields)

    @staticmethod
    def parse_any_doc(doc):
        return doc["name"], doc["fields"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(ls, "FirebaseAuthClient", FakeAuth)
    monkeypatch.setattr(ls, "FirestoreClient", FakeFs)
    monkeypatch.setattr(ls, "DEFAULT_API_KEY", "test-key")
    monkeypatch.setattr(ls, "DEFAULT_PROJECT_ID", "test-project")
    FakeFs.docs = {}
    m._VERIFIED.clear()
    return tmp_path


def _svc():
    return ls.FirebaseLoginService(session_store=FirebaseSessionStore())


def test_sign_up_creates_private_budget_automatically(env):
    res = _svc().sign_in_or_up(email="new@x.com", password="secret1", create_account=True)
    wid = res.session.workspace_id
    assert res.created_workspace and not res.joined_workspace
    assert len(wid) == 14 and wid.count("-") == 2
    assert FakeFs.docs[f"workspaces/{wid}/members/newuid"]["role"] == "owner"
    assert FakeFs.docs[f"workspaces/{wid}"]["created_by"] == "newuid"
    assert FakeFs.docs["users/newuid"]["active_workspace_id"] == wid  # mobile opens it too
    assert FirebaseSessionStore().load().is_logged_in


def test_log_in_reopens_last_budget_instead_of_creating(env):
    FakeFs.docs = {"users/olduid": {"active_workspace_id": "AAAA-BBBB-CCCC"},
                   "workspaces/AAAA-BBBB-CCCC": {"created_by": "olduid"},
                   "workspaces/AAAA-BBBB-CCCC/members/olduid": {"role": "owner"}}
    res = _svc().sign_in_or_up(email="o@x.com", password="pw", create_account=False)
    assert res.session.workspace_id == "AAAA-BBBB-CCCC" and not res.created_workspace


def test_log_in_falls_back_to_budget_used_on_this_computer(env):
    FakeFs.docs = {"workspaces/LOCL-WORK-SPCE": {"created_by": "olduid"}}
    FirebaseWorkspaceProfilesStore().upsert(name="me", workspace_id="LOCL-WORK-SPCE", email="o@x.com")
    res = _svc().sign_in_or_up(email="O@x.com", password="pw", create_account=False)
    assert res.session.workspace_id == "LOCL-WORK-SPCE" and not res.created_workspace


def test_share_code_joins_partner_budget(env):
    FakeFs.docs = {"workspaces/PART-NER0-CODE": {"created_by": "partner"}}
    res = _svc().sign_in_or_up(
        email="new@x.com", password="pw", create_account=True, share_code=" part-ner0-code "
    )
    assert res.joined_workspace and res.session.workspace_id == "PART-NER0-CODE"
    assert FakeFs.docs["workspaces/PART-NER0-CODE/members/newuid"]["role"] == "editor"


def test_mistyped_share_code_fails_instead_of_making_empty_budget(env):
    with pytest.raises(RuntimeError, match="קוד השיתוף לא נמצא"):
        _svc().sign_in_or_up(email="n@x.com", password="pw", create_account=True, share_code="NOPE")
    assert not FirebaseSessionStore().load().is_logged_in


def test_logged_out_data_goes_only_to_first_account(env):
    local = env / "users" / "_local" / "accounts"
    local.mkdir(parents=True)
    (local / "bank_movements.json").write_text('[{"id": "1"}]', encoding="utf-8")
    _svc().sign_in_or_up(email="first@x.com", password="pw", create_account=True)
    wid = FirebaseSessionStore().load().workspace_id
    assert ap.import_logged_out_data(workspace_id=wid) == 1
    assert (ap.accounts_data_dir() / f"bank_movements_{wid}.json").exists()

    FirebaseWorkspaceProfilesStore().upsert_recent(workspace_id=wid, email="first@x.com")
    _svc().sign_in_or_up(email="second@x.com", password="pw", create_account=True)
    wid2 = FirebaseSessionStore().load().workspace_id
    assert ap.import_logged_out_data(workspace_id=wid2) == 0
