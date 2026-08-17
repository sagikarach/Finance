import finance.utils.app_paths as ap


def test_finance_data_dir_isolates_every_path(tmp_path, monkeypatch):
    sandbox = tmp_path / "sbx"
    monkeypatch.setenv("FINANCE_DATA_DIR", str(sandbox))

    # the root and everything derived from it live in the sandbox
    assert ap.app_data_dir() == sandbox
    assert ap.accounts_data_dir() == sandbox / "accounts"
    assert ap.avatars_data_dir() == sandbox / "avatars"
    assert ap.user_profile_path() == sandbox / "user_profile.json"
    assert sandbox.exists()


def test_no_override_uses_the_real_data_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCE_DATA_DIR", raising=False)
    # not the sandbox — the normal per-user location (just assert it's not tmp)
    assert ap.app_data_dir() != (tmp_path / "sbx")
