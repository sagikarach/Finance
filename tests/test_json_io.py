import json
import os

import pytest

from finance.data.json_io import (
    atomic_write_json,
    read_json_list,
    workspace_json_path,
)


# ── atomic_write_json ────────────────────────────────────────────────────
def test_round_trips_and_preserves_rtl_unicode(tmp_path):
    p = tmp_path / "d.json"
    payload = {"name": "עו״ש", "items": [1, 2, 3], "nested": {"x": "שלום"}}
    atomic_write_json(p, payload)
    assert json.loads(p.read_text(encoding="utf-8")) == payload
    # written un-escaped (ensure_ascii=False)
    assert "עו״ש" in p.read_text(encoding="utf-8")


def test_creates_missing_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "c.json"
    atomic_write_json(p, [1, 2])
    assert p.exists() and json.loads(p.read_text()) == [1, 2]


def test_overwrites_existing_file(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(p, {"v": 1})
    atomic_write_json(p, {"v": 2})
    assert json.loads(p.read_text()) == {"v": 2}


def test_serialize_error_leaves_old_file_intact_and_no_tmp(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(p, {"a": 1})
    with pytest.raises(Exception):
        atomic_write_json(p, {"bad": {1, 2, 3}})  # a set is not JSON serializable
    # the previous good content survives the failed write ...
    assert json.loads(p.read_text()) == {"a": 1}
    # ... and no half-written temp file is left behind
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


# ── read_json_list ───────────────────────────────────────────────────────
def test_read_missing_file_is_empty(tmp_path):
    assert read_json_list(tmp_path / "nope.json", lambda x: x) == []


def test_read_malformed_json_is_empty(tmp_path):
    p = tmp_path / "d.json"
    p.write_text("{not json", encoding="utf-8")
    assert read_json_list(p, lambda x: x) == []


def test_read_non_list_content_is_empty(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert read_json_list(p, lambda x: x) == []


def test_read_maps_and_skips_none(tmp_path):
    p = tmp_path / "d.json"
    p.write_text(json.dumps([1, 2, 3, 4]), encoding="utf-8")
    # deserialize drops odd numbers by returning None
    out = read_json_list(p, lambda x: x if x % 2 == 0 else None)
    assert out == [2, 4]


# ── workspace_json_path ──────────────────────────────────────────────────
def test_explicit_path_is_honored(tmp_path):
    explicit = tmp_path / "custom.json"
    assert workspace_json_path("accounts", explicit) == explicit


def test_no_workspace_key_gives_bare_stem(tmp_path, monkeypatch):
    import finance.models.firebase_session as fs
    import finance.utils.app_paths as ap

    monkeypatch.setattr(fs, "current_firebase_workspace_id", lambda: "")
    monkeypatch.setattr(fs, "current_firebase_uid", lambda: "")
    monkeypatch.setattr(ap, "accounts_data_dir", lambda: tmp_path)
    assert workspace_json_path("mortgages") == tmp_path / "mortgages.json"


def test_workspace_key_is_suffixed(tmp_path, monkeypatch):
    import finance.models.firebase_session as fs
    import finance.utils.app_paths as ap

    monkeypatch.setattr(fs, "current_firebase_workspace_id", lambda: "ws42")
    monkeypatch.setattr(fs, "current_firebase_uid", lambda: "uid9")
    monkeypatch.setattr(ap, "accounts_data_dir", lambda: tmp_path)
    # workspace id wins over uid
    assert workspace_json_path("mortgages") == tmp_path / "mortgages_ws42.json"
