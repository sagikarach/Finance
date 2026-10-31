"""Each Firebase account gets its own local folder — no data bleeds between
accounts, even when they share (or guess) a workspace id."""

import json

import pytest

import finance.utils.app_paths as ap
from finance.models.firebase_session import FirebaseSession, FirebaseSessionStore
from finance.models.firebase_workspace_profiles import FirebaseWorkspaceProfilesStore

WID = "ABCD-EFGH-IJKL"


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path))
    return tmp_path


def _login(uid: str, email: str, wid: str = WID) -> None:
    FirebaseSessionStore().save(
        FirebaseSession(
            api_key="k", project_id="p", email=email, uid=uid,
            workspace_id=wid, refresh_token="r",
        )
    )


def test_accounts_on_same_workspace_get_separate_folders(sandbox):
    _login("uidA", "a@x.com")
    a = ap.accounts_data_dir()
    (a / f"bank_movements_{WID}.json").write_text("[1]", encoding="utf-8")

    _login("uidB", "b@x.com")
    b = ap.accounts_data_dir()

    assert a == sandbox / "users" / "uidA" / "accounts"
    assert b == sandbox / "users" / "uidB" / "accounts"
    assert not (b / f"bank_movements_{WID}.json").exists()


def test_logged_out_uses_local_folder(sandbox):
    assert ap.accounts_data_dir() == sandbox / "users" / "_local" / "accounts"


def test_legacy_files_migrate_only_to_their_owner(sandbox):
    legacy = sandbox / "accounts"
    legacy.mkdir()
    (legacy / f"bank_movements_{WID}.json").write_text("[42]", encoding="utf-8")
    (legacy / "google_drive_settings.json").write_text("{}", encoding="utf-8")
    FirebaseWorkspaceProfilesStore().upsert(name="mine", workspace_id=WID, email="a@x.com")

    # Someone else typing the same workspace id gets nothing from the old cache.
    _login("intruder", "evil@x.com")
    assert not (ap.accounts_data_dir() / f"bank_movements_{WID}.json").exists()
    assert not (ap.accounts_data_dir() / "google_drive_settings.json").exists()

    # The owner (email matches the saved profile) gets their data back.
    _login("uidA", "A@x.com")
    moved = ap.accounts_data_dir() / f"bank_movements_{WID}.json"
    assert json.loads(moved.read_text(encoding="utf-8")) == [42]
    assert (ap.accounts_data_dir() / "google_drive_settings.json").exists()
    # Copied, not moved — the original stays as a backup.
    assert (legacy / f"bank_movements_{WID}.json").exists()


def test_migration_runs_once_so_reset_stays_reset(sandbox):
    legacy = sandbox / "accounts"
    legacy.mkdir()
    (legacy / f"bank_movements_{WID}.json").write_text("[1]", encoding="utf-8")
    _login("uidA", "a@x.com")
    f = ap.accounts_data_dir() / f"bank_movements_{WID}.json"
    assert f.exists()
    f.unlink()  # e.g. "reset local data"
    assert not (ap.accounts_data_dir() / f.name).exists()


def test_profiles_are_matched_by_email_and_workspace(sandbox):
    store = FirebaseWorkspaceProfilesStore()
    store.upsert(name="A", workspace_id=WID, email="a@x.com")
    store.upsert(name="B", workspace_id=WID, email="b@x.com")
    store.update_ui_prefs(workspace_id=WID, email="b@x.com", display_name="Bee")

    a = store.find_by_workspace_id(workspace_id=WID, email="a@x.com")
    b = store.find_by_workspace_id(workspace_id=WID, email="b@x.com")
    assert a is not None and a.name == "A" and a.display_name == ""
    assert b is not None and b.name == "B" and b.display_name == "Bee"


def test_new_workspace_file_never_copies_shared_legacy_movements(sandbox):
    from finance.models.firebase_movements_sync import FirebaseMovementsSyncService

    _login("uidA", "a@x.com")
    acc = ap.accounts_data_dir()
    (acc / "bank_movements.json").write_text('[{"id": "old-shared"}]', encoding="utf-8")
    FirebaseMovementsSyncService().ensure_user_local_file(WID)
    assert json.loads((acc / f"bank_movements_{WID}.json").read_text(encoding="utf-8")) == []


def test_session_save_is_atomic_no_tmp_left(sandbox):
    _login("uidA", "a@x.com")
    fb = sandbox / "firebase"
    assert (fb / "session.json").exists()
    assert not [p for p in fb.iterdir() if p.name != "session.json" and p.suffix != ".json"]
    assert FirebaseSessionStore().load().uid == "uidA"
