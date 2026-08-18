"""High-level Google Drive auth for the app.

Holds the OAuth client config (client id in a small JSON settings file, the
client secret + refresh token in the Keychain), runs the interactive loopback
sign-in, and vends fresh access tokens for the Drive client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import http.server
import json
import secrets
import threading
import urllib.parse
import webbrowser

from . import google_oauth as oauth
from .keychain_passwords import delete_password, get_password, set_password
from ..utils.app_paths import accounts_data_dir
from ..utils.logging_setup import get_logger

_log = get_logger(__name__)

_SETTINGS_FILE = "google_drive_settings.json"
_KEYCHAIN_CLIENT_SECRET = "google_drive_client_secret"


def _settings_path() -> Path:
    return accounts_data_dir() / _SETTINGS_FILE


def _read_client_id() -> str:
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str((data or {}).get("client_id", "") or "").strip() if isinstance(data, dict) else ""


def _write_client_id(client_id: str) -> None:
    p = _settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"client_id": str(client_id or "").strip()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        _log.warning("could not save Drive client id: %s", exc)


class _CodeCatcher(http.server.BaseHTTPRequestHandler):
    """Captures the ?code=... Google redirects to on the loopback address."""

    query: dict = {}

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        parsed = urllib.parse.urlparse(self.path)
        _CodeCatcher.query = {
            k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        page = (
            "<html><body style='font-family:sans-serif;text-align:center;"
            "padding-top:3em'><h2>ההתחברות הצליחה ✓</h2>"
            "<p>ניתן לסגור חלון זה ולחזור לאפליקציה.</p>"
            "</body></html>"
        )
        self.wfile.write(page.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - base API name
        pass  # silence the default stderr logging


@dataclass
class GoogleDriveAuth:
    # In-memory cache of the current access token (avoids refreshing every call).
    _cached: Optional[oauth.TokenResponse] = field(default=None, repr=False)

    # ── config ───────────────────────────────────────────────────────────────
    @property
    def client_id(self) -> str:
        return _read_client_id()

    @property
    def client_secret(self) -> str:
        return str(get_password(account=_KEYCHAIN_CLIENT_SECRET) or "")

    def set_credentials(self, *, client_id: str, client_secret: str) -> None:
        _write_client_id(client_id)
        secret = str(client_secret or "").strip()
        if secret:
            set_password(account=_KEYCHAIN_CLIENT_SECRET, password=secret)
        else:
            delete_password(account=_KEYCHAIN_CLIENT_SECRET)
        self._cached = None

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def is_signed_in(self) -> bool:
        return bool(oauth.get_refresh_token())

    # ── token vending (for GoogleDriveClient.token_provider) ─────────────────
    def access_token(self) -> str:
        if self._cached is not None and self._cached.is_valid():
            return self._cached.access_token
        refresh = oauth.get_refresh_token()
        if not refresh:
            return ""
        token = oauth.refresh_access_token(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=refresh,
        )
        self._cached = token
        return token.access_token

    # ── interactive sign-in (loopback) ───────────────────────────────────────
    def sign_in(
        self,
        *,
        open_browser: Callable[[str], object] = webbrowser.open,
        timeout: float = 180.0,
    ) -> None:
        """Run the browser consent flow and store the refresh token. Raises
        :class:`~finance.models.google_oauth.OAuthError` on failure."""
        if not self.is_configured():
            raise oauth.OAuthError("Google client id/secret not set")

        verifier, challenge = oauth.make_pkce_pair()
        state = secrets.token_urlsafe(16)

        _CodeCatcher.query = {}
        server = http.server.HTTPServer(("127.0.0.1", 0), _CodeCatcher)
        server.timeout = timeout
        port = server.server_address[1]
        redirect_uri = f"http://127.0.0.1:{port}"

        url = oauth.build_auth_url(
            client_id=self.client_id,
            redirect_uri=redirect_uri,
            code_challenge=challenge,
            state=state,
        )

        result: dict = {}

        def _serve() -> None:
            server.handle_request()  # one request: the redirect
            result.update(_CodeCatcher.query)

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        open_browser(url)
        thread.join(timeout=timeout)
        try:
            server.server_close()
        except OSError:
            pass

        if result.get("state") != state:
            raise oauth.OAuthError("sign-in did not complete (state mismatch or timed out)")
        code = str(result.get("code", "") or "")
        if not code:
            err = str(result.get("error", "") or "sign-in was cancelled")
            raise oauth.OAuthError(err)

        token = oauth.exchange_code(
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=code,
            code_verifier=verifier,
            redirect_uri=redirect_uri,
        )
        if not token.refresh_token:
            raise oauth.OAuthError("Google did not return a refresh token")
        oauth.set_refresh_token(token.refresh_token)
        self._cached = token

    def sign_out(self) -> None:
        oauth.clear_refresh_token()
        self._cached = None
