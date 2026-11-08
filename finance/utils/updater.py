from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import ssl
import tempfile
import urllib.request
from typing import Optional, Tuple

from nacl.signing import VerifyKey

from ..__version__ import __version__
from ..appcast_key import PUBLIC_KEY_B64

PUBLIC_KEY_ENV = "FINANCE_ED25519_PUBKEY"
DEFAULT_PUBLIC_KEY = PUBLIC_KEY_B64


class _HttpStatusError(RuntimeError):
    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


# curl exit codes worth one retry: couldn't connect (7), timeout (28), SSL
# connect (35), empty reply (52), send/receive failures (55, 56).
_TRANSIENT_CURL = {7, 28, 35, 52, 55, 56}


def _http_get_once(url: str, timeout: int) -> bytes:
    """Fetch URL bytes. On macOS uses curl (system certs, never hangs in
    bundles); falls back to urllib on other platforms. Raises
    ``_HttpStatusError`` for HTTP >= 400 (so a GitHub 504 is not mistaken for
    "not found")."""
    import sys
    if sys.platform == "darwin":
        import subprocess
        marker = b"\n__HTTP_STATUS__:"
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout),
             "-H", "User-Agent: Finance-App-Updater",
             "-w", marker.decode() + "%{http_code}", url],
            capture_output=True, timeout=timeout + 3,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"curl error {result.returncode}: {stderr}")
        body, _, status_raw = result.stdout.rpartition(marker)
        try:
            status = int(status_raw.strip() or b"0")
        except ValueError:
            status = 0
        if status >= 400:
            raise _HttpStatusError(status)
        return body
    # Non-macOS fallback
    import ssl as _ssl
    import urllib.error as _urlerr
    try:
        import certifi
        ctx = _ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        ctx = _ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Finance-App-Updater"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except _urlerr.HTTPError as exc:
        raise _HttpStatusError(int(exc.code)) from exc


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, _HttpStatusError):
        return exc.status >= 500 or exc.status == 429
    msg = str(exc)
    if msg.startswith("curl error "):
        try:
            return int(msg.split()[2].rstrip(":")) in _TRANSIENT_CURL
        except (IndexError, ValueError):
            return False
    return isinstance(exc, (TimeoutError, OSError))


def _http_get(url: str, timeout: int = 20, attempts: int = 2) -> bytes:
    """``_http_get_once`` with one retry on timeouts, dropped connections and
    server errors (GitHub is occasionally slow for unauthenticated clients)."""
    last: Optional[Exception] = None
    for i in range(max(1, attempts)):
        try:
            return _http_get_once(url, timeout)
        except Exception as exc:  # noqa: BLE001 - classified below
            last = exc
            if i + 1 >= attempts or not _is_transient(exc):
                raise
    assert last is not None
    raise last


def _ssl_context() -> ssl.SSLContext:
    """Kept for download() which still uses urllib on non-macOS."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        pass
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _parse_version(v: str) -> Tuple[int, ...]:
    """Convert semantic-ish version string to tuple of ints for comparison."""
    v = v.lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except (ValueError, TypeError):
            parts.append(0)
    return tuple(parts)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


class _NoReleaseFound(Exception):
    """Raised when the repo exists but has no published releases."""


def _tag_to_version(tag: str) -> str:
    """Strip a release-tag prefix to a bare version. Handles the per-app tag
    namespaces (``desktop-v1.2.3`` / ``mobile-v0.2.0``) plus the legacy ``v*``."""
    t = str(tag or "").strip()
    for prefix in ("desktop-v", "mobile-v", "v"):
        if t.startswith(prefix):
            return t[len(prefix):]
    return t


def _is_desktop_release(rel: dict) -> bool:
    """A desktop release: tagged ``desktop-v*`` (or a legacy ``v*`` carrying an
    ``appcast.json`` asset). Mobile releases (``mobile-v*``) are excluded so they
    can share this repo without shadowing the desktop auto-updater."""
    tag = str(rel.get("tag_name", ""))
    if tag.startswith("mobile-"):
        return False
    if tag.startswith("desktop-v"):
        return True
    return _find_asset(rel, "appcast.json") is not None


def _github_latest_release(repo: str) -> dict:
    """The newest *desktop* release. We can't use ``/releases/latest`` because a
    mobile release could be the repo-wide latest — so we list releases (newest
    first) and pick the first desktop one that isn't a draft/prerelease."""
    url = f"https://api.github.com/repos/{repo}/releases?per_page=15"
    try:
        data = _http_get(url)
        releases = json.loads(data)
    except _HttpStatusError as exc:
        if exc.status == 404:
            raise _NoReleaseFound("אין גרסאות פורסמו עדיין.") from exc
        raise
    if not isinstance(releases, list) or not releases:
        raise _NoReleaseFound("אין גרסאות פורסמו עדיין.")
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        if _is_desktop_release(rel):
            return rel
    raise _NoReleaseFound("אין גרסאות דסקטופ פורסמו עדיין.")


def _find_asset(release: dict, name: str) -> Optional[dict]:
    for asset in release.get("assets", []) or []:
        if asset.get("name") == name:
            return asset
    return None


def _download(url: str, dest_path: pathlib.Path) -> pathlib.Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    data = _http_get(url, timeout=120)
    dest_path.write_bytes(data)
    return dest_path


def _get_public_key() -> Optional[VerifyKey]:
    raw = os.environ.get(PUBLIC_KEY_ENV, DEFAULT_PUBLIC_KEY)
    if not raw:
        return None
    try:
        data = base64.b64decode(raw.strip())
        return VerifyKey(data)
    except (ValueError, TypeError):
        return None


def _verify_signature(path: pathlib.Path, signature_b64: str) -> Optional[str]:
    vk = _get_public_key()
    if not vk:
        return None
    try:
        sig = base64.b64decode(signature_b64)
        vk.verify(path.read_bytes(), sig)
        return None
    except Exception as exc:  # noqa: BLE001
        return f"אימות חתימת העדכון נכשל: {exc}"


def _extract_zip(zip_path: pathlib.Path, dest_dir: pathlib.Path) -> pathlib.Path:
    import subprocess
    import sys
    dest_dir.mkdir(parents=True, exist_ok=True)
    if sys.platform == "darwin":
        # Use ditto on macOS — shutil/zipfile corrupts fat binaries and resource forks.
        result = subprocess.run(
            ["ditto", "-x", "-k", "--sequesterRsrc", str(zip_path), str(dest_dir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ditto extraction failed: {result.stderr.strip()}")
    else:
        shutil.unpack_archive(str(zip_path), str(dest_dir))
    return dest_dir


def check_version_only(repo: Optional[str] = None) -> Tuple[bool, str, Optional[str], Optional[str]]:
    """
    Fast version check — no download.

    Returns: (is_update_available, latest_version, zip_url_or_None, error_or_None)
    """
    repo = repo or os.environ.get("FINANCE_UPDATE_REPO", "sagikarach/Finance")
    try:
        release = _github_latest_release(repo)
        latest_tag = _tag_to_version(release.get("tag_name", ""))

        appcast_asset = _find_asset(release, "appcast.json")
        if not appcast_asset:
            is_newer_tag = _is_newer(latest_tag, __version__)
            return is_newer_tag, latest_tag, None, None

        appcast = json.loads(_http_get(appcast_asset["browser_download_url"]))

        latest_version = str(appcast.get("version", latest_tag)).lstrip("v")
        if not _is_newer(latest_version, __version__):
            return False, latest_version, None, None

        zip_url = appcast.get("url")
        sig = appcast.get("signature")
        if not zip_url or not sig:
            return True, latest_version, None, "Appcast missing url or signature — update manually."

        return True, latest_version, f"{zip_url}|{sig}", None
    except _NoReleaseFound:
        # No releases published yet — not an error from the user's perspective.
        return False, __version__, None, None
    except Exception as exc:  # noqa: BLE001
        return False, "", None, f"בדיקת עדכון נכשלה: {exc}"


def download_and_install_update(zip_url_and_sig: str) -> Tuple[Optional[pathlib.Path], Optional[str]]:
    """
    Download, verify and extract the update zip.

    Returns: (Finance.app path or None, error_or_None)
    """
    try:
        parts = zip_url_and_sig.split("|", 1)
        if len(parts) != 2:
            return None, "Invalid update URL."
        zip_url, sig = parts[0].strip(), parts[1].strip()

        zip_dest = pathlib.Path(tempfile.gettempdir()) / "Finance-mac-latest.zip"
        _download(zip_url, zip_dest)

        sig_error = _verify_signature(zip_dest, sig)
        if sig_error:
            return None, sig_error

        extract_dir = pathlib.Path(tempfile.mkdtemp(prefix="finance-update-"))
        _extract_zip(zip_dest, extract_dir)

        # Try a few common locations for Finance.app inside the zip.
        for candidate in [
            extract_dir / "Finance.app",
            extract_dir / "dist" / "Finance.app",
            next(extract_dir.rglob("Finance.app"), None),  # type: ignore[arg-type]
        ]:
            if candidate is not None and pathlib.Path(candidate).exists():
                app = pathlib.Path(candidate)
                # Restore executable bit on the main binary (may be lost during zip extraction).
                main_bin = app / "Contents" / "MacOS" / "Finance"
                if main_bin.exists():
                    main_bin.chmod(main_bin.stat().st_mode | 0o111)
                return app, None

        return None, f"Finance.app not found in extracted archive ({extract_dir})."
    except Exception as exc:  # noqa: BLE001
        return None, f"הורדת העדכון נכשלה: {exc}"


def install_app_to_applications(app_path: pathlib.Path) -> Optional[str]:
    """
    Copy Finance.app to /Applications/ using ditto (preserves code-signing).
    Returns an error string on failure, None on success.
    """
    import subprocess
    dest = pathlib.Path("/Applications/Finance.app")
    try:
        if dest.exists():
            shutil.rmtree(str(dest))
        result = subprocess.run(
            ["ditto", str(app_path), str(dest)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return result.stderr.strip() or "ditto failed"
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        return str(exc)



