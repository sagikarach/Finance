"""Google OAuth 2.0 for a desktop app — the loopback (PKCE) flow.

Signs the user in with Google in their browser and stores the resulting refresh
token in the macOS Keychain (like the Gemini key). The access token is derived
on demand from the refresh token, so :class:`GoogleDriveAuth.access_token` can
be handed straight to :class:`~finance.models.google_drive_client.GoogleDriveClient`
as its ``token_provider``.

The pure pieces (PKCE, URL building, token-response parsing, expiry) are split
out so they're unit-testable without a browser or network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import urllib.request

from .firebase_client import _ssl_context
from .keychain_passwords import delete_password, get_password, set_password
from ..utils.safe import PARSE_ERRORS

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Full Drive scope: needed to trash a file the app didn't create (drive.file
# would only see app-created files). Read-only can't delete after import.
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

_KEYCHAIN_REFRESH_TOKEN = "google_drive_refresh_token"


def make_pkce_pair() -> Tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def build_auth_url(
    *,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
    scope: str = DRIVE_SCOPE,
) -> str:
    """The consent URL to open in the browser."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",  # ask for a refresh token
        "prompt": "consent",
    }
    return f"{_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


@dataclass(frozen=True)
class TokenResponse:
    access_token: str
    expires_at: float
    refresh_token: Optional[str] = None

    def is_valid(self, *, now: Optional[float] = None) -> bool:
        ref = now if now is not None else time.time()
        return bool(self.access_token) and ref < (self.expires_at - 60)


def parse_token_response(raw: Dict[str, Any], *, now: Optional[float] = None) -> TokenResponse:
    """Build a TokenResponse from Google's JSON, computing an absolute expiry."""
    ref = now if now is not None else time.time()
    access = str(raw.get("access_token", "") or "")
    try:
        expires_in = float(raw.get("expires_in", 0) or 0)
    except (TypeError, ValueError):
        expires_in = 0.0
    refresh = raw.get("refresh_token")
    refresh_s = str(refresh).strip() if refresh else None
    return TokenResponse(
        access_token=access,
        expires_at=ref + expires_in,
        refresh_token=refresh_s,
    )


class OAuthError(RuntimeError):
    """An OAuth token request failed."""


def _post_form(url: str, form: Dict[str, str], *, timeout: float = 30.0) -> Dict[str, Any]:
    body = urllib.parse.urlencode(form).encode("ascii")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Finance")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001 - translate transport/HTTP errors
        detail = ""
        read = getattr(e, "read", None)
        if callable(read):
            try:
                payload = read()
                if isinstance(payload, (bytes, bytearray)):
                    detail = payload.decode("utf-8", errors="replace")
            except PARSE_ERRORS:
                detail = ""
        raise OAuthError(detail or str(e))
    try:
        data = json.loads(raw)
    except PARSE_ERRORS:
        raise OAuthError("invalid token response")
    if not isinstance(data, dict) or data.get("error"):
        msg = ""
        if isinstance(data, dict):
            msg = str(data.get("error_description") or data.get("error") or "")
        raise OAuthError(msg or "token request failed")
    return data


def exchange_code(
    *,
    client_id: str,
    client_secret: str,
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> TokenResponse:
    """Trade the authorization code for tokens (includes the refresh token)."""
    data = _post_form(
        _TOKEN_ENDPOINT,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )
    return parse_token_response(data)


def refresh_access_token(
    *, client_id: str, client_secret: str, refresh_token: str
) -> TokenResponse:
    """Get a fresh access token from a stored refresh token."""
    data = _post_form(
        _TOKEN_ENDPOINT,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    # A refresh response has no new refresh_token; keep the existing one.
    return parse_token_response(data)


# ── refresh-token storage (Keychain) ─────────────────────────────────────────
def get_refresh_token() -> Optional[str]:
    return get_password(account=_KEYCHAIN_REFRESH_TOKEN)


def set_refresh_token(token: str) -> None:
    token = str(token or "").strip()
    if token:
        set_password(account=_KEYCHAIN_REFRESH_TOKEN, password=token)
    else:
        delete_password(account=_KEYCHAIN_REFRESH_TOKEN)


def clear_refresh_token() -> None:
    delete_password(account=_KEYCHAIN_REFRESH_TOKEN)
