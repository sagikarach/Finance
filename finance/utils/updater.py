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


def _http_get(url: str, timeout: int = 12) -> bytes:
    """
    Fetch URL bytes. On macOS uses curl (system certs, never hangs in bundles).
    Falls back to urllib on other platforms.
    """
    import sys
    if sys.platform == "darwin":
        import subprocess
        result = subprocess.run(
            ["curl", "-s", "-f", "-L", "--max-time", str(timeout),
             "-H", "User-Agent: Finance-App-Updater", url],
            capture_output=True, timeout=timeout + 3,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"curl error {result.returncode}: {stderr}")
        return result.stdout
    # Non-macOS fallback
    import ssl as _ssl
    try:
        import certifi
        ctx = _ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = _ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Finance-App-Updater"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read()


def _ssl_context() -> ssl.SSLContext:
    """Kept for download() which still uses urllib on non-macOS."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
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
        except Exception:
            parts.append(0)
    return tuple(parts)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


class _NoReleaseFound(Exception):
    """Raised when the repo exists but has no published releases."""


def _github_latest_release(repo: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = _http_get(url)
        return json.loads(data)
    except Exception as exc:
        msg = str(exc)
        if "404" in msg or "Not Found" in msg or "curl error 22" in msg:
            raise _NoReleaseFound("אין גרסאות פורסמו עדיין.") from exc
        raise


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
    except Exception:
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
    import subprocess, sys
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
        latest_tag = str(release.get("tag_name", "")).lstrip("v")

        appcast_asset = _find_asset(release, "appcast.json")
        if not appcast_asset:
            # Fall back to comparing raw tag names when appcast is missing.
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
    except Exception as exc:
        return str(exc)


def check_for_updates_mac(repo: Optional[str] = None) -> Tuple[bool, str, Optional[pathlib.Path], Optional[str]]:
    """Legacy one-shot helper kept for compatibility."""
    is_newer_flag, version, zip_url_sig, err = check_version_only(repo)
    if err or not is_newer_flag or not zip_url_sig:
        return is_newer_flag, version, None, err
    app_path, dl_err = download_and_install_update(zip_url_sig)
    return bool(app_path), version, app_path, dl_err

