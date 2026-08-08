"""Sync-state bookkeeping: what was pulled/applied and what deletes/upserts are
still pending. Persisted per workspace key; monkeypatched to a tmp dir here."""

import finance.models.firebase_sync_state as ss
from finance.models.firebase_sync_state import (
    SyncState,
    _uniq,
    add_pending_delete,
    load_sync_state,
    mark_pending_upsert_mortgage,
    save_sync_state,
)


def _state():
    return SyncState(
        remote_ids=["a", "b"],
        applied_balance_ids=["a"],
        logged_action_ids=[],
        pending_delete_movement_ids=["x"],
        pending_delete_event_ids=[],
        pending_delete_installment_plan_ids=[],
        last_remote_updated_at="2026-01-01",
        last_remote_updated_at_ms=123,
    )


def test_uniq_dedups_and_preserves_order():
    assert _uniq(["a", "b", "a", "c", " b ", "", None]) == ["a", "b", "c"]


def test_to_from_dict_round_trip():
    st = _state()
    assert SyncState.from_dict(st.to_dict()).to_dict() == st.to_dict()


def test_from_dict_rejects_non_dict():
    st = SyncState.from_dict("garbage")
    assert st.remote_ids == [] and st.last_remote_updated_at_ms == 0


def test_load_save_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "app_data_dir", lambda: tmp_path)
    assert load_sync_state("ws1").remote_ids == []  # missing → default
    st = _state()
    save_sync_state("ws1", st)
    assert load_sync_state("ws1").to_dict() == st.to_dict()


def test_add_pending_delete_by_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "app_data_dir", lambda: tmp_path)
    add_pending_delete(key="ws1", kind="movement", item_id="mv9")
    add_pending_delete(key="ws1", kind="installment_plan", item_id="pl3")
    add_pending_delete(key="ws1", kind="mortgage", item_id="mg7")
    st = load_sync_state("ws1")
    assert st.pending_delete_movement_ids == ["mv9"]
    assert st.pending_delete_installment_plan_ids == ["pl3"]
    assert st.pending_delete_mortgage_ids == ["mg7"]


def test_mark_pending_upsert_mortgage(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "app_data_dir", lambda: tmp_path)
    mark_pending_upsert_mortgage(key="ws1", mortgage_id="mg3")
    mark_pending_upsert_mortgage(key="ws1", mortgage_id="mg3")  # dedups
    assert load_sync_state("ws1").pending_upsert_mortgage_ids == ["mg3"]
