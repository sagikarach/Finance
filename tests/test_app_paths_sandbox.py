import finance.utils.app_paths as ap


def test_finance_data_dir_isolates_every_path(tmp_path, monkeypatch):
    sandbox = tmp_path / "sbx"
    monkeypatch.setenv("FINANCE_DATA_DIR", str(sandbox))

    # the root and everything derived from it live in the sandbox; logged out,
    # account data goes to the anonymous "_local" account folder
    local = sandbox / "users" / ap.LOCAL_ACCOUNT_DIR
    assert ap.app_data_dir() == sandbox
    assert ap.accounts_data_dir() == local / "accounts"
    assert ap.avatars_data_dir() == local / "avatars"
    assert ap.user_profile_path() == local / "user_profile.json"
    assert sandbox.exists()


def test_no_override_uses_the_real_data_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("FINANCE_DATA_DIR", raising=False)
    # not the sandbox — the normal per-user location (just assert it's not tmp)
    assert ap.app_data_dir() != (tmp_path / "sbx")
