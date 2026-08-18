import urllib.parse

from finance.models.google_oauth import (
    DRIVE_SCOPE,
    build_auth_url,
    make_pkce_pair,
    parse_token_response,
)


def test_pkce_pair_is_url_safe_and_distinct():
    verifier, challenge = make_pkce_pair()
    assert verifier and challenge and verifier != challenge
    # base64url: no padding or unsafe chars
    for s in (verifier, challenge):
        assert "=" not in s and "+" not in s and "/" not in s


def test_build_auth_url_has_required_params():
    url = build_auth_url(
        client_id="cid",
        redirect_uri="http://127.0.0.1:1234",
        code_challenge="chal",
        state="st",
    )
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert q["client_id"] == ["cid"]
    assert q["redirect_uri"] == ["http://127.0.0.1:1234"]
    assert q["code_challenge"] == ["chal"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["response_type"] == ["code"]
    assert q["access_type"] == ["offline"]  # so we get a refresh token
    assert q["scope"] == [DRIVE_SCOPE]
    assert q["state"] == ["st"]


def test_parse_token_response_computes_absolute_expiry():
    tok = parse_token_response(
        {"access_token": "at", "expires_in": 3600, "refresh_token": "rt"},
        now=1000.0,
    )
    assert tok.access_token == "at"
    assert tok.refresh_token == "rt"
    assert tok.expires_at == 4600.0
    assert tok.is_valid(now=1000.0)
    assert not tok.is_valid(now=4600.0)  # inside the 60s safety margin


def test_parse_token_response_without_refresh_token():
    tok = parse_token_response({"access_token": "at", "expires_in": 100}, now=0.0)
    assert tok.refresh_token is None
    assert tok.access_token == "at"


def test_token_invalid_when_empty():
    tok = parse_token_response({"expires_in": 3600}, now=0.0)
    assert not tok.is_valid(now=0.0)
