"""Pull-side sync logic against a fake Firestore client — no network.

`merge_remote_into_local` is the heart of a pull (add/update/tombstone), and
`pull_remote_movements` picks the right query path and shapes docs into
(ids, by_id). A small in-memory FakeFirestoreClient stands in for the real one."""

from finance.models.bank_movement import BankMovement, MovementType
from finance.models.firebase_sync_pullers import (
    merge_remote_into_local,
    pull_remote_movements,
)


def _fields(amount, date, account="בנק", **extra):
    d = {
        "amount": amount,
        "date": date,
        "account_name": account,
        "category": "מזון",
        "type": "חד פעמי",
    }
    d.update(extra)
    return d


def _mv(mid, amount, date, account="בנק"):
    return BankMovement(
        amount=amount, date=date, account_name=account, category="מזון",
        type=MovementType.ONE_TIME, id=mid,
    )


# ── merge_remote_into_local ──────────────────────────────────────────────
def test_merge_adds_new_remote_movement():
    local = {}
    n = merge_remote_into_local(
        remote_by_id={"a": _fields(-10.0, "2026-01-01")}, local_by_id=local
    )
    assert n == 1 and local["a"].amount == -10.0


def test_merge_updates_existing_id():
    local = {"a": _mv("a", -10.0, "2026-01-01")}
    n = merge_remote_into_local(
        remote_by_id={"a": _fields(-99.0, "2026-02-02")}, local_by_id=local
    )
    assert n == 1 and local["a"].amount == -99.0


def test_merge_tombstone_removes_local():
    local = {"a": _mv("a", -10.0, "2026-01-01")}
    n = merge_remote_into_local(
        remote_by_id={"a": {"deleted": True}}, local_by_id=local
    )
    assert n == 1 and "a" not in local


def test_merge_tombstone_for_absent_id_is_noop():
    local = {}
    n = merge_remote_into_local(
        remote_by_id={"a": {"deleted": True}}, local_by_id=local
    )
    assert n == 0 and local == {}


def test_merge_skips_unusable_fields():
    local = {}
    # missing date/account_name → deserialize returns None → skipped, no count
    n = merge_remote_into_local(remote_by_id={"a": {"amount": -1.0}}, local_by_id=local)
    assert n == 0 and local == {}


# ── pull_remote_movements against a fake client ──────────────────────────
class _FakeFS:
    def __init__(self, docs):
        self._docs = docs
        self.calls = []

    def list_workspace_movements(self, *, workspace_id, id_token):
        self.calls.append("list_workspace")
        return self._docs

    def list_user_movements(self, *, uid, id_token):
        self.calls.append("list_user")
        return self._docs

    def query_workspace_movements_updated_after_ms(
        self, *, workspace_id, id_token, updated_after_ms, limit
    ):
        self.calls.append("query_ms")
        return self._docs

    def query_workspace_movements_updated_after(
        self, *, workspace_id, id_token, updated_after
    ):
        self.calls.append("query_after")
        return self._docs

    def parse_doc(self, d):
        return d["id"], d["fields"]


def test_pull_workspace_full_list():
    fs = _FakeFS([{"id": "a", "fields": _fields(-10.0, "2026-01-01")}])
    ids, by_id = pull_remote_movements(fs=fs, workspace_id="ws", uid="u", id_token="t")
    assert ids == ["a"] and by_id["a"]["amount"] == -10.0
    assert fs.calls == ["list_workspace"]


def test_pull_uses_incremental_ms_query_when_given():
    fs = _FakeFS([{"id": "a", "fields": _fields(-10.0, "2026-01-01")}])
    pull_remote_movements(
        fs=fs, workspace_id="ws", uid="u", id_token="t", updated_after_ms=123
    )
    assert fs.calls == ["query_ms"]


def test_pull_user_scope_when_no_workspace():
    fs = _FakeFS([{"id": "a", "fields": _fields(-10.0, "2026-01-01")}])
    pull_remote_movements(fs=fs, workspace_id="", uid="u", id_token="t")
    assert fs.calls == ["list_user"]


def test_pull_skips_docs_without_id():
    fs = _FakeFS([
        {"id": "", "fields": {}},
        {"id": "b", "fields": _fields(-5.0, "2026-01-02")},
    ])
    ids, by_id = pull_remote_movements(fs=fs, workspace_id="ws", uid="u", id_token="t")
    assert ids == ["b"] and set(by_id) == {"b"}
